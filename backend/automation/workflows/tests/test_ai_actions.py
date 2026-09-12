"""ai_extract / ai_generate.

Three properties are load-bearing: output is schema-checked, an unreachable
provider fails the node instead of degrading to StubLLM, and an AI answer
cannot set a fenced field.

Huey is not immediate in tests: the `dispatch` fixture captures the enqueue and
`dispatch.run()` executes the task body synchronously.
"""

import uuid

import pytest

from chat.providers import NoLLMAvailable, StubLLM
from iam.models import Folder
from automation.workflows import actions as workflow_actions
from automation.workflows import tasks as workflow_tasks
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.import_export import export_workflow, import_workflow
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowToken,
    WorkflowVersion,
)
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.validation import validate_graph

SEVERITY_SCHEMA = {
    "type": "object",
    "properties": {"severity": {"type": "string", "enum": ["low", "high"]}},
    "required": ["severity"],
}


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "source": source["id"],
        "target": target["id"],
        **kwargs,
    }


def ai_flow(config, ref="classify", output_mapping=None, variables=None):
    workflow = Workflow.objects.create(name="AI flow", folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    action = node(
        "action",
        ref=ref,
        action_config=config,
        output_mapping=output_mapping or {},
    )
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, action, end],
            "edges": [edge(start, action), edge(action, end)],
            "variables": [
                {"id": str(uuid.uuid4()), **variable} for variable in (variables or [])
            ],
        },
    )
    return version


def error_messages(instance):
    return [log.message or "" for log in instance.logs.filter(event_type="error")]


class FakeLLM:
    """Records the call and replays queued completions."""

    def __init__(self, *completions):
        self.completions = list(completions)
        self.calls = []

    def generate(self, prompt, context, history=None, directives="", **kwargs):  # noqa: ARG002
        self.calls.append({"prompt": prompt, "context": context, **kwargs})
        return self.completions.pop(0) if self.completions else ""


@pytest.fixture
def dispatch(monkeypatch):
    """Capture ai_call_task enqueues; run(i) executes the task body."""
    captured = []
    call = workflow_tasks.ai_call_task.call_local
    # DeferredAiTask binds ai_call_task from the actions module, so that
    # binding is the one to patch.
    monkeypatch.setattr(
        workflow_actions, "ai_call_task", lambda **kwargs: captured.append(kwargs)
    )

    class Dispatch:
        calls = captured

        @staticmethod
        def run(index=0):
            call(**captured[index])

    return Dispatch


@pytest.fixture
def llm(monkeypatch):
    """Install a FakeLLM in place of the real provider. install(*completions)
    patches get_llm_strict where the task imports it."""

    def install(*completions):
        fake = FakeLLM(*completions)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        return fake

    return install


