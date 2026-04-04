"""
Suggest Controls workflow.

Context: User is on a requirement assessment page and asks what controls
to implement, how to comply, or what to do.

Steps:
    1. Fetch the requirement details (deterministic)
    2. Search existing controls that might match (deterministic)
    3. LLM ranks and explains matches (reasoning)
    4. Emit attach proposals for matching controls (deterministic)
"""

import structlog
from typing import Iterator

from django.apps import apps
from django.db.models import Q

from chat.page_context import ParsedContext
from .base import Workflow, WorkflowContext, SSEEvent

logger = structlog.get_logger(__name__)


class SuggestControlsWorkflow(Workflow):
    name = "suggest_controls"
    description = (
        "Suggest existing controls to comply with the current requirement, "
        "or recommend new controls to create. Use this when the user asks "
        "what to implement, how to comply, what controls to add, "
        "or requests recommendations for the current requirement assessment. "
        "Works in any language."
    )
    context_models = ["requirement_assessment"]

    def run(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        # Step 1: Fetch requirement details
        yield self._thinking("Analyzing the requirement...")

        requirement_info = self._fetch_requirement(ctx)
        if not requirement_info:
            yield self._token(
                "I couldn't find the requirement details for this assessment. "
                "Please make sure you're on a requirement assessment page."
            )
            return

        req_name = requirement_info["name"]
        req_desc = requirement_info["description"]
        framework_name = requirement_info.get("framework", "")

        yield self._thinking(
            f"Requirement: {req_name}\n"
            f"Framework: {framework_name}\n"
            f"Searching for matching controls..."
        )

        # Step 2: Search for candidate controls
        candidates = self._search_controls(ctx, requirement_info)
        already_attached = self._get_attached_control_ids(ctx)

        # Filter out already-attached controls
        new_candidates = [c for c in candidates if c["id"] not in already_attached]

        yield self._thinking(
            f"Found {len(candidates)} candidate controls, "
            f"{len(already_attached)} already attached, "
            f"{len(new_candidates)} new candidates to evaluate."
        )

        # Step 3: LLM ranks and explains
        if new_candidates:
            ranking_prompt = self._build_ranking_prompt(
                requirement_info, new_candidates
            )
            yield from self._stream_llm(ctx, ranking_prompt)
        elif already_attached:
            yield self._token(
                f"This requirement already has {len(already_attached)} control(s) attached. "
                f"I searched for additional controls but didn't find strong matches. "
                f"You may want to create new controls specific to this requirement."
            )
            return
        else:
            yield self._token(
                "I couldn't find existing controls that match this requirement. "
                "Consider creating new controls tailored to it."
            )
            return

        # Step 4: Parse LLM recommendations and emit attach proposals
        if new_candidates:
            recommended = self._parse_recommended_indices(
                getattr(self, "_last_response", ""), new_candidates
            )
            if not recommended:
                # Fallback: if parsing fails, don't propose anything
                # (the LLM text already explains what's relevant)
                return

            from chat.tools import MODEL_MAP

            parent_info = MODEL_MAP.get("requirement_assessment")
            related_info = MODEL_MAP.get("applied_control")
            if parent_info and related_info:
                proposal = {
                    "type": "pending_action",
                    "action": "attach",
                    "parent_model_key": "requirement_assessment",
                    "parent_id": ctx.parsed_context.object_id,
                    "parent_url_slug": parent_info[3],
                    "m2m_field": "applied_controls",
                    "related_model_key": "applied_control",
                    "related_display": related_info[2],
                    "items": [{"id": c["id"], "name": c["name"]} for c in recommended],
                }
                yield self._pending_action(proposal)

    def _fetch_requirement(self, ctx: WorkflowContext) -> dict | None:
        """Fetch the requirement and its context from the RequirementAssessment."""
        try:
            RequirementAssessment = apps.get_model("core", "RequirementAssessment")
            ra = (
                RequirementAssessment.objects.select_related(
                    "requirement", "compliance_assessment__framework"
                )
                .filter(
                    id=ctx.parsed_context.object_id,
                    compliance_assessment__folder_id__in=ctx.accessible_folder_ids,
                )
                .first()
            )
            if not ra or not ra.requirement:
                return None

            req = ra.requirement
            result = {
                "name": req.name or "",
                "description": req.description or "",
                "ref_id": getattr(req, "ref_id", "") or "",
                "ra_status": ra.status or "",
                "ra_result": ra.result or "",
            }

            if ra.compliance_assessment:
                if ra.compliance_assessment.framework:
                    result["framework"] = ra.compliance_assessment.framework.name or ""
                    result["framework_ref"] = (
                        getattr(ra.compliance_assessment.framework, "ref_id", "") or ""
                    )
                result["folder_id"] = str(ra.compliance_assessment.folder_id)

            # Get existing attached controls count
            result["existing_controls_count"] = ra.applied_controls.count()

            return result
        except Exception as e:
            logger.error("Failed to fetch requirement: %s", e)
            return None

    def _search_controls(
        self, ctx: WorkflowContext, requirement_info: dict
    ) -> list[dict]:
        """
        Search for controls that might match the requirement.

        Strategy:
        1. First search in the same domain (folder) as the compliance assessment
        2. Use meaningful keywords from the requirement (skip stop words)
        3. If not enough results, broaden to all accessible folders
        4. Score results by keyword match count for better ranking
        """
        AppliedControl = apps.get_model("core", "AppliedControl")

        # Build meaningful keywords from requirement name + description
        req_name = requirement_info.get("name", "")
        req_desc = requirement_info.get("description", "")
        search_text = f"{req_name} {req_desc}".strip()

        # Filter out stop words and short words to get meaningful terms
        _STOP_WORDS = {
            "the",
            "and",
            "for",
            "are",
            "not",
            "that",
            "this",
            "with",
            "from",
            "have",
            "has",
            "been",
            "must",
            "shall",
            "should",
            "will",
            "can",
            "may",
            "all",
            "any",
            "each",
            "they",
            "them",
            "their",
            "its",
            "which",
            "when",
            "where",
            "what",
            "how",
            "les",
            "des",
            "une",
            "pour",
            "dans",
            "par",
            "sur",
            "aux",
            "est",
            "sont",
            "être",
            "avec",
            "qui",
            "que",
            "tout",
            "tous",
            "doit",
            "doivent",
            "peut",
            "cette",
            "ces",
        }
        words = []
        for w in search_text.split():
            clean = w.strip(".,;:!?()[]{}\"'").lower()
            if len(clean) > 3 and clean not in _STOP_WORDS:
                words.append(clean)
        # Deduplicate while preserving order
        seen = set()
        keywords = []
        for w in words:
            if w not in seen:
                seen.add(w)
                keywords.append(w)
        keywords = keywords[:15]

        if not keywords:
            return []

        # Build the keyword filter
        keyword_filter = Q()
        for word in keywords:
            keyword_filter |= Q(name__icontains=word) | Q(description__icontains=word)

        # Search 1: Same domain first (controls in the compliance assessment's folder)
        folder_id = requirement_info.get("folder_id")
        results = []
        seen_ids = set()

        if folder_id:
            domain_qs = (
                AppliedControl.objects.filter(folder_id=folder_id)
                .filter(keyword_filter)
                .order_by("name")[:20]
            )
            for ctrl in domain_qs:
                results.append(self._serialize_control(ctrl))
                seen_ids.add(str(ctrl.id))

        # Search 2: Broaden to all accessible folders if not enough results
        if len(results) < 10:
            broad_qs = (
                AppliedControl.objects.filter(folder_id__in=ctx.accessible_folder_ids)
                .filter(keyword_filter)
                .exclude(id__in=seen_ids)
                .order_by("name")[: 20 - len(results)]
            )
            for ctrl in broad_qs:
                results.append(self._serialize_control(ctrl))

        # Score and sort by keyword match count (more matches = more relevant)
        for item in results:
            text = f"{item['name']} {item['description']}".lower()
            item["_score"] = sum(1 for kw in keywords if kw in text)
        results.sort(key=lambda x: x["_score"], reverse=True)

        # Remove scoring key before returning
        for item in results:
            del item["_score"]

        return results[:20]

    @staticmethod
    def _serialize_control(ctrl) -> dict:
        return {
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

    def _get_attached_control_ids(self, ctx: WorkflowContext) -> set[str]:
        """Get IDs of controls already attached to this requirement assessment."""
        try:
            RequirementAssessment = apps.get_model("core", "RequirementAssessment")
            ra = RequirementAssessment.objects.filter(
                id=ctx.parsed_context.object_id,
                compliance_assessment__folder_id__in=ctx.accessible_folder_ids,
            ).first()
            if ra:
                return {
                    str(pk) for pk in ra.applied_controls.values_list("id", flat=True)
                }
        except (LookupError, AttributeError) as e:
            logger.warning("attached_controls_lookup_failed", error=e)
        return set()

    def _build_ranking_prompt(
        self, requirement_info: dict, candidates: list[dict]
    ) -> str:
        """Build the prompt for the LLM to rank and explain control matches."""
        from django.conf import settings

        base_url = getattr(settings, "CISO_ASSISTANT_URL", "").rstrip("/")

        req_ref = requirement_info.get("ref_id", "")
        req_name = requirement_info.get("name", "")
        req_desc = requirement_info.get("description", "")
        framework = requirement_info.get("framework", "")

        candidate_lines = []
        for i, c in enumerate(candidates, 1):
            ref = f"[{c['ref_id']}] " if c.get("ref_id") else ""
            desc = f" — {c['description']}" if c.get("description") else ""
            status = f" (status: {c['status']})" if c.get("status") else ""
            link = f"{base_url}/applied-controls/{c['id']}" if base_url else ""
            link_md = f" [link]({link})" if link else ""
            candidate_lines.append(f"{i}. {ref}{c['name']}{status}{desc}{link_md}")

        candidates_text = "\n".join(candidate_lines)

        return (
            f"You are a GRC (Governance, Risk, Compliance) expert.\n\n"
            f"**Requirement** ({framework}):\n"
            f"{'[' + req_ref + '] ' if req_ref else ''}{req_name}\n"
            f"{req_desc}\n\n"
            f"**Candidate controls** (already existing in the system):\n"
            f"{candidates_text}\n\n"
            f"**Your task:**\n"
            f"1. Evaluate which of these existing controls are relevant to the requirement above.\n"
            f"2. For each relevant control, briefly explain WHY it helps address the requirement.\n"
            f"3. If some aspects of the requirement are NOT covered by any candidate, "
            f"suggest what NEW controls should be created.\n\n"
            f"Keep your response concise. Use the control names as provided. "
            f"The user will see interactive buttons below your response to attach the controls — "
            f"do NOT describe how to attach them.\n\n"
            f"**IMPORTANT:** At the very end of your response, output a JSON block listing "
            f"ONLY the numbers of controls you recommend attaching (from the numbered list above). "
            f"Use this exact format:\n"
            f"```json\n"
            f'{{"recommended": [1, 3, 5]}}\n'
            f"```\n"
            f"Only include controls that are genuinely relevant. Do NOT include controls you "
            f"explicitly identified as not relevant."
        )
