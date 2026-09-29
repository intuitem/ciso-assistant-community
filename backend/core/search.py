"""Universal fuzzy search across GRC objects, backing ``GET /api/search/``.

Scoped with ``RoleAssignment.get_viewable_object_ids`` — the primitive
``BaseModelViewSet.get_queryset`` uses — applied before matching, never after.
"""

import re

from automation.models import PostureAssessment
from crq.models import QuantitativeRiskScenario, QuantitativeRiskStudy
from django.db.models import Q, TextField
from django.db.models.functions import Cast
from ebios_rm.models import AttackPath, EbiosRMStudy, FearedEvent, StrategicScenario
from iam.models import Folder, RoleAssignment
from pmbok.models import Accreditation
from privacy.models import DataBreach, Processing, RightRequest
from resilience.models import BusinessImpactAnalysis
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from threat_modeling.models import ThreatModel
from tprm.models import Contract, Entity, EntityAssessment, Solution

from core.models import (
    Actor,
    AppliedControl,
    Asset,
    Campaign,
    ComplianceAssessment,
    Evidence,
    Finding,
    FindingsAssessment,
    Framework,
    Incident,
    Perimeter,
    Policy,
    ReferenceControl,
    RequirementNode,
    RiskAcceptance,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    SecurityException,
    TaskTemplate,
    Threat,
    Vulnerability,
)
from core.utils import get_respondent_scoped_folder_ids


def _search_entry(model, slug, *, ref_id=False, limit=200, extra_search=None):
    """Helper to build a search config entry."""
    return {
        "model": model,
        "slug": slug,
        "ref_id": ref_id,
        "limit": limit,
        # Additional fields to search on (icontains) beyond name/description/ref_id.
        # These are ORM lookup paths, e.g. "framework__name" for a FK join.
        "extra_search": extra_search or [],
    }


SEARCHABLE_MODELS = [
    # limit: per-model cap on broad fetch. Large tables (RequirementNode,
    # ReferenceControl) get a tighter limit to avoid starving smaller models.
    # extra_search: additional fields to query via icontains for this model.
    # --- Organization ---
    _search_entry(Folder, "folders"),
    _search_entry(Perimeter, "perimeters", ref_id=True),
    # --- Catalog ---
    _search_entry(Framework, "frameworks", ref_id=True),
    _search_entry(Threat, "threats", ref_id=True, limit=100, extra_search=["provider"]),
    _search_entry(ReferenceControl, "reference-controls", ref_id=True, limit=100),
    _search_entry(RiskMatrix, "risk-matrices", ref_id=True, limit=50),
    _search_entry(RequirementNode, "requirement-nodes", ref_id=True, limit=100),
    # --- Assets ---
    _search_entry(Asset, "assets", ref_id=True),
    _search_entry(Vulnerability, "vulnerabilities", ref_id=True, limit=100),
    # --- Operations ---
    _search_entry(AppliedControl, "applied-controls", ref_id=True),
    _search_entry(Policy, "policies", ref_id=True),
    _search_entry(Incident, "incidents", ref_id=True),
    _search_entry(Finding, "findings", ref_id=True),
    _search_entry(SecurityException, "security-exceptions", ref_id=True),
    _search_entry(TaskTemplate, "task-templates", ref_id=True, limit=100),
    _search_entry(Evidence, "evidences"),
    # --- Governance ---
    _search_entry(RiskAcceptance, "risk-acceptances"),
    _search_entry(Campaign, "campaigns"),
    _search_entry(Accreditation, "accreditations", ref_id=True),
    # --- Risk ---
    _search_entry(RiskAssessment, "risk-assessments", ref_id=True),
    _search_entry(
        RiskScenario,
        "risk-scenarios",
        ref_id=True,
        extra_search=["risk_assessment__name"],
    ),
    _search_entry(QuantitativeRiskStudy, "quantitative-risk-studies", ref_id=True),
    _search_entry(
        QuantitativeRiskScenario,
        "quantitative-risk-scenarios",
        ref_id=True,
        extra_search=["quantitative_risk_study__name"],
    ),
    _search_entry(ThreatModel, "threat-models", ref_id=True),
    # --- Compliance ---
    _search_entry(
        ComplianceAssessment,
        "compliance-assessments",
        ref_id=True,
        extra_search=["framework__name"],
    ),
    _search_entry(FindingsAssessment, "findings-assessments", ref_id=True),
    _search_entry(PostureAssessment, "posture-assessments", ref_id=True),
    # --- TPRM ---
    _search_entry(Entity, "entities", ref_id=True),
    _search_entry(
        Solution, "solutions", ref_id=True, extra_search=["provider_entity__name"]
    ),
    _search_entry(Contract, "contracts", ref_id=True),
    _search_entry(
        EntityAssessment, "entity-assessments", extra_search=["entity__name"]
    ),
    # --- EBIOS RM ---
    _search_entry(EbiosRMStudy, "ebios-rm", ref_id=True),
    _search_entry(FearedEvent, "feared-events", ref_id=True),
    _search_entry(StrategicScenario, "strategic-scenarios", ref_id=True),
    _search_entry(AttackPath, "attack-paths", ref_id=True),
    # --- Privacy ---
    _search_entry(Processing, "processings", ref_id=True),
    _search_entry(DataBreach, "data-breaches", ref_id=True),
    _search_entry(RightRequest, "right-requests", ref_id=True),
    # --- Resilience ---
    _search_entry(BusinessImpactAnalysis, "business-impact-analysis"),
]


