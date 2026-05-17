"""Audit Prefill agent — Wave 1: control discovery.

Walks every Evidence in the AgentRun's folder, extracts candidate
AppliedControls via the LLM, clusters them by embedding similarity, then
matches each cluster against existing AppliedControls in the perimeter
(embedding shortlist + LLM-as-judge). Emits one AgentAction per cluster:
``link_control_existing`` if a perimeter control matches, else
``extract_control`` (create draft).

Wave 2 (per-RequirementAssessment proposal) is a separate AgentRun that
references the approved Wave-1 controls — see ``audit_prefill_wave2.py``.
"""

import math
import mimetypes
import time

import structlog
from django.utils import timezone
from huey.contrib.djhuey import db_task

from .questionnaire import _heartbeat, _parse_json_response

logger = structlog.get_logger(__name__)


# Cosine threshold for grouping two extracted candidates into one cluster.
# Below this, the LLM judge has to settle ties anyway, so don't be greedy.
INTRA_RUN_CLUSTER_THRESHOLD = 0.82

# Cosine threshold for considering an existing AppliedControl in the perimeter
# as a *possible* match for a cluster (LLM judge then decides).
PERIMETER_SHORTLIST_THRESHOLD = 0.65
PERIMETER_SHORTLIST_TOP_K = 3

# Wall-clock cap for extracting one evidence; oversized PDFs shouldn't stall
# the whole run.
PER_EVIDENCE_TIMEOUT_SEC = 120

# Max chars per evidence fed to the LLM. Larger documents are head-truncated;
# the snippet field carried in the cluster source_refs preserves the actual
# passage that led to each candidate.
MAX_EVIDENCE_CHARS = 18_000


EXTRACT_CONTROLS_PROMPT = """You are reading an internal security document. \
Extract security CONTROLS — concrete, implementable safeguards that an \
auditor could cite as evidence of compliance.

A control is something the organization DOES or MAINTAINS that reduces risk. \
It has an action verb, a scope, and is verifiable (someone could check \
whether it's in place).

Document name: {evidence_name}

Document content:
\"\"\"
{content}
\"\"\"

Reply with a single JSON object, no prose:
{{"controls": [
    {{
      "name": "<short, capitalized name (max 80 chars), action-oriented>",
      "description": "<one sentence: what the control does, who is responsible, how it is verified>",
      "category": "policy" | "process" | "technical" | "physical" | "procedure",
      "csf_function": "govern" | "identify" | "protect" | "detect" | "respond" | "recover",
      "snippet": "<verbatim quote from the document, max 400 chars, that PROVES the control exists — not background context>"
    }}
]}}

INCLUDE these kinds of things:
- "MFA enforced on internal apps via SSO" (technical safeguard, verifiable)
- "Quarterly access reviews" (recurring process, verifiable)
- "Data classification policy applied at ingest" (governance + action)
- "Backups encrypted at rest, tested monthly" (technical + verification)

EXCLUDE — these are NOT controls, do not extract them:
- Role descriptions or org-chart entries ("Partner L1 Support handles \
basic troubleshooting" → role, not control)
- Definitions, glossaries, acronyms ("PII = Personally Identifiable \
Information" → definition)
- Background context, motivation, scope statements ("This policy applies \
to all employees" → preamble)
- Aspirations or future plans without implementation ("We will adopt \
zero-trust" → not yet a control)
- Vendor/product mentions without an organizational action ("AWS Security \
Hub is available" → tool name only)
- Document metadata (version numbers, owners of THE DOCUMENT, review dates \
of THE DOCUMENT)

Rules:
- Pick a snippet that, on its own, shows the control exists — a direct \
quote of the safeguard, not a heading or a definition around it.
- Keep names short and matchable — "MFA enforcement" beats "Implement \
multi-factor authentication on all internal applications".
- Extract every distinct control the document describes. A single policy \
document often contains many — don't merge them into one.
- Only reply with {{"controls": []}} if the document genuinely contains \
no implementable safeguards (e.g. it is purely an org chart, a CV, an \
invoice, or a glossary)."""


JUDGE_SAME_CONTROL_PROMPT = """You are deciding whether two security control \
records describe the same underlying control.

Control A (candidate from a document):
  Name: {a_name}
  Description: {a_description}

Control B (existing in the perimeter):
  Name: {b_name}
  Description: {b_description}

Reply with a single JSON object, no prose:
{{"same": true | false, "reason": "<one short sentence>"}}

Rules:
- "Same" means they would be merged in a security control library — same \
mechanism, same scope. Wording differences are fine.
- Different scope (e.g. "MFA for admins" vs "MFA for all users") → not same.
- Different mechanism with overlapping purpose (e.g. "Password rotation" vs \
"MFA enforcement") → not same."""


