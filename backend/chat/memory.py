"""
Conversation memory helpers for the chat module.

Phase 2: token-aware verbatim-window packing. Replaces the previous fixed
20-message slice with a budget-driven walk over recent messages.

Future phases (rolling summary, tool-observation replay) will introduce a
SessionMemory protocol; for now a single function suffices.
"""

from .tokens import count_tokens


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
