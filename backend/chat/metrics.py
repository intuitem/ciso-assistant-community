"""
Chat memory metrics helpers (Levels 1 + 2).

Level 1: append a JSON line per turn to a log file (env-configurable). Useful
for live tailing and post-hoc analysis with `jq`/`awk`. Failures are swallowed
so observability never breaks the chat.

Level 2: produce the per-message metrics dict that gets persisted on
`ChatMessage.metrics` for SQL-driven aggregation by the `chat_metrics`
management command.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


_DEFAULT_PATH = "logs/chat_metrics.jsonl"


def _resolve_path() -> Optional[Path]:
    """
    Return the configured metrics log path or None if disabled.

    `CHAT_METRICS_LOG_PATH` env var:
      - empty / "off" / "false" / "0" → disabled
      - any other value → that path (relative to cwd)
      - unset → default `logs/chat_metrics.jsonl`
    """
    raw = os.environ.get("CHAT_METRICS_LOG_PATH", _DEFAULT_PATH).strip()
    if not raw or raw.lower() in ("off", "false", "0", "disabled"):
        return None
    return Path(raw)


def build_turn_metrics(
    *,
    prompt_tokens: int,
    model_context_tokens: int,
    system_prompt_tokens: int,
    context_tokens: int,
    history_tokens: int,
    user_tokens: int,
    summary_tokens: int,
    history_messages: int,
    section_names: list[str],
) -> dict:
    """
    Bundle the per-turn metrics into a stable dict shape, used both by the
    Level 1 JSONL writer and as the value persisted on `ChatMessage.metrics`.
    """
    over_budget = prompt_tokens > model_context_tokens
    high_watermark = prompt_tokens >= int(model_context_tokens * 0.8)
    utilization_pct = round(100 * prompt_tokens / max(model_context_tokens, 1), 1)
    return {
        "prompt_tokens": prompt_tokens,
        "model_context_tokens": model_context_tokens,
        "utilization_pct": utilization_pct,
        "system_prompt_tokens": system_prompt_tokens,
        "context_tokens": context_tokens,
        "history_tokens": history_tokens,
        "user_tokens": user_tokens,
        "summary_tokens": summary_tokens,
        "history_messages": history_messages,
        "sections": section_names,
        "over_budget": over_budget,
        "high_watermark": high_watermark,
    }


def record_metric(event: str, **fields) -> None:
    """
    Append one JSON line to the chat metrics log file. Fail-soft: a write
    error logs a warning but never raises.
    """
    path = _resolve_path()
    if path is None:
        return

    payload = {"event": event, "ts": time.time(), **fields}
    line = json.dumps(payload, default=str, ensure_ascii=False)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as e:
        logger.warning("chat_metric_write_failed", error=str(e), path=str(path))
