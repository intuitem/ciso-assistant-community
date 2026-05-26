"""Verbatim window packing, rolling summary, tool-observation replay."""

import json
import re
from datetime import datetime
from typing import Optional

import structlog

from .constants import (
    CHAT_SESSION_SUMMARY_ENABLED,
    CHAT_TOOL_REPLAY_ENABLED,
    SUMMARY_INPUT_TOKEN_CAP,
    SUMMARY_TOKEN_CAP,
    TOOL_REPLAY_TOKENS,
    TOOL_REPLAY_TURNS,
    VERBATIM_WINDOW_TOKENS,
)
from .tokens import count_tokens, truncate_to_tokens


logger = structlog.get_logger(__name__)


def pack_verbatim_window(messages: list[dict], budget_tokens: int) -> list[dict]:
    """Pack newest→oldest into budget. Always keeps the last message even if oversize."""
    if not messages or budget_tokens <= 0:
        return []

    kept: list[dict] = []
    used = 0
    for msg in reversed(messages):
        msg_tokens = count_tokens(msg.get("content", "") or "")
        if kept and used + msg_tokens > budget_tokens:
            break
        kept.append(msg)
        used += msg_tokens

    kept.reverse()
    return kept


SUMMARY_PROMPT = """You maintain a running summary of an ongoing GRC chat session.
Update the summary below by integrating ONE new exchange.

EXISTING SUMMARY:
{summary}

NEW EXCHANGE:
USER: {user}
ASSISTANT: {assistant}

Rewrite the summary using exactly these four sections.
Total length MUST be under 400 tokens. Do not invent details.

GOAL: <one sentence: what is the user trying to accomplish>
ENTITIES: <comma-separated named objects: frameworks, assets, control IDs, domain names>
DECISIONS: <numbered list of conclusions or commitments reached>
OPEN: <numbered list of pending questions or actions>

If a section is empty, write "none"."""


def detect_falloff_pair(
    all_messages: list[dict],
    summary_until_ts: Optional[datetime],
    budget_tokens: int = VERBATIM_WINDOW_TOKENS,
) -> Optional[tuple[dict, dict]]:
    """Oldest user/assistant pair that fell off the window AND isn't summarized yet."""
    if not all_messages:
        return None

    packed = pack_verbatim_window(all_messages, budget_tokens)
    if len(packed) >= len(all_messages):
        return None

    live_start_ts = packed[0]["created_at"]
    candidates = [
        m
        for m in all_messages
        if m["created_at"] < live_start_ts
        and (summary_until_ts is None or m["created_at"] > summary_until_ts)
    ]
    if not candidates:
        return None

    # Only consecutive (user, assistant) pairs — orphans (errored gens) stay unfolded
    for i in range(len(candidates) - 1):
        cur, nxt = candidates[i], candidates[i + 1]
        if cur["role"] == "user" and nxt["role"] == "assistant":
            return (cur, nxt)
    return None


def update_summary_for_session(session, llm) -> bool:
    """Fold one fallen-off exchange into session.summary. Synchronous LLM call."""
    if not CHAT_SESSION_SUMMARY_ENABLED:
        return False
    # workflow_state is the canonical memory for workflow turns
    if session.workflow_state:
        return False

    # Local import avoids a circular at module load
    from .models import ChatSession

    all_messages = list(
        session.messages.order_by("created_at").values("role", "content", "created_at")
    )
    pair = detect_falloff_pair(
        all_messages, session.summary_until_ts, VERBATIM_WINDOW_TOKENS
    )
    if pair is None:
        return False

    user_msg, asst_msg = pair
    truncated_assistant = truncate_to_tokens(
        asst_msg.get("content", "") or "", SUMMARY_INPUT_TOKEN_CAP
    )

    prompt = SUMMARY_PROMPT.format(
        summary=session.summary or "(empty)",
        user=user_msg.get("content", "") or "",
        assistant=truncated_assistant,
    )

    try:
        new_summary = llm.generate(prompt, context="", history=None)
    except Exception as e:
        logger.warning("summary_update_call_failed", error=str(e))
        return False

    if not new_summary or not new_summary.strip():
        logger.warning("summary_update_empty_response")
        return False

    new_summary = truncate_to_tokens(new_summary.strip(), SUMMARY_TOKEN_CAP)

    # Single-row update avoids racing with the session's other fields
    ChatSession.objects.filter(pk=session.pk).update(
        summary=new_summary,
        summary_until_ts=asst_msg["created_at"],
    )
    logger.info(
        "summary_updated",
        session_id=str(session.pk),
        watermark=asst_msg["created_at"].isoformat(),
        summary_tokens=count_tokens(new_summary),
    )
    return True


