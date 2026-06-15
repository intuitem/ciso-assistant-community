"""Pure merge logic for the "map from an audit" feature.

HTTP-agnostic: these helpers take ComplianceAssessment instances plus the
mapping engine's output and return plain dicts. The DRF endpoints that drive
them live in ``core.views`` (``ComplianceAssessmentViewSet.map_from`` /
``map_from_preview``); the multi-hop / weakest-link coverage computation lives
in ``core.mappings.engine``.
"""

# Default ("no information") value for each scalar RequirementAssessment field a
# merge can carry. A source field equal to its default carries no information,
# so it never overwrites a real value on the target.
SCALAR_DEFAULTS = {
    "result": "not_assessed",
    "status": "to_do",
    "score": None,
    "is_scored": False,
    "documentation_score": None,
}


def is_full_coverage(source_ra, same_framework, origin_fw_id):
    """Does the source audit's own data fully cover this target requirement?

    Same framework is always a full 1:1 copy. Cross-framework looks only at
    the path *origins* (the source audit's requirements); intermediate
    frameworks are transit points the user has no data for, even when they
    fully cover the target. Coverage is weakest-link (computed by the engine).
    """
    if same_framework:
        return True
    src_ras = source_ra.get("mapping_inference", {}).get(
        "source_requirement_assessments", {}
    )
    return any(
        v.get("coverage") == "full"
        for v in src_ras.values()
        if (v.get("source_framework") or {}).get("id") == origin_fw_id
    )


def merge_requirement(
    current,
    source_ra,
    *,
    is_full_coverage,
    same_framework,
    allowed_scalars=None,
    observation_allowed=True,
):
    """Merge one source RA into one target RA, in memory.

    Returns (merged_fields, field_changes, m2m_added):
    - merged_fields: values to write on the target
    - field_changes: before/after pairs for the preview diff
    - m2m_added: count of genuinely-new M2M links, by field

    *allowed_scalars*, when given, restricts the scalar fields that may
    flow — only fields visible on both source and target should be offered.
    """
    merged_fields = {}
    field_changes = {}

    # Full coverage copies from source; partial coverage only fills a target
    # still at its default. Either way, only a meaningful source value flows.
    for field, default in SCALAR_DEFAULTS.items():
        if allowed_scalars is not None and field not in allowed_scalars:
            continue
        current_val = current.get(field)
        engine_val = source_ra.get(field)
        engine_is_meaningful = engine_val is not None and engine_val != default
        target_is_default = current_val is None or current_val == default
        if engine_is_meaningful and (is_full_coverage or target_is_default):
            merged_fields[field] = engine_val
            if engine_val != current_val:
                field_changes[field] = {"current": current_val, "new": engine_val}

    # Observation: append unless the source text is already present (keeps
    # re-running from the same source idempotent).  Respect visibility.
    current_obs = current.get("observation") or ""
    engine_obs = source_ra.get("observation") or ""
    if observation_allowed and engine_obs and engine_obs not in current_obs:
        merged = (
            engine_obs if not current_obs else f"{current_obs}\n\n---\n{engine_obs}"
        )
        merged_fields["observation"] = merged
        field_changes["observation"] = {
            "current": current_obs or None,
            "new": merged,
        }

    # M2M: applied_controls flow for every coverage type; evidences and
    # security_exceptions only on full coverage (or same framework).
    m2m_added = {}
    m2m_fields = ["applied_controls"]
    if is_full_coverage or same_framework:
        m2m_fields += ["evidences", "security_exceptions"]
    for m2m_field in m2m_fields:
        new_ids = set(source_ra.get(m2m_field, [])) - set(current.get(m2m_field, []))
        if new_ids:
            m2m_added[m2m_field] = len(new_ids)

    # Carry the new mapping_inference (cross-framework only) so the RA is
    # included in merged_target -- this is what gates the M2M apply step.
    if not same_framework and source_ra.get("mapping_inference"):
        merged_fields["mapping_inference"] = source_ra["mapping_inference"]

    return merged_fields, field_changes, m2m_added


def map_from_sources(urn, source_ra, same_framework):
    """Source requirement(s) feeding a target, for the preview display.
    Carries urns; labels are resolved by the caller via safe_display_str."""
    if same_framework:
        return [{"urn": urn, "str": source_ra.get("name"), "coverage": "full"}]
    src_sras = source_ra.get("mapping_inference", {}).get(
        "source_requirement_assessments", {}
    )
    return [
        {
            "urn": s.get("urn"),
            "str": s.get("str"),
            "coverage": s.get("coverage"),
            "framework": (s.get("source_framework") or {}).get("name"),
        }
        for s in src_sras.values()
    ]


def compute_map_from_merge(target_audit, source_audit):
    """
    Compute the merge of source audit data into a target audit.

    Returns (mapped_results, merged_target, merge_details, target_data) where:
    - mapped_results: raw engine output (for M2M IDs)
    - merged_target: dict of {urn: merged_fields} for scalar updates
    - merge_details: list of per-RA merge info for preview/apply. Each entry
      carries a "meaningful" flag that is True only when the user-visible
      state actually changes (scalar/observation change or new M2M links) --
      a refreshed mapping_inference alone does not count.
    - target_data: load_audit_fields(target_audit), reused by the caller for
      IG-correct denominators and current/projected distributions.
    Returns (None, None, None, None) when no mapping path exists.
    """
    from core.mappings.engine import engine
    from core.views import get_mapping_max_depth

    source_urn = source_audit.framework.urn
    dest_urn = target_audit.framework.urn
    origin_fw_id = str(source_audit.framework_id)

    audit_from_results = engine.load_audit_fields(source_audit)

    same_framework = source_audit.framework_id == target_audit.framework_id

    if same_framework:
        mapped_results = audit_from_results
    else:
        max_depth = get_mapping_max_depth()
        mapped_results, _ = engine.best_mapping_inferences(
            audit_from_results, source_urn, dest_urn, max_depth
        )

    if not mapped_results or not mapped_results.get("requirement_assessments"):
        return None, None, None, None

    target_data = engine.load_audit_fields(target_audit)
    target_ras = target_data.get("requirement_assessments", {})

    # Only merge fields visible on both audits: the source must expose
    # the data and the target must accept it.
    allowed_scalars = {
        f
        for f in SCALAR_DEFAULTS
        if source_audit._auditor_visible(f) and target_audit._auditor_visible(f)
    }
    observation_allowed = source_audit._auditor_visible(
        "observation"
    ) and target_audit._auditor_visible("observation")

    merged_target = {}
    merge_details = []

    for urn, source_ra in mapped_results["requirement_assessments"].items():
        current = target_ras.get(urn)
        if current is None:
            continue

        is_full = is_full_coverage(source_ra, same_framework, origin_fw_id)
        merged_fields, field_changes, m2m_added = merge_requirement(
            current,
            source_ra,
            is_full_coverage=is_full,
            same_framework=same_framework,
            allowed_scalars=allowed_scalars,
            observation_allowed=observation_allowed,
        )
        meaningful = bool(field_changes) or bool(m2m_added)
        if not (merged_fields or meaningful):
            continue

        merged_target[urn] = merged_fields
        merge_details.append(
            {
                "urn": urn,
                "name": current.get("name", ""),
                "coverage": "full" if is_full else "partial",
                "field_changes": field_changes,
                "m2m_added": m2m_added,
                "sources": map_from_sources(urn, source_ra, same_framework),
                "meaningful": meaningful,
            }
        )

    return mapped_results, merged_target, merge_details, target_data