@pytest.mark.django_db
class TestAiExtract:
    def test_inference_runs_outside_the_engine_transaction(
        self, dispatch, django_capture_on_commit_callbacks
    ):
        version = ai_flow(
            {"type": "ai_extract", "prompt": "Classify", "schema": SEVERITY_SCHEMA}
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        # Parked, no call made: that happens in the task, after commit.
        assert instance.status == WorkflowInstance.Status.ACTIVE
        token = instance.tokens.get(current_node__type=WorkflowNode.Type.ACTION)
        assert token.status == WorkflowToken.Status.WAITING
        assert dispatch.calls[0]["token_id"] == str(token.id)

    def test_validated_object_becomes_the_node_output(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        llm('{"severity": "high"}')
        version = ai_flow(
            {
                "type": "ai_extract",
                "prompt": "Classify this finding",
                "input": "The database is exposed to the internet",
                "schema": SEVERITY_SCHEMA,
            },
            output_mapping={"verdict": "severity"},
            variables=[{"key": "verdict", "type": "string", "default_value": ""}],
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["classify"] == {"severity": "high"}
        # output_mapping ran, so a condition node could branch on it.
        assert instance.variables["verdict"] == "high"
        assert instance.logs.get(event_type="action_executed").data == {
            "severity": "high"
        }

    def test_schema_and_own_system_prompt_reach_the_provider(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        fake = llm('{"severity": "low"}')
        version = ai_flow(
            {
                "type": "ai_extract",
                "prompt": "Classify",
                "input": "quiet",
                "schema": SEVERITY_SCHEMA,
            }
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        call = fake.calls[0]
        assert call["schema"] == SEVERITY_SCHEMA
        # Not the chat persona, which operators can rewrite.
        assert call["system_prompt"] == workflow_actions.AI_SYSTEM_PROMPT
        assert call["context"] == "quiet"

    def test_templated_prompt_and_input_are_rendered(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        fake = llm('{"severity": "low"}')
        version = ai_flow(
            {
                "type": "ai_extract",
                "prompt": "Classify for {{customer}}",
                "input": "{{detail}}",
                "schema": SEVERITY_SCHEMA,
            },
            variables=[
                {"key": "customer", "type": "string", "default_value": "Acme"},
                {"key": "detail", "type": "string", "default_value": "port 5432 open"},
            ],
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        assert fake.calls[0]["prompt"] == "Classify for Acme"
        assert fake.calls[0]["context"] == "port 5432 open"

    def test_output_off_schema_retries_then_fails_the_node(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        # Both draws are off-schema: 'critical' is not in the enum.
        fake = llm('{"severity": "critical"}', '{"severity": "critical"}')
        version = ai_flow(
            {
                "type": "ai_extract",
                "prompt": "Classify",
                "schema": SEVERITY_SCHEMA,
                "max_attempts": 2,
            }
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        # Re-draws before spending a node retry.
        assert len(fake.calls) == 2
        assert not instance.logs.filter(event_type="action_executed").exists()
        assert any("does not match the schema" in m for m in error_messages(instance))

    def test_a_later_draw_that_validates_is_accepted(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        fake = llm("not json at all", '{"severity": "high"}')
        version = ai_flow(
            {
                "type": "ai_extract",
                "prompt": "Classify",
                "schema": SEVERITY_SCHEMA,
                "max_attempts": 2,
            }
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["classify"] == {"severity": "high"}

    def test_unreachable_provider_fails_the_node(
        self, dispatch, monkeypatch, django_capture_on_commit_callbacks
    ):
        def unavailable():
            raise NoLLMAvailable("no LLM provider reachable (provider: ollama)")

        monkeypatch.setattr("chat.providers.get_llm_strict", unavailable)
        version = ai_flow(
            {"type": "ai_extract", "prompt": "Classify", "schema": SEVERITY_SCHEMA}
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        # Never an ACTION_EXECUTED row carrying stub text.
        assert not instance.logs.filter(event_type="action_executed").exists()
        assert any("no AI provider is reachable" in m for m in error_messages(instance))

    def test_get_llm_strict_refuses_the_stub(self, monkeypatch):
        monkeypatch.setattr("chat.providers.get_llm", lambda: StubLLM())
        from chat import providers

        with pytest.raises(NoLLMAvailable):
            providers.get_llm_strict()

    def test_provider_error_message_stays_out_of_the_run_log(
        self, dispatch, monkeypatch, django_capture_on_commit_callbacks
    ):
        class Exploding:
            def generate(self, *args, **kwargs):
                # A real httpx error carries the endpoint URL.
                raise RuntimeError("POST http://secret-host:1234/v1 failed")

        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: Exploding())
        version = ai_flow(
            {"type": "ai_extract", "prompt": "Classify", "schema": SEVERITY_SCHEMA}
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        messages = " ".join(error_messages(instance))
        assert "secret-host" not in messages
        assert "the AI provider call failed" in messages

    def test_duplicate_task_delivery_is_ignored(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        fake = llm('{"severity": "high"}', '{"severity": "low"}')
        version = ai_flow(
            {"type": "ai_extract", "prompt": "Classify", "schema": SEVERITY_SCHEMA}
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        dispatch.run()
        instance.refresh_from_db()
        # The dispatch claim is exclusive.
        assert len(fake.calls) == 1
        assert instance.logs.filter(event_type="action_executed").count() == 1

    def test_oversized_input_is_truncated_and_says_so(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        fake = llm('{"severity": "low"}')
        version = ai_flow(
            {
                "type": "ai_extract",
                "prompt": "Classify",
                "input": "{{detail}}",
                "schema": SEVERITY_SCHEMA,
            },
            variables=[
                {
                    "key": "detail",
                    "type": "string",
                    "default_value": "x" * (workflow_actions.AI_INPUT_MAX_CHARS + 500),
                }
            ],
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert len(fake.calls[0]["context"]) == workflow_actions.AI_INPUT_MAX_CHARS
        # Visible rather than silent.
        assert instance.node_outputs["classify"]["_input_truncated"] is True


@pytest.mark.django_db
class TestAiGenerate:
    def test_prose_output(self, dispatch, llm, django_capture_on_commit_callbacks):
        fake = llm("  The control lapsed in June.  ")
        version = ai_flow(
            {
                "type": "ai_generate",
                "prompt": "Draft an observation",
                "input": "overdue since June",
                "max_words": 50,
            }
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["classify"] == {
            "text": "The control lapsed in June."
        }
        assert "at most 50 words" in fake.calls[0]["prompt"]
        assert fake.calls[0].get("schema") is None

    def test_runaway_output_is_capped(
        self, dispatch, llm, django_capture_on_commit_callbacks
    ):
        llm("word " * 5000)
        version = ai_flow(
            {"type": "ai_generate", "prompt": "Draft"},
            output_mapping={"draft": "text"},
            variables=[{"key": "draft", "type": "string"}],
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        # max_words is a prompt instruction, not a guarantee. Asserted on the
        # variable, not node_outputs: the engine caps node-output leaves at
        # MAX_LEAF_CHARS itself, while output_mapping copies uncapped.
        assert len(instance.variables["draft"]) == workflow_actions.AI_TEXT_MAX_CHARS
        assert len(instance.node_outputs["classify"]["text"]) < 1100


@pytest.mark.django_db
class TestAiCallBudget:
    def test_budget_exhausted_fails_the_node(
        self, settings, dispatch, llm, django_capture_on_commit_callbacks
    ):
        settings.WORKFLOW_AI_MAX_CALLS_PER_RUN = 1
        llm('{"severity": "high"}', '{"severity": "low"}')
        workflow = Workflow.objects.create(
            name="Two AI steps", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        first = node(
            "action",
            ref="first",
            action_config={
                "type": "ai_extract",
                "prompt": "Classify",
                "schema": SEVERITY_SCHEMA,
            },
        )
        second = node(
            "action",
            ref="second",
            action_config={
                "type": "ai_extract",
                "prompt": "Classify again",
                "schema": SEVERITY_SCHEMA,
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, first, second, end],
                "edges": [
                    edge(start, first),
                    edge(first, second),
                    edge(second, end),
                ],
                "variables": [],
            },
        )
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        # The first step spent the budget; the second refuses before calling.
        assert instance.node_outputs["first"] == {"severity": "high"}
        assert "second" not in instance.node_outputs
        assert any(
            "used its 1 AI calls" in message for message in error_messages(instance)
        )

    def test_budget_refusal_is_not_retried(
        self, settings, dispatch, llm, django_capture_on_commit_callbacks
    ):
        settings.WORKFLOW_AI_MAX_CALLS_PER_RUN = 0
        llm('{"severity": "high"}')
        version = ai_flow(
            {"type": "ai_extract", "prompt": "Classify", "schema": SEVERITY_SCHEMA}
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        instance.refresh_from_db()
        token = instance.tokens.get(current_node__ref="classify")
        # Fatal, not retryable: a retry would make the same refused call.
        assert token.status == WorkflowToken.Status.ERROR
        assert token.retry_count == 0
        assert not dispatch.calls


@pytest.mark.django_db
class TestAiValueFencing:
    """An AI answer may route a branch or fill free text, never a fenced
    field."""

    def published(self, update_fields, output_mapping=None):
        workflow = Workflow.objects.create(
            name="Fencing", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        classify = node(
            "action",
            ref="classify",
            action_config={
                "type": "ai_extract",
                "prompt": "Classify",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                    "required": ["status"],
                },
            },
            output_mapping=output_mapping or {},
        )
        write = node(
            "action",
            ref="write",
            action_config={
                "type": "update_object",
                "model": "evidence",
                "id": "{{evidence_id}}",
                "fields": update_fields,
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, classify, write, end],
                "edges": [
                    edge(start, classify),
                    edge(classify, write),
                    edge(write, end),
                ],
                "variables": [
                    {"id": str(uuid.uuid4()), "key": key, "type": "string"}
                    for key in ("evidence_id", *(output_mapping or {}))
                ],
            },
        )
        return version

    def codes(self, version):
        return {error["code"] for error in validate_graph(version)}

    def test_ai_output_cannot_set_a_fenced_field(self):
        version = self.published({"status": "{{nodes.classify.status}}"})
        assert "action_update_ai_value_on_fenced_field" in self.codes(version)

    def test_ai_variable_cannot_set_a_fenced_field(self):
        version = self.published(
            {"status": "{{verdict}}"}, output_mapping={"verdict": "status"}
        )
        assert "action_update_ai_value_on_fenced_field" in self.codes(version)

    def test_ai_output_may_fill_a_free_text_field(self):
        version = self.published({"description": "{{nodes.classify.status}}"})
        assert "action_update_ai_value_on_fenced_field" not in self.codes(version)

    def test_a_literal_still_sets_a_fenced_field(self):
        # The supported pattern: branch on the AI answer, write the literal.
        version = self.published({"status": "expired"})
        assert "action_update_ai_value_on_fenced_field" not in self.codes(version)


@pytest.mark.django_db
class TestAiConfigValidation:
    def graph_codes(self, config, output_mapping=None):
        version = ai_flow(config, output_mapping=output_mapping)
        return {error["code"] for error in validate_graph(version)}

    def test_missing_prompt_is_refused(self):
        assert "action_ai_no_prompt" in self.graph_codes(
            {"type": "ai_extract", "schema": SEVERITY_SCHEMA}
        )

    def test_missing_schema_is_refused(self):
        assert "action_ai_no_schema" in self.graph_codes(
            {"type": "ai_extract", "prompt": "Classify"}
        )

    def test_non_object_schema_is_refused(self):
        assert "action_ai_schema_not_object" in self.graph_codes(
            {"type": "ai_extract", "prompt": "Classify", "schema": {"type": "array"}}
        )

    def test_invalid_schema_is_refused(self):
        assert "action_ai_bad_schema" in self.graph_codes(
            {"type": "ai_extract", "prompt": "Classify", "schema": {"type": "nope"}}
        )

    def test_output_mapping_off_the_schema_is_refused(self):
        assert "action_ai_unmapped_output" in self.graph_codes(
            {"type": "ai_extract", "prompt": "Classify", "schema": SEVERITY_SCHEMA},
            output_mapping={"verdict": "confidence"},
        )

    def test_a_sound_step_publishes(self):
        assert not self.graph_codes(
            {"type": "ai_extract", "prompt": "Classify", "schema": SEVERITY_SCHEMA},
            output_mapping={"verdict": "severity"},
        )

    def test_ai_generate_needs_no_schema(self):
        assert not self.graph_codes({"type": "ai_generate", "prompt": "Draft"})


@pytest.mark.django_db
class TestAiActionPortability:
    """action_config is free-form in workflow-v1.schema.json, so no version
    bump was needed; this pins that the nested schema survives anyway."""

    def test_ai_step_survives_export_and_import(self):
        version = ai_flow(
            {
                "type": "ai_extract",
                "prompt": "Classify",
                "input": "{{detail}}",
                "schema": SEVERITY_SCHEMA,
                "max_attempts": 3,
            },
            output_mapping={"verdict": "severity"},
            variables=[{"key": "verdict", "type": "string"}],
        )
        version.status = WorkflowVersion.Status.PUBLISHED
        version.save()
        document = export_workflow(version.workflow)
        # Same database, so the importer renames around the collision.
        imported, _warnings = import_workflow(document, Folder.get_root_folder())
        node = imported.versions.get().nodes.get(ref="classify")
        assert node.action_config["schema"] == SEVERITY_SCHEMA
        assert node.action_config["max_attempts"] == 3
        assert node.output_mapping == {"verdict": "severity"}
