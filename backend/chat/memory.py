"""
Conversation memory helpers for the chat module.

Two-tier memory model:
  Tier 1 (hot, in-prompt): rolling summary + verbatim window + per-turn context
  Tier 2 (warm, persisted): all ChatMessage rows, tool_observations, attachments

Phase 2 added the verbatim window packer (`pack_verbatim_window`).
Phase 3 adds the rolling summary (`update_summary_for_session`,
`detect_falloff_pair`, `inject_summary`).
Phase 4 adds tool-observation replay (`inject_tool_replays`).
"""

import json
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


# --------------------------------------------------------------------------
# Phase 2: verbatim window packing
# --------------------------------------------------------------------------


def pack_verbatim_window(messages: list[dict], budget_tokens: int) -> list[dict]:
    """
    Walk `messages` newest → oldest, accumulating until adding the next would
    exceed `budget_tokens`. Returns the kept messages in chronological order.

    The most recent message is always included if there is one — even when it
    alone exceeds the budget — because dropping the immediately-prior turn is
    a worse failure mode than overshooting the budget by a single message.

    `messages` is expected to be a list of dicts with at least a `content`
    key (str). Other keys (role, metadata) are preserved untouched.
    """
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


# --------------------------------------------------------------------------
# Phase 3: rolling summary
# --------------------------------------------------------------------------


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
    """
    Find the oldest user/assistant pair that has fallen off the verbatim
    window AND has not yet been folded into the rolling summary.

    `all_messages` must be ordered chronologically (oldest first) and each
    dict must have `role`, `content`, and `created_at` keys.

    Returns (user_msg, assistant_msg) or None if no fold is needed this turn.
    """
    if not all_messages:
        return None

    packed = pack_verbatim_window(all_messages, budget_tokens)
    if len(packed) >= len(all_messages):
        return None  # everything still fits, nothing fell off

    live_start_ts = packed[0]["created_at"]

    # Candidates: messages older than the live window AND newer than the
    # watermark (or all, if no watermark yet).
    candidates = [
        m
        for m in all_messages
        if m["created_at"] < live_start_ts
        and (summary_until_ts is None or m["created_at"] > summary_until_ts)
    ]
    if not candidates:
        return None

    # Find the oldest user message in the candidate range, paired with the
    # next assistant message that follows it. If either is missing (e.g. an
    # orphan user without a reply because generation errored), skip — the
    # next turn will reconsider with more context.
    user_msg = next((m for m in candidates if m["role"] == "user"), None)
    if user_msg is None:
        return None
    user_idx = candidates.index(user_msg)
    asst_msg = next(
        (m for m in candidates[user_idx + 1 :] if m["role"] == "assistant"),
        None,
    )
    if asst_msg is None:
        return None
    return (user_msg, asst_msg)


def update_summary_for_session(session, llm) -> bool:
    """
    Fold the oldest unsummarized fallen-off exchange into `session.summary`.
    Returns True if the summary was updated; False otherwise (nothing to fold,
    workflow active, feature flag off, or LLM call failed).

    Synchronous: invokes one non-streaming LLM call. The caller decides when
    to invoke this (typically right after the assistant message is saved and
    the SSE 'done' event has been yielded).
    """
    if not CHAT_SESSION_SUMMARY_ENABLED:
        return False
    # Workflow turns: workflow_state is canonical; don't double-track here
    if session.workflow_state:
        return False

    # Local import — avoids circular dependency with models at module load
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
        # Use generate (non-streaming, no extra context, no history) so the
        # call is small and predictable.
        new_summary = llm.generate(prompt, context="", history=None)
    except Exception as e:
        logger.warning("summary_update_call_failed", error=str(e))
        return False

    if not new_summary or not new_summary.strip():
        logger.warning("summary_update_empty_response")
        return False

    new_summary = truncate_to_tokens(new_summary.strip(), SUMMARY_TOKEN_CAP)

    # Single-row update — avoids racing with the session's other fields.
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
    """
    Prepend a synthetic system message containing the rolling summary so the
    LLM sees it before the verbatim history. No-op if summary is empty or
    feature flag is off.
    """
    if not CHAT_SESSION_SUMMARY_ENABLED or not summary or not summary.strip():
        return history
    note = {
        "role": "system",
        "content": f"[SESSION SUMMARY]\n{summary.strip()}\n[/SESSION SUMMARY]",
    }
    return [note] + list(history)


# --------------------------------------------------------------------------
# Phase 4: tool-observation replay
# --------------------------------------------------------------------------


def inject_tool_replays(
    history_with_obs: list[dict],
    turn_count: int = TOOL_REPLAY_TURNS,
) -> list[dict]:
    """
    For the most recent `turn_count` assistant messages with a non-empty
    `tool_observation`, inject a synthetic system note immediately after each
    so the next turn's LLM call has the raw evidence (not just the assistant's
    paraphrase).

    `history_with_obs` items must be dicts with `role`, `content`, and
    optionally `tool_observation` (a dict shaped by `views.py`).
    No-op if feature flag is off or history is empty.
    """
    if not CHAT_TOOL_REPLAY_ENABLED or not history_with_obs:
        return list(history_with_obs)

    # Walk newest → oldest to identify which assistant indices replay.
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
        # Strip tool_observation from the message itself before forwarding —
        # only the synthetic system note carries it forward.
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
            out.append({"role": "system", "content": note})
    return out


def build_replay_payload(
    tool_name: str,
    tool_args: dict,
    formatted_result: str,
) -> Optional[dict]:
    """
    Produce the JSON shape stored on `ChatMessage.tool_observation`, or None
    if the tool is not whitelisted for replay or the result is empty.

    The whitelist lives in `chat.tools.REPLAYABLE_TOOLS` to keep tool-related
    decisions colocated with tool definitions.
    """
    from .tools import REPLAYABLE_TOOLS

    if not CHAT_TOOL_REPLAY_ENABLED:
        return None
    if tool_name not in REPLAYABLE_TOOLS:
        return None
    if not formatted_result:
        return None
    return {
        "tool": tool_name,
        "args": tool_args or {},
        "result_text": truncate_to_tokens(formatted_result, TOOL_REPLAY_TOKENS),
    }
