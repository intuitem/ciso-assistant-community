"""
Workflow registry.

Workflows register as tools so the LLM picks them via intent detection —
no regex, no keyword matching, works in any language.
"""

from chat.page_context import ParsedContext
from .base import Workflow


def _get_workflows() -> list[Workflow]:
    """
    Lazy-load workflow instances to avoid import-time Django app issues.
    """
    from .suggest_controls import SuggestControlsWorkflow
    from .risk_treatment import RiskTreatmentWorkflow
    from .evidence_guidance import EvidenceGuidanceWorkflow
    from .ebios_rm_draft import EbiosRMAssistWorkflow

    return [
        SuggestControlsWorkflow(),
        RiskTreatmentWorkflow(),
        EvidenceGuidanceWorkflow(),
        EbiosRMAssistWorkflow(),
    ]


def get_available_workflows(
    parsed_context: ParsedContext | None,
) -> list[Workflow]:
    """Return workflows available for the current page context."""
    return [w for w in _get_workflows() if w.is_available(parsed_context)]


def get_workflow_tools(parsed_context: ParsedContext | None) -> list[dict]:
    """
    Build tool definitions for available workflows.
    These are added to the LLM's tool list so it can select them.
    """
    tools = []
    for workflow in get_available_workflows(parsed_context):
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": f"workflow_{workflow.name}",
                    "description": workflow.description,
                    "parameters": {
                        "type": "object",
                        "properties": workflow.get_tool_parameters(),
                        "required": [],
                    },
                },
            }
        )
    return tools


def get_workflow_by_tool_name(tool_name: str) -> Workflow | None:
    """Resolve a tool name like 'workflow_suggest_controls' to its Workflow."""
    if not tool_name.startswith("workflow_"):
        return None
    workflow_name = tool_name[len("workflow_") :]
    for workflow in _get_workflows():
        if workflow.name == workflow_name:
            return workflow
    return None
