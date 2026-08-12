"""
Helper functions for importing EBIOS RM studies from Egerie Suite's XML export.

The Egerie XML format ("analysis" root, EgerieSuite_v4.x) stores the study as a
single XML document. Sections we consume: <meta> (study metadata),
<system> (assets, owners, risk sources, objectives, stakeholders),
<assessment> (feared events, controls, strategic/operational scenarios,
elementary actions).
Scales are expressed as floats in [0..1] (the "percent" of a 4-level scale);
they're carried through unchanged here and mapped to matrix indices at import
time so the target risk matrix can be honored.
"""

import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Optional

# defusedxml hardens the stdlib parser against XXE, billion-laughs, etc. We
# only need its safe `parse`; the resulting tree is a regular stdlib ElementTree,
# so all the iteration/typing below still uses xml.etree.ElementTree.
from defusedxml.ElementTree import parse as safe_xml_parse

EGERIE_NS = "http://www.egerie-software.com/riskmanager"


def _strip_namespace(root: ET.Element) -> None:
    """Strip the Egerie namespace prefix from every element in the tree."""
    prefix = f"{{{EGERIE_NS}}}"
    for elem in root.iter():
        if elem.tag.startswith(prefix):
            elem.tag = elem.tag[len(prefix) :]


def _text(elem: Optional[ET.Element], default: str = "") -> str:
    if elem is None or elem.text is None:
        return default
    return elem.text.strip()


def _float(elem: Optional[ET.Element]) -> Optional[float]:
    if elem is None or elem.text is None or not elem.text.strip():
        return None
    try:
        return float(elem.text.strip())
    except ValueError:
        return None


def _label(elem: ET.Element) -> str:
    """Pull the localized <label> child text, falling back to empty string."""
    return _text(elem.find("label"))


def _description(elem: ET.Element) -> str:
    return _text(elem.find("description"))


def _ref(elem: Optional[ET.Element]) -> str:
    if elem is None:
        return ""
    return elem.attrib.get("ref", "")


def quartile_to_index(percent: Optional[float], matrix_size: int) -> Optional[int]:
    """Map an Egerie percent ([0..1]) to a 0-indexed matrix level.

    Egerie's 4-level scales use percents 0, 0.3333, 0.6667, 1.0; on a 4-level
    matrix this returns 0/1/2/3 cleanly. Free-text intermediate values round to
    the nearest level.
    """
    if percent is None or matrix_size <= 0:
        return None
    return max(0, min(matrix_size - 1, int(round(percent * (matrix_size - 1)))))


def extract_study(root: ET.Element) -> dict:
    meta = root.find("meta")
    if meta is None:
        return {"name": "", "description": "", "ref_id": "", "version": ""}
    return {
        "name": _label(meta) or root.attrib.get("id", ""),
        "description": _description(meta),
        "ref_id": root.attrib.get("id", ""),
        "version": root.attrib.get("version", ""),
        "system_description": _text(meta.find("systemDescription")),
        "system_objective": _text(meta.find("systemObjective")),
        "system_constraints": _text(meta.find("systemConstraints")),
        "context_and_issues": _text(meta.find("contextAndIssues")),
        "method": _text(meta.find("method")),
    }


def extract_primary_assets(root: ET.Element) -> list:
    assets = []
    for pa in root.iterfind("./system/primaryAssets/primaryAsset"):
        # Egerie marks the asset's nature via an empty child tag (e.g. <information/>,
        # <process/>, <personalDataRelated/>); these are kind hints, not children we need.
        assets.append(
            {
                "id": pa.attrib.get("id", ""),
                "name": _label(pa),
                "description": _description(pa),
                "type": "PR",  # primary
            }
        )
    return assets


def extract_supporting_assets(root: ET.Element) -> list:
    assets = []
    for sa in root.iterfind("./system/supportingAssets/supportingAsset"):
        assets.append(
            {
                "id": sa.attrib.get("id", ""),
                "name": _label(sa),
                "description": _description(sa),
                "type": "SP",  # supporting
            }
        )
    return assets


def extract_risk_sources(root: ET.Element) -> list:
    sources = []
    for rs in root.iterfind("./system/riskSources/riskSource"):
        sources.append(
            {
                "id": rs.attrib.get("id", ""),
                "name": _label(rs),
                "category_ref": _ref(rs.find("category")),
                "objective_ids": [
                    o.attrib.get("ref", "")
                    for o in rs.iterfind("./objectives/objective")
                    if o.attrib.get("ref")
                ],
            }
        )
    return sources


