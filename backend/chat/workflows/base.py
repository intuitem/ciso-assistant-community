"""
Base class for agentic workflows.

A workflow is a multi-step task that orchestrates data retrieval and LLM reasoning.
Each step is just a Python method call — no DAGs, no state machines.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Iterator

from chat.page_context import ParsedContext

logger = logging.getLogger(__name__)

# Appended to all workflow LLM prompts
LANGUAGE_INSTRUCTION = (
    "\n\nRespond in the same language the user writes in. "
    "If the input mixes languages, respond in English."
)


@dataclass
class SSEEvent:
    """A single Server-Sent Event to stream to the frontend."""

    type: str  # "token", "thinking", "pending_action", "done", "error"
    content: str | dict = ""

    def encode(self) -> str:
        """Encode as SSE data line."""
        if isinstance(self.content, dict):
            data = json.dumps({"type": self.type, **self.content})
        else:
            data = json.dumps({"type": self.type, "content": self.content})
        return f"data: {data}\n\n"


@dataclass
class WorkflowContext:
    """Everything a workflow needs to execute."""

    user_message: str
    parsed_context: ParsedContext | None
    accessible_folder_ids: list[str]
    llm: object  # LLM provider instance
    history: list[dict] = field(default_factory=list)


class Workflow:
    """
    Base class for agentic workflows.

    Subclasses implement:
        - name: short identifier
        - match(): should this workflow handle the request?
        - run(): yield SSEEvents as the workflow executes

    The run() method is a generator — it yields SSEEvents that are streamed
    directly to the frontend. This means each step's output is visible
    to the user as it happens.
    """

    name: str = "base"
    description: str = ""
    # Page context model_keys where this workflow is available
    context_models: list[str] = []

    def is_available(self, parsed_context: ParsedContext | None) -> bool:
        """
        Is this workflow available given the current page context?
        Used to filter which workflow tools the LLM sees.
        """
        if not self.context_models:
            return True
        if not parsed_context or not parsed_context.object_id:
            return False
        return parsed_context.model_key in self.context_models

    def get_tool_parameters(self) -> dict:
        """
        Return tool parameter properties for the LLM tool schema.
        Override in subclasses to add workflow-specific parameters.
        """
        return {}

    def run(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        """
        Execute the workflow, yielding SSEEvents.
        Each step is just code — Python control flow IS the orchestration.
        """
        raise NotImplementedError

    def _thinking(self, message: str) -> SSEEvent:
        """Emit a thinking event (shown in collapsible block)."""
        return SSEEvent(type="thinking", content=message)

    def _token(self, text: str) -> SSEEvent:
        """Emit a text token (appended to response)."""
        return SSEEvent(type="token", content=text)

    def _pending_action(self, action_data: dict) -> SSEEvent:
        """Emit a pending action (shown as confirmation cards)."""
        return SSEEvent(type="pending_action", content=action_data)

    def _error(self, message: str) -> SSEEvent:
        """Emit an error event."""
        return SSEEvent(type="error", content=message)

    def _parse_recommended_indices(
        self, llm_response: str, candidates: list[dict]
    ) -> list[dict]:
        """
        Parse the JSON block from the LLM response to get recommended items.

        Expects the LLM to have output a block like:
            ```json
            {"recommended": [1, 3, 5]}
            ```
        where numbers are 1-based indices into the candidates list.
        """
        try:
            # Find JSON in code fence
            match = re.search(r"```json\s*(\{.*?\})\s*```", llm_response, re.DOTALL)
            if not match:
                # Try without code fence
                match = re.search(
                    r'\{\s*"recommended"\s*:\s*\[[\d\s,]*\]\s*\}', llm_response
                )
                if not match:
                    logger.warning("Could not find recommended JSON in LLM response")
                    return []
                raw = match.group(0)
            else:
                raw = match.group(1)

            data = json.loads(raw)
            indices = data.get("recommended", [])
            result = []
            for idx in indices:
                if isinstance(idx, int) and 1 <= idx <= len(candidates):
                    result.append(candidates[idx - 1])
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse recommended items: %s", e)
            return []

    def _stream_llm(
        self,
        ctx: WorkflowContext,
        prompt: str,
        context: str = "",
        skip_language_hint: bool = False,
    ) -> Iterator[SSEEvent]:
        """
        Stream LLM response tokens as SSEEvents.
        Handles both regular tokens and thinking tokens.
        Returns the full response text via a mutable list (last element).
        """
        if not skip_language_hint:
            prompt = prompt + LANGUAGE_INSTRUCTION
        full_response = []
        for token_type, token in ctx.llm.stream(prompt, context, history=ctx.history):
            full_response.append(token if token_type == "token" else "")
            yield SSEEvent(type=token_type, content=token)
        # Store the complete response for the caller
        self._last_response = "".join(full_response)
