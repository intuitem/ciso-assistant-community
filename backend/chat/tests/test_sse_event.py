"""Tests for SSEEvent encoding."""

import json


class TestSSEEvent:
    def test_string_content(self):
        from chat.workflows.base import SSEEvent

        event = SSEEvent(type="token", content="hello")
        encoded = event.encode()
        assert encoded.startswith("data: ")
        assert encoded.endswith("\n\n")
        data = json.loads(encoded[6:].strip())
        assert data == {"type": "token", "content": "hello"}

    def test_dict_content_spread(self):
        from chat.workflows.base import SSEEvent

        event = SSEEvent(
            type="pending_action",
            content={
                "action": "create",
                "model_key": "asset",
                "items": [{"name": "x"}],
            },
        )
        data = json.loads(event.encode()[6:].strip())
        assert data["type"] == "pending_action"
        assert data["action"] == "create"
        assert data["model_key"] == "asset"

    def test_pending_choice_encoding(self):
        from chat.workflows.base import SSEEvent

        event = SSEEvent(
            type="pending_choice",
            content={
                "field": "risk_matrix",
                "label": "Select a matrix",
                "items": [{"id": "1", "name": "5x5"}],
            },
        )
        data = json.loads(event.encode()[6:].strip())
        assert data["type"] == "pending_choice"
        assert data["field"] == "risk_matrix"
        assert data["items"][0]["name"] == "5x5"

    def test_thinking_event(self):
        from chat.workflows.base import SSEEvent

        data = json.loads(
            SSEEvent(type="thinking", content="reasoning...").encode()[6:].strip()
        )
        assert data == {"type": "thinking", "content": "reasoning..."}

    def test_empty_content(self):
        from chat.workflows.base import SSEEvent

        data = json.loads(SSEEvent(type="token").encode()[6:].strip())
        assert data == {"type": "token", "content": ""}
