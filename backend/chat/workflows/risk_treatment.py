"""
Risk Treatment workflow.

Context: User is on a risk scenario page and asks how to mitigate/treat
the risk or what controls to apply.

Steps:
    1. Fetch risk scenario details — threats, assets, current level (deterministic)
    2. Search existing controls that address similar risks (deterministic)
    3. LLM evaluates and recommends treatment approach (reasoning)
    4. Emit attach proposals for matching controls (deterministic)
"""

import structlog
from typing import Iterator

from django.apps import apps
from django.db.models import Q

from chat.page_context import ParsedContext
from .base import Workflow, WorkflowContext, SSEEvent

logger = structlog.get_logger(__name__)


class RiskTreatmentWorkflow(Workflow):
    name = "risk_treatment"
    description = (
        "Suggest how to treat the current risk scenario — recommend a treatment "
        "approach (mitigate, accept, avoid, transfer) and propose controls to "
        "reduce the risk. Use this when the user asks how to mitigate, treat, "
        "reduce, or address the current risk scenario, or what controls to add. "
        "Works in any language."
    )
    context_models = ["risk_scenario"]

    def run(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        # Step 1: Fetch risk scenario details
        yield self._thinking("Analyzing the risk scenario...")

        scenario_info = self._fetch_scenario(ctx)
        if not scenario_info:
            yield self._token(
                "I couldn't find the risk scenario details. "
                "Please make sure you're on a risk scenario page."
            )
            return

        yield self._thinking(
            f"Risk: {scenario_info['name']}\n"
            f"Threats: {', '.join(scenario_info['threats']) or 'none specified'}\n"
            f"Assets: {', '.join(scenario_info['assets']) or 'none specified'}\n"
            f"Searching for relevant controls..."
        )

        # Step 2: Search for candidate controls
        candidates = self._search_controls(ctx, scenario_info)
        already_attached = scenario_info.get("existing_control_ids", set())

        new_candidates = [c for c in candidates if c["id"] not in already_attached]

        yield self._thinking(
            f"Found {len(candidates)} candidate controls, "
            f"{len(already_attached)} already attached, "
            f"{len(new_candidates)} new candidates."
        )

        # Step 3: LLM reasons about treatment
        ranking_prompt = self._build_treatment_prompt(scenario_info, new_candidates)
        yield from self._stream_llm(ctx, ranking_prompt)

        # Step 4: Parse LLM recommendations and emit attach proposals
        if new_candidates:
            recommended = self._parse_recommended_indices(
                getattr(self, "_last_response", ""), new_candidates
            )
            if not recommended:
                return

            from chat.tools import MODEL_MAP

            parent_info = MODEL_MAP.get("risk_scenario")
            related_info = MODEL_MAP.get("applied_control")
            if parent_info and related_info:
                proposal = {
                    "type": "pending_action",
                    "action": "attach",
                    "parent_model_key": "risk_scenario",
                    "parent_id": ctx.parsed_context.object_id,
                    "parent_url_slug": parent_info[3],
                    "m2m_field": "applied_controls",
                    "related_model_key": "applied_control",
                    "related_display": related_info[2],
                    "items": [{"id": c["id"], "name": c["name"]} for c in recommended],
                }
                yield self._pending_action(proposal)

    def _fetch_scenario(self, ctx: WorkflowContext) -> dict | None:
        """Fetch risk scenario with related threats, assets, and controls."""
        try:
            RiskScenario = apps.get_model("core", "RiskScenario")
            scenario = (
                RiskScenario.objects.prefetch_related(
                    "threats", "assets", "applied_controls", "existing_applied_controls"
                )
                .filter(
                    id=ctx.parsed_context.object_id,
                    risk_assessment__folder_id__in=ctx.accessible_folder_ids,
                )
                .first()
            )
            if not scenario:
                return None

            return {
                "name": str(scenario),
                "description": scenario.description or "",
                "ref_id": scenario.ref_id or "",
                "treatment": (
                    scenario.get_treatment_display()
                    if hasattr(scenario, "get_treatment_display")
                    else scenario.treatment or ""
                ),
                "current_level": scenario.current_level
                if scenario.current_level >= 0
                else None,
                "residual_level": scenario.residual_level
                if scenario.residual_level >= 0
                else None,
                "threats": [str(t) for t in scenario.threats.all()],
                "assets": [str(a) for a in scenario.assets.all()],
                "existing_control_ids": {
                    str(pk)
                    for pk in scenario.applied_controls.values_list("id", flat=True)
                }
                | {
                    str(pk)
                    for pk in scenario.existing_applied_controls.values_list(
                        "id", flat=True
                    )
                },
                "existing_controls": [
                    str(c)
                    for c in list(scenario.applied_controls.all())
                    + list(scenario.existing_applied_controls.all())
                ],
            }
        except Exception as e:
            logger.error("Failed to fetch risk scenario: %s", e)
            return None

    def _search_controls(self, ctx: WorkflowContext, scenario_info: dict) -> list[dict]:
        """Search for controls relevant to the scenario's threats and assets."""
        AppliedControl = apps.get_model("core", "AppliedControl")

        already_attached = scenario_info.get("existing_control_ids", set())
        qs = AppliedControl.objects.filter(folder_id__in=ctx.accessible_folder_ids)
        if already_attached:
            qs = qs.exclude(id__in=already_attached)

        # Build search from threats + assets + scenario description
        search_terms = []
        search_terms.extend(scenario_info.get("threats", []))
        search_terms.extend(scenario_info.get("assets", []))
        if scenario_info.get("description"):
            words = [w for w in scenario_info["description"].split() if len(w) > 3][:8]
            search_terms.extend(words)

        if search_terms:
            q = Q()
            for term in search_terms[:15]:
                q |= Q(name__icontains=term) | Q(description__icontains=term)
            qs = qs.filter(q)

        qs = qs.order_by("-status", "name")[:20]

        results = []
        for ctrl in qs:
            results.append(
                {
                    "id": str(ctrl.id),
                    "name": str(ctrl),
                    "ref_id": ctrl.ref_id or "",
                    "description": (
                        ctrl.description[:200] + "..."
                        if ctrl.description and len(ctrl.description) > 200
                        else ctrl.description or ""
                    ),
                    "status": (
                        ctrl.get_status_display()
                        if hasattr(ctrl, "get_status_display")
                        else ctrl.status or ""
                    ),
                    "category": (
                        ctrl.get_category_display()
                        if hasattr(ctrl, "get_category_display")
                        else ctrl.category or ""
                    ),
                }
            )
        return results

    def _build_treatment_prompt(
        self, scenario_info: dict, candidates: list[dict]
    ) -> str:
        """Build the prompt for risk treatment recommendation."""
        from django.conf import settings

        base_url = getattr(settings, "CISO_ASSISTANT_URL", "").rstrip("/")

        threats = ", ".join(scenario_info.get("threats", [])) or "not specified"
        assets = ", ".join(scenario_info.get("assets", [])) or "not specified"
        existing = ", ".join(scenario_info.get("existing_controls", [])) or "none"
        current_level = scenario_info.get("current_level")
        level_text = (
            f"Current risk level: {current_level}" if current_level is not None else ""
        )

        candidate_lines = []
        for i, c in enumerate(candidates, 1):
            ref = f"[{c['ref_id']}] " if c.get("ref_id") else ""
            desc = f" — {c['description']}" if c.get("description") else ""
            link = f"{base_url}/applied-controls/{c['id']}" if base_url else ""
            link_md = f" [link]({link})" if link else ""
            candidate_lines.append(f"{i}. {ref}{c['name']}{desc}{link_md}")

        candidates_text = (
            "\n".join(candidate_lines)
            if candidate_lines
            else "No matching controls found in the system."
        )

        return (
            f"You are a GRC (Governance, Risk, Compliance) expert.\n\n"
            f"**Risk Scenario:** {scenario_info['name']}\n"
            f"{scenario_info.get('description', '')}\n\n"
            f"**Threats:** {threats}\n"
            f"**Assets at risk:** {assets}\n"
            f"**Existing controls:** {existing}\n"
            f"{level_text}\n"
            f"**Treatment:** {scenario_info.get('treatment', 'open')}\n\n"
            f"**Available controls in the system:**\n{candidates_text}\n\n"
            f"**Your task:**\n"
            f"1. Recommend a treatment approach (mitigate, accept, avoid, or transfer) with brief justification.\n"
            f"2. If mitigating, evaluate which of the available controls would help reduce this risk.\n"
            f"3. For each relevant control, explain briefly how it addresses the identified threats.\n"
            f"4. If gaps remain, suggest what NEW controls should be created.\n\n"
            f"Keep your response concise and actionable. "
            f"The user will see interactive buttons below to attach controls — "
            f"do NOT describe how to attach them.\n\n"
            f"**IMPORTANT:** At the very end of your response, output a JSON block listing "
            f"ONLY the numbers of controls you recommend attaching (from the numbered list above). "
            f"Use this exact format:\n"
            f"```json\n"
            f'{{"recommended": [1, 3, 5]}}\n'
            f"```\n"
            f"Only include controls that are genuinely relevant to mitigating this risk."
        )
