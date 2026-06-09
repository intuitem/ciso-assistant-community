"""Tests for LiteLLMProvider — unit tests with mocked litellm."""

import json
import sys
import types
from types import SimpleNamespace
from unittest import mock

import pytest


def _make_litellm_stub():
    """Install a fake litellm module so LiteLLMProvider can import it."""
    fake = types.ModuleType("litellm")
    fake.completion = mock.MagicMock(name="litellm.completion")
    fake.RateLimitError = type("RateLimitError", (Exception,), {})
    fake.AuthenticationError = type("AuthenticationError", (Exception,), {})
    fake.NotFoundError = type("NotFoundError", (Exception,), {})
    fake.APIConnectionError = type("APIConnectionError", (Exception,), {})
    fake.Timeout = type("Timeout", (Exception,), {})
    sys.modules["litellm"] = fake
    return fake


_litellm = _make_litellm_stub()


def _mock_response(content="Hello", tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=None, message=message)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], usage=usage)


def _mock_tool_call_response(name="get_weather", arguments='{"city": "Paris"}'):
    func = SimpleNamespace(name=name, arguments=arguments)
    tc = SimpleNamespace(function=func)
    message = SimpleNamespace(content=None, tool_calls=[tc])
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _mock_stream_chunks(tokens):
    chunks = []
    for token in tokens:
        delta = SimpleNamespace(content=token, reasoning_content=None)
        choice = SimpleNamespace(delta=delta)
        chunks.append(SimpleNamespace(choices=[choice]))
    return iter(chunks)


def _mock_stream_chunks_with_thinking(thinking_tokens, content_tokens):
    chunks = []
    for t in thinking_tokens:
        delta = SimpleNamespace(content=None, reasoning_content=t)
        chunks.append(SimpleNamespace(choices=[SimpleNamespace(delta=delta)]))
    for c in content_tokens:
        delta = SimpleNamespace(content=c, reasoning_content=None)
        chunks.append(SimpleNamespace(choices=[SimpleNamespace(delta=delta)]))
    return iter(chunks)


class TestLiteLLMProviderInit:
    def test_default_model(self):
        from chat.providers import LiteLLMProvider
        llm = LiteLLMProvider()
        assert llm.model == "openai/gpt-4o-mini"

    def test_custom_model(self):
        from chat.providers import LiteLLMProvider
        llm = LiteLLMProvider(model="anthropic/claude-sonnet-4-6")
        assert llm.model == "anthropic/claude-sonnet-4-6"

    def test_api_key_forwarded_when_set(self):
        from chat.providers import LiteLLMProvider
        llm = LiteLLMProvider(api_key="sk-test-123")
        kwargs = llm._call_kwargs()
        assert kwargs["api_key"] == "sk-test-123"

    def test_api_key_omitted_when_empty(self):
        from chat.providers import LiteLLMProvider
        llm = LiteLLMProvider(api_key="")
        kwargs = llm._call_kwargs()
        assert "api_key" not in kwargs

    def test_api_base_forwarded_when_set(self):
        from chat.providers import LiteLLMProvider
        llm = LiteLLMProvider(api_base="http://localhost:4000")
        kwargs = llm._call_kwargs()
        assert kwargs["api_base"] == "http://localhost:4000"

    def test_api_base_omitted_when_empty(self):
        from chat.providers import LiteLLMProvider
        llm = LiteLLMProvider(api_base="")
        kwargs = llm._call_kwargs()
        assert "api_base" not in kwargs

    def test_drop_params_always_true(self):
        from chat.providers import LiteLLMProvider
        llm = LiteLLMProvider()
        kwargs = llm._call_kwargs()
        assert kwargs["drop_params"] is True