_ACCENT_MAP = {
    "a": "[aàáâãäåæ]",
    "e": "[eèéêë]",
    "i": "[iìíîï]",
    "o": "[oòóôõöø]",
    "u": "[uùúûü]",
    "c": "[cç]",
    "n": "[nñ]",
    "y": "[yýÿ]",
    "s": "[sß]",
}


def _accent_regex(word: str) -> str:
    """Convert a word to a regex pattern that matches accented variants.

    E.g. "referentiel" -> "r[eèéêë]f[eèéêë]r[eèéêë][nñ]t[iìíîï][eèéêë]l"
    Works on both SQLite and PostgreSQL with __iregex.
    """
    return "".join(_ACCENT_MAP.get(c, re.escape(c)) for c in word.lower())


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def global_search(request):
    """
    Universal fuzzy search across all searchable models.

    GET /api/search/?q=firewall+policy&type=applied-controls,assets
    """
    from rapidfuzz import fuzz

    EMPTY_RESPONSE = {"results": [], "query": "", "count": 0, "total_candidates": 0}

    # Cap query length to avoid excessive icontains processing across all models.
    # 200 chars is far beyond any realistic search; words capped at 20 since each
    # word generates 2-3 Q objects per model (~1000+ total at the limit).
    # Minimum 2 chars to avoid single-character fan-out (e.g. q=a matching everything).
    query = request.query_params.get("q", "").strip()[:200]
    if len(query) < 2:
        return Response(EMPTY_RESPONSE)

    type_filter = request.query_params.get("type", "")
    allowed_types = set(type_filter.split(",")) if type_filter else None

    words = query.split()[:20]
    # Build prefix set for typo-tolerant broad fetch (first 3 chars of each word)
    prefixes = {w[:3].lower() for w in words if len(w) >= 3}

    candidates = []

    for entry in SEARCHABLE_MODELS:
        model_class = entry["model"]
        url_slug = entry["slug"]
        has_ref_id = entry["ref_id"]
        max_per_model = entry["limit"]
        extra_search = entry["extra_search"]

        if allowed_types and url_slug not in allowed_types:
            continue

        # Permission-aware queryset
        accessible_ids = RoleAssignment.get_viewable_object_ids(
            request.user, model_class
        )
        qs = model_class.objects.filter(id__in=accessible_ids)

        # ComplianceAssessment has extra respondent scoping: users who lack the
        # full auditor view (view_compliance_assessment_full) in a folder can only see
        # assessments where they have a requirement assignment. Mirror the logic
        # from ComplianceAssessmentViewSet.
        if model_class is ComplianceAssessment:
            respondent_folders = get_respondent_scoped_folder_ids(request.user)
            if respondent_folders:
                user_actors = Actor.get_all_for_user(request.user)
                qs = qs.filter(
                    ~Q(folder_id__in=respondent_folders)
                    | Q(requirement_assignments__actor__in=user_actors)
                ).distinct()

        # Build Q filter for each word on searchable fields.
        # Uses iregex with accent-folding character classes so that e.g.
        # "referentiel" matches "RÉFÉRENTIEL" on SQLite (whose LIKE is
        # ASCII-only and can't fold accents).
        field_names = {f.name for f in model_class._meta.get_fields()}
        searchable = ["name", "description"]
        if has_ref_id:
            searchable.append("ref_id")
        # `translations` holds the localized name/description. Cast first: a regex against
        # the JSONField itself is `jsonb ~* text` on PostgreSQL, which has no operator.
        if "translations" in field_names:
            qs = qs.annotate(translations_text=Cast("translations", TextField()))
            searchable.append("translations_text")
        searchable.extend(extra_search)

        q_filter = Q()
        for word in words:
            pattern = _accent_regex(word)
            word_q = Q()
            for field in searchable:
                word_q |= Q(**{f"{field}__iregex": pattern})
            q_filter |= word_q

        # Also add prefix-based matching for typo tolerance (name + ref_id only)
        for prefix in prefixes:
            prefix_pattern = _accent_regex(prefix)
            prefix_q = Q(**{"name__iregex": prefix_pattern})
            if has_ref_id:
                prefix_q |= Q(**{"ref_id__iregex": prefix_pattern})
            q_filter |= prefix_q

        # Detect optional display fields present on this model (reuses field_names from above)
        extra_fields = []
        if has_ref_id:
            extra_fields.append("ref_id")
        if "folder" in field_names:
            extra_fields.append("folder__name")
        if "provider_entity" in field_names:
            extra_fields.append("provider_entity__name")
        if model_class is RequirementNode:
            extra_fields.append("framework_id")

        # The cap truncates before ranking, so order first. `id` breaks ties: library
        # imports share one timestamp across thousands of rows.
        results = (
            qs.filter(q_filter)
            .order_by("-updated_at", "id")
            .values(
                "id",
                "name",
                "description",
                *extra_fields,
            )[:max_per_model]
        )

        for row in results:
            candidates.append(
                {
                    "type": url_slug,
                    "id": str(row["id"]),
                    "name": row["name"] or "",
                    "ref_id": row.get("ref_id", "") or "",
                    "description": row.get("description") or "",
                    "folder": row.get("folder__name", "") or "",
                    "provider": row.get("provider_entity__name", "") or "",
                    "framework_id": str(row["framework_id"])
                    if row.get("framework_id")
                    else None,
                }
            )

    # Strip accents/diacritics for accent-insensitive matching and scoring.
    # SQLite's LIKE is only ASCII case-insensitive, and rapidfuzz treats
    # accented chars as distinct — normalizing levels the playing field.
    import unicodedata

    def strip_accents(s: str) -> str:
        return "".join(
            c
            for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) != "Mn"
        ).lower()

    query_norm = strip_accents(query)

    # Score and rank with rapidfuzz
    for candidate in candidates:
        name_norm = strip_accents(candidate["name"])
        ref_norm = strip_accents(candidate["ref_id"])
        desc_norm = strip_accents(candidate["description"])

        # Fuzzy scores (on normalized strings for accent-insensitive comparison)
        name_score = fuzz.WRatio(query_norm, name_norm)
        ref_score = fuzz.WRatio(query_norm, ref_norm) if ref_norm else 0
        desc_score = fuzz.partial_ratio(query_norm, desc_norm) * 0.4

        # Substring bonus: literal match in name or ref_id should rank very
        # high. WRatio penalizes long names unfairly (e.g. "recyf" vs
        # "RECYF : REFERENTIEL CYBER France..." scores only 24).
        substring_bonus = 0
        if query_norm in name_norm:
            substring_bonus = 95 if name_norm.startswith(query_norm) else 90
        if query_norm in ref_norm:
            substring_bonus = max(substring_bonus, 95)

        candidate["score"] = max(name_score, ref_score, desc_score, substring_bonus)

    # Sort by score descending, return top 50
    candidates.sort(key=lambda c: c["score"], reverse=True)
    top_results = candidates[:50]

    # Build final response: add URLs and truncate descriptions for the wire
    for r in top_results:
        if r["type"] == "requirement-nodes" and r.get("framework_id"):
            # Link to parent framework (no standalone requirement detail page yet)
            r["url"] = f"/frameworks/{r['framework_id']}"
        else:
            r["url"] = f"/{r['type']}/{r['id']}"
        r["description"] = r["description"][:200]

    return Response(
        {
            "results": top_results,
            "query": query,
            "count": len(top_results),
            "total_candidates": len(candidates),
        }
    )