def extract_objectives(root: ET.Element) -> list:
    objectives = []
    for ob in root.iterfind("./system/objectives/objective"):
        objectives.append(
            {
                "id": ob.attrib.get("id", ""),
                "name": _label(ob),
                "category_ref": _ref(ob.find("category")),
            }
        )
    return objectives


def extract_owners(root: ET.Element) -> list:
    owners = []
    for o in root.iterfind("./system/owners/owner"):
        owners.append(
            {
                "id": o.attrib.get("id", ""),
                "full_name": _text(o.find("fullName")),
                "service": _text(o.find("service")),
                "email": _text(o.find("email")),
            }
        )
    return owners


def extract_feared_events(root: ET.Element) -> list:
    events = []
    for fe in root.iterfind("./assessment/fearedEvents/fearedEvent"):
        events.append(
            {
                "id": fe.attrib.get("id", ""),
                "name": _label(fe),
                "description": _description(fe),
                "primary_asset_id": _ref(fe.find("primaryAsset")),
                "severity": _float(fe.find("severity")),
                "objective_category_refs": [
                    _ref(oc)
                    for oc in fe.iterfind("./objectiveCategories/objectiveCategory")
                ],
            }
        )
    return events


def extract_stakeholders(root: ET.Element) -> list:
    stakeholders = []
    for sh in root.iterfind("./system/stakeholders/stakeholder"):
        stakeholders.append(
            {
                "id": sh.attrib.get("id", ""),
                "name": _label(sh),
                "description": _description(sh),
                "category_ref": _ref(sh.find("category")),
                "supporting_asset_id": sh.attrib.get("supportingAsset", ""),
                "dependence": _float(sh.find("dependence")),
                "penetration": _float(sh.find("penetration")),
                "maturity": _float(sh.find("maturity")),
                "trust": _float(sh.find("trust")),
            }
        )
    return stakeholders


def _extract_strategic_scenario(ss: ET.Element) -> dict:
    """One <strategicScenario>; the EBIOS pair lives in <links> (one riskSource
    + one objective + N fearedEvents)."""
    links = ss.find("links")
    risk_source_ref = ""
    objective_ref = ""
    feared_event_refs: list[str] = []
    if links is not None:
        rs = links.find("riskSource")
        if rs is not None:
            risk_source_ref = rs.attrib.get("ref", "")
        ob = links.find("objective")
        if ob is not None:
            objective_ref = ob.attrib.get("ref", "")
        for fe in links.iterfind("fearedEvent"):
            ref = fe.attrib.get("ref", "")
            if ref:
                feared_event_refs.append(ref)

    attack_paths = []
    for ap in ss.iterfind("./attackPaths/attackPath"):
        attack_paths.append(
            {
                "id": ap.attrib.get("id", ""),
                # The riskSource/objective refs inside attackPath point at graph-node
                # UUIDs (not the canonical RS_/O_ ids in <context>). They're kept for
                # traceability but the canonical pair lives on the parent scenario.
                "graph_risk_source_uuid": _ref(ap.find("riskSource")),
                "graph_objective_uuid": _ref(ap.find("objective")),
            }
        )

    return {
        "id": ss.attrib.get("id", ""),
        "name": _label(ss),
        "risk_source_id": risk_source_ref,
        "objective_id": objective_ref,
        "feared_event_ids": feared_event_refs,
        "resources": _float(ss.find("resources")),
        "motivation": _float(ss.find("motivation")),
        "severity": _float(ss.find("severity")),
        "attack_paths": attack_paths,
    }


def extract_strategic_scenarios(root: ET.Element) -> list:
    return [
        _extract_strategic_scenario(ss)
        for ss in root.iterfind("./assessment/strategicScenarios/strategicScenario")
    ]


