"""
Evidence Guidance workflow.

Context: User is on a requirement assessment page and asks what evidence
to collect, provide, or gather.

Steps:
    1. Fetch requirement details + linked controls (deterministic)
    2. Search existing evidences that might apply (deterministic)
    3. LLM advises what evidence to collect and why (reasoning)
    4. Emit attach proposals for existing evidences or suggest new ones (deterministic)
"""

import logging
from typing import Iterator

from django.apps import apps
from django.db.models import Q

from chat.page_context import ParsedContext
from .base import Workflow, WorkflowContext, SSEEvent

logger = logging.getLogger(__name__)


class EvidenceGuidanceWorkflow(Workflow):
    name = "evidence_guidance"
    description = (
        "Advise what evidence to collect, provide, or gather for the current "
        "requirement assessment. Suggests existing evidences to attach and "
        "describes what new evidence an auditor would expect. Use this when "
        "the user asks about evidence, proof, documentation, or how to "
        "demonstrate compliance. Works in any language."
    )
    context_models = ["requirement_assessment"]

    def run(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        # Step 1: Fetch requirement + controls context
        yield self._thinking("Analyzing the requirement and linked controls...")

        context_info = self._fetch_context(ctx)
        if not context_info:
            yield self._token(
                "I couldn't find the requirement details. "
                "Please make sure you're on a requirement assessment page."
            )
            return

        yield self._thinking(
            f"Requirement: {context_info['req_name']}\n"
            f"Controls: {len(context_info['controls'])} linked\n"
            f"Searching for relevant evidences..."
        )

        # Step 2: Search existing evidences
        candidates = self._search_evidences(ctx, context_info)
        already_attached = context_info.get("existing_evidence_ids", set())
        new_candidates = [c for c in candidates if c["id"] not in already_attached]

        yield self._thinking(
            f"Found {len(candidates)} candidate evidences, "
            f"{len(already_attached)} already attached."
        )

        # Step 3: LLM advises on evidence
        guidance_prompt = self._build_guidance_prompt(context_info, new_candidates)
        yield from self._stream_llm(ctx, guidance_prompt)

        # Step 4: Parse LLM recommendations and emit attach proposals
        if new_candidates:
            recommended = self._parse_recommended_indices(
                getattr(self, "_last_response", ""), new_candidates
            )
            if not recommended:
                return

            from chat.tools import MODEL_MAP

            parent_info = MODEL_MAP.get("requirement_assessment")
            related_info = MODEL_MAP.get("evidence")
            if parent_info and related_info:
                proposal = {
                    "type": "pending_action",
                    "action": "attach",
                    "parent_model_key": "requirement_assessment",
                    "parent_id": ctx.parsed_context.object_id,
                    "parent_url_slug": parent_info[3],
                    "m2m_field": "evidences",
                    "related_model_key": "evidence",
                    "related_display": related_info[2],
                    "items": [{"id": c["id"], "name": c["name"]} for c in recommended],
                }
                yield self._pending_action(proposal)

    def _fetch_context(self, ctx: WorkflowContext) -> dict | None:
        """Fetch requirement, controls, and existing evidences."""
        try:
            RequirementAssessment = apps.get_model("core", "RequirementAssessment")
            ra = (
                RequirementAssessment.objects.select_related(
                    "requirement", "compliance_assessment__framework"
                )
                .prefetch_related("applied_controls", "evidences")
                .filter(id=ctx.parsed_context.object_id)
                .first()
            )
            if not ra or not ra.requirement:
                return None

            req = ra.requirement
            controls = [
                {
                    "name": str(c),
                    "category": (
                        c.get_category_display()
                        if hasattr(c, "get_category_display")
                        else c.category or ""
                    ),
                }
                for c in ra.applied_controls.all()
            ]

            result = {
                "req_name": req.name or "",
                "req_description": req.description or "",
                "req_ref_id": getattr(req, "ref_id", "") or "",
                "framework": "",
                "controls": controls,
                "existing_evidence_ids": {
                    str(pk) for pk in ra.evidences.values_list("id", flat=True)
                },
            }

            if ra.compliance_assessment and ra.compliance_assessment.framework:
                result["framework"] = ra.compliance_assessment.framework.name or ""

            return result
        except Exception as e:
            logger.error("Failed to fetch requirement context: %s", e)
            return None

    def _search_evidences(self, ctx: WorkflowContext, context_info: dict) -> list[dict]:
        """Search for evidences that might be relevant."""
        Evidence = apps.get_model("core", "Evidence")

        qs = Evidence.objects.filter(folder_id__in=ctx.accessible_folder_ids)

        # Search based on requirement text + control names
        search_terms = []
        if context_info.get("req_description"):
            words = [w for w in context_info["req_description"].split() if len(w) > 3][
                :8
            ]
            search_terms.extend(words)
        for ctrl in context_info.get("controls", []):
            words = [w for w in ctrl["name"].split() if len(w) > 3][:3]
            search_terms.extend(words)

        if search_terms:
            q = Q()
            for term in search_terms[:15]:
                q |= Q(name__icontains=term) | Q(description__icontains=term)
            qs = qs.filter(q)

        qs = qs.order_by("-updated_at")[:20]

        results = []
        for ev in qs:
            results.append(
                {
                    "id": str(ev.id),
                    "name": str(ev),
                    "description": (
                        ev.description[:200] + "..."
                        if ev.description and len(ev.description) > 200
                        else ev.description or ""
                    ),
                    "status": (
                        ev.get_status_display()
                        if hasattr(ev, "get_status_display")
                        else ev.status or ""
                    ),
                }
            )
        return results

    def _build_guidance_prompt(self, context_info: dict, candidates: list[dict]) -> str:
        """Build the prompt for evidence guidance."""
        from django.conf import settings

        base_url = getattr(settings, "CISO_ASSISTANT_URL", "").rstrip("/")

        req_ref = context_info.get("req_ref_id", "")
        req_name = context_info.get("req_name", "")
        req_desc = context_info.get("req_description", "")
        framework = context_info.get("framework", "")

        controls_text = ""
        if context_info.get("controls"):
            controls_text = "**Linked controls:**\n"
            for c in context_info["controls"]:
                cat = f" ({c['category']})" if c.get("category") else ""
                controls_text += f"- {c['name']}{cat}\n"
        else:
            controls_text = "**No controls linked yet.**\n"

        candidate_lines = []
        for i, c in enumerate(candidates, 1):
            desc = f" — {c['description']}" if c.get("description") else ""
            status = f" (status: {c['status']})" if c.get("status") else ""
            link = f"{base_url}/evidences/{c['id']}" if base_url else ""
            link_md = f" [link]({link})" if link else ""
            candidate_lines.append(f"{i}. {c['name']}{status}{desc}{link_md}")

        candidates_text = (
            "\n".join(candidate_lines)
            if candidate_lines
            else "No existing evidences match."
        )

        return (
            f"You are a GRC (Governance, Risk, Compliance) expert specializing in audit evidence.\n\n"
            f"**Requirement** ({framework}):\n"
            f"{'[' + req_ref + '] ' if req_ref else ''}{req_name}\n"
            f"{req_desc}\n\n"
            f"{controls_text}\n"
            f"**Existing evidences in the system that might apply:**\n{candidates_text}\n\n"
            f"**Your task:**\n"
            f"1. Describe what types of evidence would satisfy this requirement (be specific: "
            f"documents, logs, screenshots, policies, configurations, etc.).\n"
            f"2. If any of the existing evidences above are relevant, explain which ones and why.\n"
            f"3. Recommend what new evidence the user should create and collect.\n\n"
            f"Keep your response concise and practical. Focus on what an auditor would expect to see. "
            f"The user will see interactive buttons below to attach existing evidences — "
            f"do NOT describe how to attach them.\n\n"
            f"**IMPORTANT:** At the very end of your response, output a JSON block listing "
            f"ONLY the numbers of evidences you recommend attaching (from the numbered list above). "
            f"Use this exact format:\n"
            f"```json\n"
            f'{{"recommended": [1, 3, 5]}}\n'
            f"```\n"
            f"Only include evidences that are genuinely relevant to this requirement."
        )