_VALID_AC_CATEGORIES = {"policy", "process", "technical", "physical", "procedure"}
_VALID_AC_CSF_FUNCTIONS = {
    "govern",
    "identify",
    "protect",
    "detect",
    "respond",
    "recover",
}


@db_task()
def run_audit_prefill_wave1(agent_run_id: str):
    """Wave 1 entry point: extract → cluster → match → emit AgentActions."""
    from core.models import AppliedControl, Evidence

    from .models import AgentRun
    from .providers import get_embedder, get_llm

    try:
        run = AgentRun.objects.select_related("owner", "folder").get(id=agent_run_id)
    except AgentRun.DoesNotExist:
        logger.error("AgentRun %s not found", agent_run_id)
        return

    if run.status != AgentRun.Status.QUEUED:
        logger.warning("AgentRun %s is %s; skipping", agent_run_id, run.status)
        return

    run.status = AgentRun.Status.RUNNING
    run.started_at = timezone.now()
    run.last_heartbeat_at = timezone.now()
    run.error_message = ""
    run.save(
        update_fields=[
            "status",
            "started_at",
            "last_heartbeat_at",
            "error_message",
            "updated_at",
        ]
    )

    try:
        llm = get_llm()
        embedder = get_embedder()
    except Exception as e:
        _fail(run, f"LLM or embedder unavailable: {e}")
        return

    evidences = list(
        Evidence.objects.filter(folder=run.folder).prefetch_related("revisions")
    )
    existing_controls = list(AppliedControl.objects.filter(folder=run.folder))

    run.total_steps = len(evidences) + 1  # +1 for the dedup/match pass
    run.completed_steps = 0
    run.save(update_fields=["total_steps", "completed_steps", "updated_at"])

    if not evidences:
        run.status = AgentRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.current_step_label = "No evidences in folder."
        run.config = {**(run.config or {}), "wave": 1, "candidates": 0, "clusters": 0}
        run.save(
            update_fields=[
                "status",
                "finished_at",
                "current_step_label",
                "config",
                "updated_at",
            ]
        )
        return

    candidates: list[dict] = []
    try:
        for i, evidence in enumerate(evidences, start=1):
            label = f"Reading {i}/{len(evidences)}: {evidence.name[:80]}"
            if not _heartbeat(run, label):
                return  # cancelled

            t0 = time.time()
            try:
                doc_candidates = _extract_controls_from_evidence(evidence, llm)
            except Exception as e:
                logger.error("Extraction failed for evidence %s: %s", evidence.id, e)
                doc_candidates = []
            elapsed = time.time() - t0
            if elapsed > PER_EVIDENCE_TIMEOUT_SEC:
                logger.warning(
                    "Evidence %s exceeded soft budget (%.1fs)", evidence.id, elapsed
                )
            for c in doc_candidates:
                c["evidence_id"] = str(evidence.id)
                c["evidence_name"] = evidence.name
            candidates.extend(doc_candidates)

            run.completed_steps = i
            run.last_heartbeat_at = timezone.now()
            run.save(
                update_fields=["completed_steps", "last_heartbeat_at", "updated_at"]
            )

        # Dedup pass — clusters + perimeter match
        if not _heartbeat(run, "Clustering and matching candidates…"):
            return

        clusters = _cluster_candidates(candidates, embedder)
        _emit_cluster_actions(
            run=run,
            clusters=clusters,
            existing_controls=existing_controls,
            embedder=embedder,
            llm=llm,
        )

        run.completed_steps = run.total_steps
        run.status = AgentRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.current_step_label = ""
        run.config = {
            **(run.config or {}),
            "wave": 1,
            "candidates": len(candidates),
            "clusters": len(clusters),
        }
        run.save(
            update_fields=[
                "completed_steps",
                "status",
                "finished_at",
                "current_step_label",
                "config",
                "updated_at",
            ]
        )
        logger.info(
            "AgentRun %s Wave 1 completed: %d candidates → %d clusters",
            run.id,
            len(candidates),
            len(clusters),
        )

    except Exception as e:
        logger.exception("AgentRun %s Wave 1 failed", run.id)
        _fail(run, str(e))


