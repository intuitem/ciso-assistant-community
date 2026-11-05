from unittest.mock import patch

import pytest

from core.models import Incident
from iam.models import Folder


class FakeLLM:
    """Routes with the scripted tool calls and records what it was given."""

    system_prompt = ""

    def __init__(self, *calls):
        self.calls = list(calls)
        self.prompts = []
        self.context = None

    def tool_call(self, prompt, tools, history=None):
        self.prompts.append(prompt)
        return self.calls.pop(0) if self.calls else None

    def stream(self, prompt, context, history=None, directives=""):
        self.context = context
        yield "token", "ok"

    def generate(self, *args, **kwargs):
        return ""


def ask(client, llm, content):
    session = client.post("/api/chat/sessions/", {}, format="json").json()
    with patch("chat.views.get_llm", return_value=llm):
        res = client.post(
            f"/api/chat/sessions/{session['id']}/message/",
            {"content": content},
            format="json",
        )
        b"".join(res.streaming_content)


def incidents_with(status):
    return {
        "name": "query_objects",
        "arguments": {"model": "incident", "action": "list", "status": [status]},
    }


@pytest.mark.django_db
def test_unknown_filter_value_gets_one_correction_round(authenticated_client):
    root = Folder.get_root_folder()
    Incident.objects.create(name="lost laptop", folder=root, status="new")
    Incident.objects.create(name="old outage", folder=root, status="closed")
    llm = FakeLLM(incidents_with("open"), incidents_with("new"))
    ask(authenticated_client, llm, "Which incidents are still open?")
    # the second routing call is told why the first matched nothing
    assert len(llm.prompts) == 2 and "Valid values" in llm.prompts[1]
    assert "lost laptop" in llm.context and "old outage" not in llm.context


@pytest.mark.django_db
def test_valid_filter_is_not_retried(authenticated_client):
    Incident.objects.create(
        name="lost laptop", folder=Folder.get_root_folder(), status="new"
    )
    llm = FakeLLM(incidents_with("new"))
    ask(authenticated_client, llm, "Which incidents are new?")
    assert len(llm.prompts) == 1 and "lost laptop" in llm.context
