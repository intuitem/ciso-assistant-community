"""Tests for providers.py — thinking token parsing and streaming."""


class TestFilterThinkingTokens:
    def test_no_think_tags(self):
        from chat.providers import filter_thinking_tokens

        tokens = ["Hello", " world", "!"]
        result = list(filter_thinking_tokens(iter(tokens)))
        assert result == [("token", "Hello"), ("token", " world"), ("token", "!")]

    def test_think_block_single_token(self):
        from chat.providers import filter_thinking_tokens

        tokens = ["<think>reasoning here</think>actual response"]
        result = list(filter_thinking_tokens(iter(tokens)))
        assert ("thinking", "reasoning here") in result
        assert ("token", "actual response") in result

    def test_think_block_across_tokens(self):
        from chat.providers import filter_thinking_tokens

        tokens = ["<think>", "reasoning", " here", "</think>", "response"]
        result = list(filter_thinking_tokens(iter(tokens)))
        contents = {"thinking": [], "token": []}
        for t, c in result:
            contents[t].append(c)
        assert len(contents["thinking"]) > 0
        assert "response" in "".join(contents["token"])

    def test_no_tags_passthrough(self):
        from chat.providers import filter_thinking_tokens

        tokens = ["Just", " a", " normal", " response"]
        result = list(filter_thinking_tokens(iter(tokens)))
        assert all(t == "token" for t, _ in result)
        assert "".join(c for _, c in result) == "Just a normal response"

    def test_empty_stream(self):
        from chat.providers import filter_thinking_tokens

        result = list(filter_thinking_tokens(iter([])))
        assert result == []

    def test_think_at_start_then_content(self):
        from chat.providers import filter_thinking_tokens

        tokens = ["<think>let me think</think>Here is the answer"]
        result = list(filter_thinking_tokens(iter(tokens)))
        thinking = "".join(c for t, c in result if t == "thinking")
        content = "".join(c for t, c in result if t == "token")
        assert "let me think" in thinking
        assert "Here is the answer" in content


class TestStripThinking:
    def test_removes_think_block(self):
        from chat.providers import strip_thinking

        assert strip_thinking("<think>internal</think>Final") == "Final"

    def test_no_think_block(self):
        from chat.providers import strip_thinking

        assert strip_thinking("Just normal") == "Just normal"

    def test_multiple_think_blocks(self):
        from chat.providers import strip_thinking

        result = strip_thinking("<think>a</think>mid<think>b</think>end")
        assert "a" not in result
        assert "b" not in result
        assert "end" in result


class TestMergeThinkingStream:
    def test_thinking_then_content(self):
        from chat.providers import _merge_thinking_stream

        raw = iter([("thinking", "hmm"), ("thinking", "ok"), ("raw", "answer")])
        result = list(_merge_thinking_stream(raw))
        assert ("thinking", "hmm") in result
        assert ("thinking", "ok") in result
        assert ("token", "answer") in result

    def test_content_only(self):
        from chat.providers import _merge_thinking_stream

        raw = iter([("raw", "just"), ("raw", " content")])
        result = list(_merge_thinking_stream(raw))
        assert all(t == "token" for t, _ in result)
        assert "".join(c for _, c in result) == "just content"

    def test_content_with_think_tags(self):
        from chat.providers import _merge_thinking_stream

        raw = iter([("raw", "<think>inner</think>outer")])
        result = list(_merge_thinking_stream(raw))
        thinking = "".join(c for t, c in result if t == "thinking")
        content = "".join(c for t, c in result if t == "token")
        assert "inner" in thinking
        assert "outer" in content

    def test_empty_stream(self):
        from chat.providers import _merge_thinking_stream

        result = list(_merge_thinking_stream(iter([])))
        assert result == []

    def test_content_streams_progressively(self):
        """Content tokens must not be buffered until stream end."""
        from chat.providers import _merge_thinking_stream

        raw = iter(
            [
                ("thinking", "t1"),
                ("thinking", "t2"),
                ("raw", "c1"),
                ("raw", "c2"),
                ("raw", "c3"),
            ]
        )
        result = list(_merge_thinking_stream(raw))
        content_tokens = [c for t, c in result if t == "token"]
        # All 3 content tokens should be present (not merged into one)
        assert len(content_tokens) >= 3


class TestStubLLM:
    def test_stream_returns_tuples(self):
        from chat.providers import StubLLM

        llm = StubLLM()
        result = list(llm.stream("hello", "context"))
        assert len(result) == 1
        token_type, content = result[0]
        assert token_type == "token"
        assert "context" in content

    def test_tool_call_returns_none(self):
        from chat.providers import StubLLM

        assert StubLLM().tool_call("prompt", []) is None