def _fail(run, message: str):
    run.status = run.Status.FAILED
    run.error_message = message
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "error_message", "finished_at", "updated_at"])


def _extract_controls_from_evidence(evidence, llm) -> list[dict]:
    """Read the latest revision's attachment, send to LLM, return cleaned list."""
    from .extractors import get_extractor

    revision = evidence.last_revision
    if not revision or not revision.attachment:
        return []

    filename = revision.attachment.name
    content_type, _ = mimetypes.guess_type(filename)
    extractor = get_extractor(content_type or "")
    if not extractor:
        logger.info("No extractor for evidence %s (%s)", evidence.id, content_type)
        return []

    try:
        chunks = extractor(revision.attachment)
    except Exception as e:
        logger.warning(
            "Extractor failed for evidence %s (%s): %s", evidence.id, filename, e
        )
        return []
    if not chunks:
        return []

    full_text = "\n\n".join(c.text for c in chunks)
    if len(full_text) > MAX_EVIDENCE_CHARS:
        full_text = full_text[:MAX_EVIDENCE_CHARS]

    prompt = EXTRACT_CONTROLS_PROMPT.format(
        evidence_name=evidence.name[:160] or "(untitled)",
        content=full_text,
    )
    try:
        raw = llm.generate(prompt=prompt, context="", history=[])
    except Exception as e:
        logger.warning("LLM extract failed for evidence %s: %s", evidence.id, e)
        return []

    parsed = _parse_json_response(raw) or {}
    items = parsed.get("controls") or []
    if not isinstance(items, list):
        return []

    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip()[:200]
        description = (item.get("description") or "").strip()[:1000]
        if not name:
            continue
        category = (item.get("category") or "").strip().lower()
        csf = (item.get("csf_function") or "").strip().lower()
        snippet = (item.get("snippet") or "").strip()[:400]
        cleaned.append(
            {
                "name": name,
                "description": description,
                "category": category if category in _VALID_AC_CATEGORIES else "",
                "csf_function": csf if csf in _VALID_AC_CSF_FUNCTIONS else "",
                "snippet": snippet,
            }
        )
    return cleaned


def _cluster_candidates(candidates: list[dict], embedder) -> list[dict]:
    """Greedy single-link clustering on (name + description) embeddings.

    Returns a list of cluster dicts:
      {
        "centroid_name": str,
        "centroid_description": str,
        "category": str,           # most common non-empty in cluster
        "csf_function": str,       # idem
        "members": [candidate, ...]
      }
    """
    if not candidates:
        return []

    texts = [_candidate_text(c) for c in candidates]
    try:
        vectors = embedder.embed(texts)
    except Exception as e:
        logger.warning("Embedding failed for cluster pass: %s", e)
        # Fall back: one cluster per candidate (degenerate but safe)
        return [_singleton_cluster(c) for c in candidates]

    norms = [_normalize(v) for v in vectors]
    cluster_indices: list[list[int]] = []
    cluster_centroids: list[list[float]] = []

    for i, vec in enumerate(norms):
        best_j = -1
        best_score = -1.0
        for j, centroid in enumerate(cluster_centroids):
            score = _dot(vec, centroid)
            if score > best_score:
                best_score = score
                best_j = j
        if best_score >= INTRA_RUN_CLUSTER_THRESHOLD and best_j >= 0:
            cluster_indices[best_j].append(i)
            # Update centroid = mean of members (renormalized)
            members = cluster_indices[best_j]
            mean = [
                sum(norms[m][k] for m in members) / len(members)
                for k in range(len(vec))
            ]
            cluster_centroids[best_j] = _normalize(mean)
        else:
            cluster_indices.append([i])
            cluster_centroids.append(vec)

    clusters: list[dict] = []
    for member_ids in cluster_indices:
        members = [candidates[i] for i in member_ids]
        clusters.append(
            {
                "centroid_name": members[0]["name"],
                "centroid_description": members[0]["description"],
                "category": _mode([m["category"] for m in members]),
                "csf_function": _mode([m["csf_function"] for m in members]),
                "members": members,
            }
        )
    return clusters


def _singleton_cluster(candidate: dict) -> dict:
    return {
        "centroid_name": candidate["name"],
        "centroid_description": candidate["description"],
        "category": candidate["category"],
        "csf_function": candidate["csf_function"],
        "members": [candidate],
    }