def inject_summary(history: list[dict], summary: str) -> list[dict]:
    """Prepend the rolling summary as a system message. No-op when empty/disabled."""
    if not CHAT_SESSION_SUMMARY_ENABLED or not summary or not summary.strip():
        return history
    note = {
        "role": "system",
        "content": f"[SESSION SUMMARY]\n{summary.strip()}\n[/SESSION SUMMARY]",
    }
    return [note] + list(history)


def inject_tool_replays(
    history_with_obs: list[dict],
    turn_count: int = TOOL_REPLAY_TURNS,
) -> list[dict]:
    """Append synthetic system notes for the last N assistants' tool_observation."""
    if not CHAT_TOOL_REPLAY_ENABLED or not history_with_obs:
        return list(history_with_obs)

    replay_indices: set[int] = set()
    seen_assistants = 0
    for i in range(len(history_with_obs) - 1, -1, -1):
        msg = history_with_obs[i]
        if msg.get("role") != "assistant":
            continue
        seen_assistants += 1
        if seen_assistants <= turn_count and msg.get("tool_observation"):
            replay_indices.add(i)
        if seen_assistants >= turn_count:
            break

    if not replay_indices:
        return [
            {k: v for k, v in m.items() if k != "tool_observation"}
            for m in history_with_obs
        ]

    out: list[dict] = []
    for i, msg in enumerate(history_with_obs):
        # Strip tool_observation; the synthetic note carries it forward instead
        clean = {k: v for k, v in msg.items() if k != "tool_observation"}
        out.append(clean)
        if i in replay_indices:
            obs = msg.get("tool_observation") or {}
            tool = obs.get("tool", "unknown")
            args = obs.get("args", {})
            try:
                args_str = json.dumps(args, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                args_str = str(args)
            result_text = truncate_to_tokens(
                obs.get("result_text", "") or "", TOOL_REPLAY_TOKENS
            )
            note = (
                f"[TOOL OBSERVATION from previous turn — {tool}({args_str})]\n"
                f"{result_text}\n"
                "[/TOOL OBSERVATION]"
            )
            # user role, not system — replay carries (potentially) user-data text
            out.append({"role": "user", "content": note})
    return out


# Strip role/delimiter markers that could let attacker-controlled tool data
# escape framing. Mirrors views._INJECTION_PATTERNS plus our own wrappers.
_REPLAY_INJECTION_PATTERNS = re.compile(
    r"(?:"
    r"\[/?(?:SYSTEM|CONTEXT|INST|SESSION SUMMARY|TOOL OBSERVATION)\]"
    r"|<\|(?:im_start|im_end|system)\|>"
    r"|```\s*(?:system|tool_call)"
    r")",
    re.IGNORECASE,
)


def _sanitize_replay_text(text: str) -> str:
    return _REPLAY_INJECTION_PATTERNS.sub("", text or "")


def build_replay_payload(
    tool_name: str,
    tool_args: dict,
    formatted_result: str,
) -> Optional[dict]:
    """Shape the tool_observation payload, or None if tool isn't replayable."""
    from .tools import REPLAYABLE_TOOLS

    if not CHAT_TOOL_REPLAY_ENABLED:
        return None
    if tool_name not in REPLAYABLE_TOOLS:
        return None
    if not formatted_result:
        return None
    sanitized = _sanitize_replay_text(formatted_result)
    return {
        "tool": tool_name,
        "args": tool_args or {},
        "result_text": truncate_to_tokens(sanitized, TOOL_REPLAY_TOKENS),
    }