def _extract_operational_scenario(os_elem: ET.Element) -> dict:
    links = os_elem.find("links")
    strategic_scenario_ids: list[str] = []
    attack_path_ids: list[str] = []
    feared_event_ids: list[str] = []
    risk_source_ids: list[str] = []
    if links is not None:
        for ss in links.iterfind("strategicScenario"):
            ref = ss.attrib.get("ref", "")
            if ref:
                strategic_scenario_ids.append(ref)
        for ap in links.iterfind("attackPath"):
            ref = ap.attrib.get("ref", "")
            if ref:
                attack_path_ids.append(ref)
        for fe in links.iterfind("fearedEvent"):
            ref = fe.attrib.get("ref", "")
            if ref:
                feared_event_ids.append(ref)
        for rs in links.iterfind("riskSource"):
            ref = rs.attrib.get("ref", "")
            if ref:
                risk_source_ids.append(ref)

    control_refs = []
    for c in os_elem.iterfind("./mitigation/risk/controls/control"):
        ref = c.attrib.get("ref", "")
        coverage = _float(c.find("coverage"))
        if ref:
            control_refs.append({"ref": ref, "coverage": coverage})

    return {
        "id": os_elem.attrib.get("id", ""),
        "name": _label(os_elem),
        "likelihood": _float(os_elem.find("likelihood")),
        "severity": _float(os_elem.find("severity")),
        "strategic_scenario_ids": strategic_scenario_ids,
        "attack_path_ids": attack_path_ids,
        "feared_event_ids": feared_event_ids,
        "risk_source_ids": risk_source_ids,
        "control_refs": control_refs,
    }


def extract_operational_scenarios(root: ET.Element) -> list:
    return [
        _extract_operational_scenario(os_elem)
        for os_elem in root.iterfind(
            "./assessment/operationalScenarios/operationalScenario"
        )
    ]


def extract_elementary_actions(root: ET.Element) -> list:
    actions = []
    for ea in root.iterfind("./assessment/elementaryActions/elementaryAction"):
        supporting_asset_ids = [
            sa.attrib.get("ref", "")
            for sa in ea.iterfind("./links/supportingAsset")
            if sa.attrib.get("ref")
        ]
        actions.append(
            {
                "id": ea.attrib.get("id", ""),
                "name": _label(ea),
                "description": _description(ea),
                "category_ref": _ref(ea.find("category")),
                "complexity": _float(ea.find("complexity")),
                "success": _float(ea.find("success")),
                "supporting_asset_ids": supporting_asset_ids,
            }
        )
    return actions


def extract_controls(root: ET.Element) -> list:
    """Egerie security controls.

    Status is decoded from <implementation><default>...</default></implementation>.
    Egerie values: 'inactive', 'planned', 'applied' (and a few v3 variants).
    """
    controls = []
    for c in root.iterfind("./assessment/controls/control"):
        impl = c.find("implementation")
        default_status = ""
        if impl is not None:
            default_status = _text(impl.find("default"))
        controls.append(
            {
                "id": c.attrib.get("id", ""),
                "name": _label(c),
                "description": _description(c),
                "category": c.attrib.get("category", ""),
                "parent_id": _ref(c.find("parent")),
                "owner_id": _ref(c.find("owner")),
                "egerie_status": default_status,
            }
        )
    return controls


# Egerie implementation status -> CISO Assistant AppliedControl.status.
# CISO has no "planned" intermediate state; fold it into "to_do".
_EGERIE_STATUS_MAP = {
    "inactive": "to_do",
    "planned": "to_do",
    "in_progress": "in_progress",
    "applied": "active",
    "active": "active",
    "deprecated": "deprecated",
}


def map_egerie_status(egerie_status: Optional[str]) -> str:
    return _EGERIE_STATUS_MAP.get((egerie_status or "").lower(), "")


def process_xml_file(file_content: bytes) -> dict:
    """Parse an Egerie analysis XML and return a normalized dict.

    Output keys mirror the structure used by ebios_rm_excel_helpers but include
    Egerie-specific fields (id, raw float scores) so the importer can resolve
    cross-references and apply matrix-aware quartile mapping.
    """
    tree = safe_xml_parse(BytesIO(file_content))
    root = tree.getroot()
    if root is None:
        raise ValueError("Egerie XML document is empty or malformed")
    _strip_namespace(root)

    return {
        "study": extract_study(root),
        "primary_assets": extract_primary_assets(root),
        "supporting_assets": extract_supporting_assets(root),
        "risk_sources": extract_risk_sources(root),
        "objectives": extract_objectives(root),
        "owners": extract_owners(root),
        "feared_events": extract_feared_events(root),
        "stakeholders": extract_stakeholders(root),
        "strategic_scenarios": extract_strategic_scenarios(root),
        "operational_scenarios": extract_operational_scenarios(root),
        "elementary_actions": extract_elementary_actions(root),
        "controls": extract_controls(root),
    }
