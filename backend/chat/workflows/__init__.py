"""
Agentic workflow engine for complex, multi-step chat tasks.

Architecture:
    - Workflows register as LLM tools — the LLM picks them via intent
      detection, not regex. Works in any language.
    - The router adds workflow tools to the LLM's tool list based on
      page context (e.g., suggest_controls only appears on requirement pages).
    - Each workflow is a Python class with run() yielding SSE events.
    - Adding a new workflow = new file + one line in registry.

Workflows vs tool-calling:
    - Tool-calling: single ORM query, create, or attach. LLM picks the tool.
    - Workflows: multi-step orchestration (retrieve → reason → propose).
      Deterministic code drives the steps; LLM only handles reasoning.
"""

from .base import Workflow
from .registry import get_workflow_tools, get_workflow_by_tool_name

__all__ = ["Workflow", "get_workflow_tools", "get_workflow_by_tool_name"]
