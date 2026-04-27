"""Tests for memory.py — verbatim window packing."""

from chat.memory import pack_verbatim_window
from chat.tokens import count_tokens


def _msg(role: str, content: str) -> dict:
    return {"role": role, "content": content}


class TestPackVerbatimWindow:
    def test_empty_input(self):
        assert pack_verbatim_window([], 1000) == []

    def test_zero_budget(self):
        msgs = [_msg("user", "hi")]
        assert pack_verbatim_window(msgs, 0) == []

    def test_negative_budget(self):
        msgs = [_msg("user", "hi")]
        assert pack_verbatim_window(msgs, -1) == []

    def test_all_fit(self):
        msgs = [
            _msg("user", "hello"),
            _msg("assistant", "hi there"),
            _msg("user", "how are you"),
        ]
        result = pack_verbatim_window(msgs, 1000)
        assert result == msgs  # all kept, original chronological order

    def test_partial_fit_drops_oldest(self):
        # Each "X" * 30 is ~10 tokens
        msgs = [
            _msg("user", "X" * 30),  # oldest
            _msg("assistant", "Y" * 30),
            _msg("user", "Z" * 30),  # newest
        ]
        # Budget for ~2 messages
        result = pack_verbatim_window(msgs, 25)
        assert len(result) == 2
        # Chronological order preserved (older→newer in result)
        assert result[0]["content"] == "Y" * 30
        assert result[1]["content"] == "Z" * 30

    def test_always_keeps_last_even_if_oversize(self):
        # One huge message that exceeds the budget alone
        big = _msg("user", "X" * 10_000)
        result = pack_verbatim_window([big], 10)
        # We do NOT drop the most recent message
        assert result == [big]

    def test_chronological_order_after_packing(self):
        msgs = [_msg("user", f"msg{i}") for i in range(10)]
        result = pack_verbatim_window(msgs, 1000)
        # Check order is preserved
        assert [m["content"] for m in result] == [f"msg{i}" for i in range(10)]

    def test_budget_respected_when_dropping(self):
        # 5 messages of ~10 tokens each (~30 chars)
        msgs = [_msg("user", "ABCDEFGHIJ" * 3) for _ in range(5)]
        budget = 25  # fits ~2 messages with slack
        result = pack_verbatim_window(msgs, budget)
        # The budget invariant: total kept (excluding the always-kept-last
        # exception) should not exceed budget. With 5 equal-size messages
        # and budget for ~2, we expect 2-3 messages kept.
        assert 2 <= len(result) <= 3
        assert result == msgs[-len(result) :]  # tail of input

    def test_preserves_dict_shape(self):
        msgs = [
            {"role": "user", "content": "hi", "extra": "preserved"},
            {"role": "assistant", "content": "hello", "ts": 12345},
        ]
        result = pack_verbatim_window(msgs, 1000)
        assert result[0]["extra"] == "preserved"
        assert result[1]["ts"] == 12345

    def test_handles_missing_content(self):
        # Defensive: dict without 'content' key shouldn't crash
        msgs = [{"role": "user"}, _msg("assistant", "hi")]
        result = pack_verbatim_window(msgs, 1000)
        assert len(result) == 2

    def test_handles_none_content(self):
        msgs = [_msg("user", None), _msg("assistant", "hi")]  # type: ignore[arg-type]
        result = pack_verbatim_window(msgs, 1000)
        assert len(result) == 2

    def test_token_budget_enforced(self):
        # 20 small messages, budget for ~5
        msgs = [_msg("user", "ABCDEF") for _ in range(20)]  # 6 chars → 2 tokens each
        result = pack_verbatim_window(msgs, 12)  # ~5-6 messages of 2 tokens
        total = sum(count_tokens(m["content"]) for m in result)
        # Either we hit the budget (total ≤ budget) or we kept exactly 1
        # (always-keep-last exception). For non-trivial input we expect the
        # former.
        assert total <= 12 or len(result) == 1