def _emit_cluster_actions(
    *,
    run,
    clusters: list[dict],
    existing_controls: list,
    embedder,
    llm,
) -> None:
    """For each cluster, emit either link_control_existing or extract_control."""
    from django.contrib.contenttypes.models import ContentType

    from core.models import AppliedControl

    from .models import AgentAction

    ac_ct = ContentType.objects.get_for_model(AppliedControl)

    # Embed existing controls once
    existing_vectors: list[tuple[AppliedControl, list[float]]] = []
    if existing_controls:
        existing_texts = [_existing_control_text(ac) for ac in existing_controls]
        try:
            raw_vectors = embedder.embed(existing_texts)
            for ac, vec in zip(existing_controls, raw_vectors):
                existing_vectors.append((ac, _normalize(vec)))
        except Exception as e:
            logger.warning(
                "Embedding existing controls failed; skipping dedup match: %s", e
            )

    for cluster_idx, cluster in enumerate(clusters):
        cluster_text = _candidate_text(
            {
                "name": cluster["centroid_name"],
                "description": cluster["centroid_description"],
            }
        )
        try:
            cluster_vec = _normalize(embedder.embed([cluster_text])[0])
        except Exception:
            cluster_vec = None

        source_refs = [
            {
                "index": i + 1,
                "kind": "evidence",
                "id": m["evidence_id"],
                "name": m["evidence_name"],
                "snippet": m["snippet"],
                "score": None,
            }
            for i, m in enumerate(cluster["members"])
        ]

        matched_ac = None
        match_reason = ""
        if cluster_vec is not None and existing_vectors:
            scored = sorted(
                ((_dot(cluster_vec, v), ac) for ac, v in existing_vectors),
                key=lambda x: x[0],
                reverse=True,
            )
            shortlist = [
                (score, ac)
                for score, ac in scored[:PERIMETER_SHORTLIST_TOP_K]
                if score >= PERIMETER_SHORTLIST_THRESHOLD
            ]
            for score, ac in shortlist:
                same, reason = _llm_judge_same(
                    llm,
                    a_name=cluster["centroid_name"],
                    a_description=cluster["centroid_description"],
                    b_name=ac.name,
                    b_description=ac.description or "",
                )
                if same:
                    matched_ac = ac
                    match_reason = (
                        f"cosine={score:.2f}; judge: {reason}"
                        if reason
                        else f"cosine={score:.2f}"
                    )
                    break

        confidence = _cluster_confidence(cluster, matched=matched_ac is not None)

        if matched_ac is not None:
            AgentAction.objects.create(
                agent_run=run,
                kind=AgentAction.Kind.LINK_CONTROL_EXISTING,
                target_content_type=ac_ct,
                target_object_id=matched_ac.id,
                payload={
                    "cluster_id": cluster_idx,
                    "candidate_name": cluster["centroid_name"],
                    "candidate_description": cluster["centroid_description"],
                    "existing_control_id": str(matched_ac.id),
                    "existing_control_name": matched_ac.name,
                },
                rationale=match_reason,
                source_refs=source_refs,
                confidence=confidence,
                state=AgentAction.State.PROPOSED,
            )
        else:
            AgentAction.objects.create(
                agent_run=run,
                kind=AgentAction.Kind.EXTRACT_CONTROL,
                target_content_type=None,
                target_object_id=None,
                payload={
                    "cluster_id": cluster_idx,
                    "name": cluster["centroid_name"],
                    "description": cluster["centroid_description"],
                    "category": cluster["category"],
                    "csf_function": cluster["csf_function"],
                    "status": "to_do",
                },
                rationale=(
                    f"Extracted from {len(cluster['members'])} document mention(s); "
                    "no matching control in perimeter."
                ),
                source_refs=source_refs,
                confidence=confidence,
                state=AgentAction.State.PROPOSED,
            )


def _llm_judge_same(
    llm, *, a_name: str, a_description: str, b_name: str, b_description: str
) -> tuple[bool, str]:
    """LLM-as-judge: are these the same control? Returns (same, reason)."""
    prompt = JUDGE_SAME_CONTROL_PROMPT.format(
        a_name=a_name[:200],
        a_description=(a_description or "")[:500],
        b_name=b_name[:200],
        b_description=(b_description or "")[:500],
    )
    try:
        raw = llm.generate(prompt=prompt, context="", history=[])
    except Exception as e:
        logger.warning("Judge LLM call failed: %s", e)
        return (False, "")
    parsed = _parse_json_response(raw) or {}
    same = bool(parsed.get("same"))
    reason = (parsed.get("reason") or "").strip()[:300]
    return (same, reason)