class TestLiteLLMProviderGenerate:
    def test_generate_returns_content(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_response("The answer is 4.")
        llm = LiteLLMProvider(model="openai/gpt-4o")
        result = llm.generate("What is 2+2?", context="math help")
        assert result == "The answer is 4."
        _litellm.completion.assert_called_once()
        call_kwargs = _litellm.completion.call_args
        assert call_kwargs.kwargs["model"] == "openai/gpt-4o"
        assert call_kwargs.kwargs["drop_params"] is True

    def test_generate_strips_thinking(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_response(
            "<think>let me reason</think>Final answer"
        )
        llm = LiteLLMProvider()
        result = llm.generate("test", context="")
        assert "let me reason" not in result
        assert "Final answer" in result

    def test_generate_passes_history(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_response("response")
        llm = LiteLLMProvider()
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        llm.generate("follow up", context="", history=history)
        messages = _litellm.completion.call_args.kwargs["messages"]
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    def test_generate_null_content_raises(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_response(content=None)
        llm = LiteLLMProvider()
        with pytest.raises((TypeError, AttributeError)):
            llm.generate("test", context="")

    def test_generate_auth_error_propagates(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.side_effect = _litellm.AuthenticationError("Invalid API key")
        llm = LiteLLMProvider()
        with pytest.raises(Exception, match="Invalid API key"):
            llm.generate("test", context="")
        _litellm.completion.side_effect = None

    def test_generate_rate_limit_propagates(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.side_effect = _litellm.RateLimitError("429 Too Many Requests")
        llm = LiteLLMProvider()
        with pytest.raises(Exception, match="429"):
            llm.generate("test", context="")
        _litellm.completion.side_effect = None

    def test_generate_timeout_propagates(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.side_effect = _litellm.Timeout("Request timed out")
        llm = LiteLLMProvider()
        with pytest.raises(Exception, match="timed out"):
            llm.generate("test", context="")
        _litellm.completion.side_effect = None

    def test_generate_not_found_propagates(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.side_effect = _litellm.NotFoundError("Model not found")
        llm = LiteLLMProvider()
        with pytest.raises(Exception, match="not found"):
            llm.generate("test", context="")
        _litellm.completion.side_effect = None


class TestLiteLLMProviderStream:
    def test_stream_yields_tokens(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_stream_chunks(["Hello", " world"])
        llm = LiteLLMProvider()
        result = list(llm.stream("test", context=""))
        content = "".join(c for _, c in result if _ == "token")
        assert "Hello" in content
        assert "world" in content

    def test_stream_with_thinking(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_stream_chunks_with_thinking(
            ["hmm", " ok"], ["answer"]
        )
        llm = LiteLLMProvider()
        result = list(llm.stream("test", context=""))
        thinking = [c for t, c in result if t == "thinking"]
        tokens = [c for t, c in result if t == "token"]
        assert len(thinking) > 0
        assert len(tokens) > 0

    def test_stream_empty(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = iter([])
        llm = LiteLLMProvider()
        result = list(llm.stream("test", context=""))
        assert result == []

    def test_stream_passes_stream_true(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = iter([])
        llm = LiteLLMProvider()
        list(llm._raw_stream("test", context=""))
        assert _litellm.completion.call_args.kwargs["stream"] is True


class TestLiteLLMProviderToolCall:
    def test_tool_call_returns_parsed_result(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_tool_call_response(
            name="get_weather", arguments='{"city": "Paris"}'
        )
        llm = LiteLLMProvider()
        result = llm.tool_call("Weather in Paris?", tools=[{"type": "function"}])
        assert result == {"name": "get_weather", "arguments": {"city": "Paris"}}

    def test_tool_call_no_tools_returns_none(self):
        from chat.providers import LiteLLMProvider
        response = _mock_response(content="I can't call tools")
        _litellm.completion.return_value = response
        llm = LiteLLMProvider()
        result = llm.tool_call("test", tools=[])
        assert result is None

    def test_tool_call_dict_arguments(self):
        from chat.providers import LiteLLMProvider
        func = SimpleNamespace(name="search", arguments={"query": "test"})
        tc = SimpleNamespace(function=func)
        message = SimpleNamespace(content=None, tool_calls=[tc])
        _litellm.completion.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=message)]
        )
        llm = LiteLLMProvider()
        result = llm.tool_call("search test", tools=[{"type": "function"}])
        assert result == {"name": "search", "arguments": {"query": "test"}}

    def test_tool_call_malformed_json_arguments(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.return_value = _mock_tool_call_response(
            name="func", arguments="not valid json"
        )
        llm = LiteLLMProvider()
        result = llm.tool_call("test", tools=[{"type": "function"}])
        assert result == {"name": "func", "arguments": {}}

    def test_tool_call_exception_returns_none(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.side_effect = _litellm.APIConnectionError("Connection failed")
        llm = LiteLLMProvider()
        result = llm.tool_call("test", tools=[])
        assert result is None
        _litellm.completion.side_effect = None

    def test_tool_call_rate_limit_returns_none(self):
        from chat.providers import LiteLLMProvider
        _litellm.completion.side_effect = _litellm.RateLimitError("429")
        llm = LiteLLMProvider()
        result = llm.tool_call("test", tools=[])
        assert result is None
        _litellm.completion.side_effect = None