def _candidate_text(c: dict) -> str:
    name = c.get("name") or ""
    description = c.get("description") or ""
    if description:
        return f"{name} — {description}"
    return name


def _existing_control_text(ac) -> str:
    name = ac.name or ""
    description = ac.description or ""
    if description:
        return f"{name} — {description}"
    return name


def _mode(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for v in values:
        if not v:
            continue
        counts[v] = counts.get(v, 0) + 1
    if not counts:
        return ""
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _normalize(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cluster_confidence(cluster: dict, *, matched: bool) -> float:
    """Heuristic confidence: more evidence mentions = higher confidence."""
    n = len(cluster.get("members", []))
    base = 0.55 if n == 1 else min(0.95, 0.55 + 0.1 * (n - 1))
    if matched:
        # Linking to an existing control is structurally safer than creating
        # a fresh one — give it a small bump so the review UI sorts it up.
        base = min(0.95, base + 0.05)
    return round(base, 2)


# ---------------------------------------------------------------------------
# Wave 2 — per-RequirementAssessment proposal pipeline
# ---------------------------------------------------------------------------

PROPOSE_RESULT_PROMPT = """You are an internal auditor proposing a compliance \
verdict for a single requirement, given (a) the requirement text and (b) the \
catalog of security controls our organization has documented.

Requirement:
\"\"\"
{requirement_text}
\"\"\"

Available controls (use only these — do not invent IDs):
{control_catalog}

Reply with a single JSON object, no prose:
{{
  "result": "compliant" | "partially_compliant" | "non_compliant" | "not_applicable",
  "control_ids": ["<control id from the catalog>", ...],
  {observation_field}
  "confidence": <float 0..1>
}}

Rules:
- "compliant" only if the cited controls together fully cover the \
requirement.
- "partially_compliant" when the controls address part of the requirement \
but leave gaps.
- "non_compliant" when no listed control addresses the requirement.
- "not_applicable" only when the requirement does not apply to our scope.
- control_ids must be a subset of the catalog IDs. Empty list is allowed \
(implies non_compliant or not_applicable).
- {observation_rule}"""

OBSERVATION_FIELD_THOROUGH = '"observation": "<2-3 sentences justifying the verdict, citing specific controls by name>",'
OBSERVATION_RULE_THOROUGH = (
    "observation should be concrete and reference the controls by name."
)
OBSERVATION_FIELD_FAST = ""
OBSERVATION_RULE_FAST = (
    "Do NOT include an observation field — it stays empty for fast strictness."
)

# Per-RA shortlist of existing perimeter controls (those NOT already surfaced
# by Wave 1). Embedded once at run start, scored per requirement. Threshold
# keeps irrelevant controls out of the prompt even if they fill the top-K.
WAVE2_EXISTING_TOP_K_FAST = 5
WAVE2_EXISTING_TOP_K_THOROUGH = 8
WAVE2_EXISTING_COSINE_FLOOR = 0.5


_VALID_RA_RESULTS = {
    "compliant",
    "partially_compliant",
    "non_compliant",
    "not_applicable",
}


@db_task()
def run_audit_prefill_wave2(agent_run_id: str):
    """Wave 2 entry point.

    Reads the parent Wave-1 run's approved actions to build the catalog of
    controls available for citation (existing perimeter controls that were
    approved as ``link_control_existing``, plus freshly-created controls
    from approved ``extract_control`` actions). Per selected
    RequirementAssessment in the target ComplianceAssessment, retrieves
    relevant passages and asks the LLM to propose
    ``{result, control_ids[], observation?, confidence}``. Emits one
    ``propose_result`` AgentAction per RA.
    """
    from core.models import ComplianceAssessment, RequirementAssessment
    from django.contrib.contenttypes.models import ContentType

    from .models import AgentAction, AgentRun
    from .providers import get_embedder, get_llm
    from .questionnaire import _build_context_block, _search_folder_evidence

    try:
        run = AgentRun.objects.select_related("owner", "folder").get(id=agent_run_id)
    except AgentRun.DoesNotExist:
        logger.error("AgentRun %s not found", agent_run_id)
        return

    if run.status != AgentRun.Status.QUEUED:
        logger.warning("AgentRun %s is %s; skipping", agent_run_id, run.status)
        return

    run.status = AgentRun.Status.RUNNING
    run.started_at = timezone.now()
    run.last_heartbeat_at = timezone.now()
    run.save(
        update_fields=[
            "status",
            "started_at",
            "last_heartbeat_at",
            "updated_at",
        ]
    )

    try:
        llm = get_llm()
    except Exception as e:
        _fail(run, f"LLM unavailable: {e}")
        return

    # Embedder is optional — if it fails we just skip the existing-controls
    # shortlist (Wave 2 still works using Wave-1-derived controls only).
    try:
        embedder = get_embedder()
    except Exception as e:
        logger.warning(
            "AgentRun %s Wave 2: embedder unavailable, skipping existing-controls "
            "shortlist (%s)",
            run.id,
            e,
        )
        embedder = None

    # Resolve the parent Wave-1 run and build the control catalog.
    parent_id = (run.config or {}).get("parent_run_id")
    if not parent_id:
        _fail(run, "Wave 2 run has no parent_run_id in config.")
        return
    try:
        catalog_controls = _build_control_catalog(parent_id)
    except Exception as e:
        _fail(run, f"Failed to build control catalog: {e}")
        return

    # Index existing perimeter controls (excluding ones already in the
    # Wave-1-derived catalog so they don't appear twice). Embedded once
    # here, scored per RA inside the loop.
    wave1_ids = {str(c.id) for c in catalog_controls}
    existing_index = (
        _index_existing_controls(run.folder, embedder, exclude_ids=wave1_ids)
        if embedder is not None
        else []
    )
    top_k_existing = (
        WAVE2_EXISTING_TOP_K_THOROUGH
        if run.strictness == AgentRun.Strictness.THOROUGH
        else WAVE2_EXISTING_TOP_K_FAST
    )

    # Resolve the target audit + its requirement assessments.
    try:
        ca = ComplianceAssessment.objects.get(id=run.target_object_id)
    except ComplianceAssessment.DoesNotExist:
        _fail(run, "Target compliance assessment not found.")
        return

    ras = list(
        RequirementAssessment.objects.filter(
            compliance_assessment=ca, selected=True
        ).select_related("requirement")
    )
    run.total_steps = len(ras)
    run.completed_steps = 0
    run.save(update_fields=["total_steps", "completed_steps", "updated_at"])

    if not ras:
        run.status = AgentRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.current_step_label = "No selected requirements."
        run.save(
            update_fields=["status", "finished_at", "current_step_label", "updated_at"]
        )
        return

    is_thorough = run.strictness == AgentRun.Strictness.THOROUGH
    ra_ct = ContentType.objects.get_for_model(RequirementAssessment)

    try:
        for i, ra in enumerate(ras, start=1):
            label = f"Assessing {i}/{len(ras)}: {str(ra.requirement)[:80]}"
            if not _heartbeat(run, label):
                return

            try:
                _propose_result_for_ra(
                    run=run,
                    ra=ra,
                    catalog_controls=catalog_controls,
                    existing_index=existing_index,
                    top_k_existing=top_k_existing,
                    embedder=embedder,
                    llm=llm,
                    ra_ct=ra_ct,
                    is_thorough=is_thorough,
                    search_folder=lambda q: _search_folder_evidence(
                        q, run.folder_id, top_k=8 if is_thorough else 5
                    ),
                    build_context=_build_context_block,
                )
            except Exception as e:
                logger.exception("Failed Wave 2 RA %s", ra.id)
                AgentAction.objects.create(
                    agent_run=run,
                    kind=AgentAction.Kind.PROPOSE_RESULT,
                    target_content_type=ra_ct,
                    target_object_id=ra.id,
                    payload={
                        "result": "not_assessed",
                        "control_ids": [],
                        "observation": "",
                        "confidence": 0.0,
                    },
                    rationale=f"Error: {e}",
                    source_refs=[],
                    confidence=0.0,
                    state=AgentAction.State.PROPOSED,
                )

            run.completed_steps = i
            run.last_heartbeat_at = timezone.now()
            run.save(
                update_fields=["completed_steps", "last_heartbeat_at", "updated_at"]
            )

        run.status = AgentRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.current_step_label = ""
        run.config = {
            **(run.config or {}),
            "wave": 2,
            "ras_proposed": len(ras),
            "catalog_size": len(catalog_controls),
        }
        run.save(
            update_fields=[
                "status",
                "finished_at",
                "current_step_label",
                "config",
                "updated_at",
            ]
        )

    except Exception as e:
        logger.exception("AgentRun %s Wave 2 failed", run.id)
        _fail(run, str(e))


def _build_control_catalog(parent_wave1_run_id: str) -> list:
    """Return AppliedControls Wave 2 may cite, in deterministic order.

    Sourced from the parent Wave-1 run's approved actions:
      - ``extract_control`` actions store the newly-created control id in
        ``payload.created_control_id``.
      - ``link_control_existing`` actions target the existing control via
        ``target_object_id``.
    """
    from core.models import AppliedControl
    from django.contrib.contenttypes.models import ContentType

    from .models import AgentAction

    control_ids: list[str] = []
    ac_ct = ContentType.objects.get_for_model(AppliedControl)

    approved = AgentAction.objects.filter(
        agent_run_id=parent_wave1_run_id,
        state=AgentAction.State.APPROVED,
    )
    for action in approved:
        if action.kind == AgentAction.Kind.EXTRACT_CONTROL:
            created_id = (action.payload or {}).get("created_control_id")
            if created_id:
                control_ids.append(created_id)
        elif action.kind == AgentAction.Kind.LINK_CONTROL_EXISTING:
            if action.target_content_type_id == ac_ct.id and action.target_object_id:
                control_ids.append(str(action.target_object_id))

    seen: set[str] = set()
    deduped: list[str] = []
    for cid in control_ids:
        if cid not in seen:
            seen.add(cid)
            deduped.append(cid)
    if not deduped:
        return []
    by_id = AppliedControl.objects.in_bulk([uuid_from_str(c) for c in deduped])
    return [by_id[uid] for uid in by_id]


def uuid_from_str(s: str):
    import uuid as _uuid

    return _uuid.UUID(s)


def _propose_result_for_ra(
    *,
    run,
    ra,
    catalog_controls: list,
    existing_index: list,
    top_k_existing: int,
    embedder,
    llm,
    ra_ct,
    is_thorough: bool,
    search_folder,
    build_context,
):
    """Single-RA pipeline: retrieve passages → LLM propose → emit AgentAction.

    Catalog the LLM sees has two labeled sections:
      [Evidence-backed]        — controls surfaced + approved in Wave 1
      [Existing in perimeter]  — top-K perimeter controls by cosine to the
                                  requirement (above WAVE2_EXISTING_COSINE_FLOOR)
    The LLM picks IDs from either section; the post-processor accepts both.
    """
    from .models import AgentAction

    requirement_text = _requirement_text(ra)

    # RAG retrieval on the requirement text — the same folder-scoped helper
    # the questionnaire autopilot uses.
    try:
        rag_results = search_folder(requirement_text)
    except Exception as e:
        logger.warning("Wave 2 RAG failed for RA %s: %s", ra.id, e)
        rag_results = []
    context_block, source_refs = build_context(rag_results)

    shortlist = _shortlist_existing_controls(
        requirement_text=requirement_text,
        existing_index=existing_index,
        embedder=embedder,
        top_k=top_k_existing,
        threshold=WAVE2_EXISTING_COSINE_FLOOR,
    )
    catalog_block = _format_catalog_sections(
        [
            ("Evidence-backed (from this run's documents)", catalog_controls),
            ("Existing in perimeter (matched by relevance)", shortlist),
        ]
    )
    obs_field = OBSERVATION_FIELD_THOROUGH if is_thorough else OBSERVATION_FIELD_FAST
    obs_rule = OBSERVATION_RULE_THOROUGH if is_thorough else OBSERVATION_RULE_FAST

    prompt = PROPOSE_RESULT_PROMPT.format(
        requirement_text=requirement_text[:2000],
        control_catalog=catalog_block or "(no controls available)",
        observation_field=obs_field,
        observation_rule=obs_rule,
    )
    if context_block:
        prompt += f"\n\nRelevant document passages:\n{context_block}"

    t0 = time.time()
    try:
        raw = llm.generate(prompt=prompt, context="", history=[])
    except Exception as e:
        logger.error("LLM propose_result failed for RA %s: %s", ra.id, e)
        raw = ""
    duration_ms = int((time.time() - t0) * 1000)

    parsed = _parse_json_response(raw) or {}
    result = (parsed.get("result") or "").strip()
    if result not in _VALID_RA_RESULTS:
        result = "not_assessed"
    proposed_ids = parsed.get("control_ids") or []
    if not isinstance(proposed_ids, list):
        proposed_ids = []
    catalog_id_set = {str(c.id) for c in catalog_controls} | {
        str(c.id) for c in shortlist
    }
    control_ids = [
        cid for cid in proposed_ids if isinstance(cid, str) and cid in catalog_id_set
    ]
    observation = (parsed.get("observation") or "").strip() if is_thorough else ""
    try:
        confidence = float(parsed.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    # Build per-control evidence linking from RAG source_refs: any cited
    # evidence becomes a candidate to link onto each proposed control. The
    # frontend can let the user trim before approving.
    evidence_links = _build_evidence_links(control_ids, source_refs)

    AgentAction.objects.create(
        agent_run=run,
        kind=AgentAction.Kind.PROPOSE_RESULT,
        target_content_type=ra_ct,
        target_object_id=ra.id,
        payload={
            "result": result,
            "control_ids": control_ids,
            "observation": observation,
            "evidence_links": evidence_links,
            "confidence": confidence,
        },
        rationale=raw[:2000],
        source_refs=source_refs,
        confidence=confidence,
        state=AgentAction.State.PROPOSED,
        duration_ms=duration_ms,
    )


def _requirement_text(ra) -> str:
    req = ra.requirement
    bits = []
    if getattr(req, "ref_id", ""):
        bits.append(f"[{req.ref_id}]")
    short = getattr(req, "display_short", None) or str(req)
    if short:
        bits.append(short)
    desc = getattr(req, "description", "") or ""
    if desc:
        bits.append(desc)
    return "\n".join(bits)


def _format_catalog_sections(sections: list[tuple[str, list]]) -> str:
    """Format multiple labeled control sections for the LLM prompt.

    Empty sections are omitted. Label is enclosed in [ ] so the LLM treats
    it as a header rather than an instruction.
    """
    parts: list[str] = []
    for label, controls in sections:
        if not controls:
            continue
        parts.append(f"[{label}]")
        for ac in controls:
            desc = (ac.description or "")[:200]
            line = f"- id={ac.id} | {ac.name}"
            if desc:
                line += f" — {desc}"
            parts.append(line)
        parts.append("")  # blank line between sections
    return "\n".join(parts).rstrip()


def _index_existing_controls(folder, embedder, exclude_ids: set[str]) -> list[tuple]:
    """Embed every AppliedControl in folder (minus the wave1-derived set).

    Called once at Wave 2 start. Returns ``[(control, normalized_vector), …]``
    consumed by :func:`_shortlist_existing_controls` per RA. Embedding cost
    scales with perimeter size, not requirement count.
    """
    from core.models import AppliedControl

    qs = AppliedControl.objects.filter(folder=folder)
    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)
    controls = list(qs)
    if not controls:
        return []
    texts = [_existing_control_text(ac) for ac in controls]
    try:
        vectors = embedder.embed(texts)
    except Exception as e:
        logger.warning(
            "Existing-controls embedding failed; shortlist will be empty (%s)", e
        )
        return []
    return list(zip(controls, [_normalize(v) for v in vectors]))


def _shortlist_existing_controls(
    *,
    requirement_text: str,
    existing_index: list,
    embedder,
    top_k: int,
    threshold: float,
) -> list:
    """Top-K perimeter controls by cosine to the requirement, above threshold."""
    if not existing_index or embedder is None:
        return []
    try:
        req_vec = _normalize(embedder.embed([requirement_text[:2000]])[0])
    except Exception as e:
        logger.warning("Requirement embedding failed: %s", e)
        return []
    scored = [(_dot(req_vec, vec), ac) for ac, vec in existing_index]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ac for score, ac in scored[:top_k] if score >= threshold]


def _build_evidence_links(
    control_ids: list[str], source_refs: list[dict]
) -> list[dict]:
    """Attach every cited evidence to every proposed control.

    Coarse heuristic — the user trims before approving. The alternative
    (asking the LLM to per-control assign evidence) doubled prompt size in
    spike runs without enough accuracy gain to justify it.
    """
    evidence_ids = [
        str(r.get("id"))
        for r in source_refs
        if (r.get("kind") == "evidence" or r.get("kind") == "document") and r.get("id")
    ]
    # Dedup while preserving order
    seen: set[str] = set()
    unique_evidence_ids = []
    for eid in evidence_ids:
        if eid not in seen:
            seen.add(eid)
            unique_evidence_ids.append(eid)
    return [
        {"control_id": cid, "evidence_ids": unique_evidence_ids[:]}
        for cid in control_ids
    ]
