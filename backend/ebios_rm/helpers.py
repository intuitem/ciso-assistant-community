from django.db.models.query import QuerySet
from django.utils.translation import gettext as _
import math
import random
from global_settings.models import GlobalSettings
from global_settings.utils import ff_is_enabled
from .models import (
    AttackPath,
    EbiosRMStudy,
    FearedEvent,
    OperationalScenario,
    RoTo,
    Stakeholder,
    StrategicScenario,
)
from core.models import AppliedControl, Asset, RiskScenario

import textwrap


def ecosystem_circular_chart_data(stakeholders_queryset: QuerySet):
    """
    Generate data for circular ecosystem chart.
    Returns stakeholders grouped by maturity clusters (cyber reliability) with simple format:
    {
        "maturity_groups": ["<4", "4-5", "6-7", ">7"],
        "current": {
            "<4": [[criticality, angle, exposure, label], ...],
            "4-5": [...],
            ...
        },
        "residual": { ... },
        "not_displayed": 0
    }
    """
    qs = stakeholders_queryset
    max_val = GlobalSettings.objects.get(name="general").value.get("ebios_radar_max", 6)

    def get_maturity_group(reliability_value):
        """Group by cyber reliability (maturity * trust)"""
        if reliability_value < 4:
            return "<4"
        if reliability_value >= 4 and reliability_value < 6:
            return "4-5"
        if reliability_value >= 6 and reliability_value <= 7:
            return "6-7"
        if reliability_value > 7:
            return ">7"
        return "<4"

    # Get unique categories for angle distribution
    categories = set()
    for sh in qs:
        if sh.category:
            categories.add(sh.category.name)

    categories_list = sorted(list(categories))
    num_categories = len(categories_list)

    if num_categories == 0:
        return {
            "maturity_groups": ["<4", "4-5", "6-7", ">7"],
            "current": {},
            "residual": {},
            "not_displayed": len(qs),
        }

    # Calculate angle section for each category
    angle_step = 360 / num_categories
    # Add offset to align properly: for 4 categories, shift by 45° to get + instead of X
    angle_offset = angle_step / 2
    category_angles = {}
    for i, cat in enumerate(categories_list):
        # Apply offset so boundaries align at 0°, 90°, 180°, 270° for 4 categories
        category_angles[cat] = {
            "base": i * angle_step + angle_offset,
            "start": i * angle_step,
            "end": (i + 1) * angle_step,
        }

    # Initialize data structures for maturity groups
    maturity_groups = ["<4", "4-5", "6-7", ">7"]
    current_data = {group: [] for group in maturity_groups}
    residual_data = {group: [] for group in maturity_groups}
    not_displayed = 0
    max_criticality_found = 0

    # Group stakeholders by category and maturity
    stakeholders_by_category = {cat: [] for cat in categories_list}
    for sh in qs:
        if not sh.category:
            not_displayed += 1
            continue
        category_name = sh.category.name
        stakeholders_by_category[category_name].append(sh)

    # Sort stakeholders within each category by current criticality (descending)
    for cat in categories_list:
        stakeholders_by_category[cat].sort(
            key=lambda sh: sh.current_criticality, reverse=True
        )

    # Process stakeholders category by category, ordered by criticality
    for category_name in categories_list:
        cat_stakeholders = stakeholders_by_category[category_name]
        cat_info = category_angles[category_name]
        section_width = angle_step * 0.8  # Use 80% of section width

        # Distribute stakeholders evenly within category's angular range
        num_in_category = len(cat_stakeholders)
        if num_in_category == 0:
            continue

        for idx, sh in enumerate(cat_stakeholders):
            # Distribute evenly across the section
            if num_in_category == 1:
                # Center single item
                offset = 0
            else:
                # Spread multiple items evenly
                offset = (idx / (num_in_category - 1) - 0.5) * section_width

            jitter = random.uniform(-2, 2)  # Small jitter for natural look
            angle = cat_info["base"] + offset + jitter

            # Normalize angle to 0-360
            angle = angle % 360

            # Current data
            c_criticality = math.floor(sh.current_criticality * 100) / 100.0
            c_exposure = sh.current_dependency * sh.current_penetration
            c_exposure_val = c_exposure * 4  # Scale for size
            c_reliability = sh.current_maturity * sh.current_trust
            c_maturity_group = get_maturity_group(c_reliability)

            # Track max criticality across both current and residual
            max_criticality_found = max(max_criticality_found, c_criticality)

            current_data[c_maturity_group].append(
                [
                    c_criticality,
                    angle,
                    c_exposure_val,
                    f"{sh.entity.name}-{category_name}",
                ]
            )

            # Residual data
            r_criticality = math.floor(sh.residual_criticality * 100) / 100.0
            r_exposure = sh.residual_dependency * sh.residual_penetration
            r_exposure_val = r_exposure * 4  # Scale for size
            r_reliability = sh.residual_maturity * sh.residual_trust
            r_maturity_group = get_maturity_group(r_reliability)

            # Track max criticality across both current and residual
            max_criticality_found = max(max_criticality_found, r_criticality)

            residual_data[r_maturity_group].append(
                [
                    r_criticality,
                    angle,
                    r_exposure_val,
                    f"{sh.entity.name}-{category_name}",
                ]
            )

    # Calculate consistent chart max for both current and residual comparison
    # Add small offset to ensure highest criticality points don't end up at center
    chart_max = (
        max(max_val, max_criticality_found) + 0.5
        if max_criticality_found > 0
        else max_val
    )

    # Prepare category boundaries for delimiter lines
    category_boundaries = []
    category_label_positions = []
    for i, cat in enumerate(categories_list):
        angle_info = category_angles[cat]
        # Add the start boundary of each category section (at 0°, 90°, 180°, 270° for 4 cats)
        boundary_angle = (i * angle_step) % 360
        category_boundaries.append(boundary_angle)
        # Add middle angle for category label positioning
        category_label_positions.append(
            {"category": cat, "angle": angle_info["base"] % 360}
        )

    return {
        "maturity_groups": maturity_groups,
        "categories": categories_list,
        "current": current_data,
        "residual": residual_data,
        "not_displayed": not_displayed,
        "chart_max": chart_max,
        "category_boundaries": category_boundaries,
        "category_label_positions": category_label_positions,
    }


def ecosystem_radar_chart_data(stakeholders_queryset: QuerySet):
    qs = stakeholders_queryset

    def add_jitter(value, max_jitter=5.0):
        """Add a small random offset to prevent perfect overlaps"""
        return value + random.uniform(-max_jitter, max_jitter)

    def get_exposure_segment_id(value):
        if value < 3:
            return 1
        if value >= 3 and value < 7:
            return 2
        if value >= 7 and value <= 9:
            return 3
        if value > 9:
            return 4
        return 0

    def get_reliability_cluster(value):
        if value < 4:
            return "clst1"
        if value >= 4 and value < 6:
            return "clst2"
        if value >= 6 and value <= 7:
            return "clst3"
        if value > 7:
            return "clst4"
        return 1

    """
    // data format: f1-f4 (fiabilité cyber = maturité x confiance ) to get the clusters and colors
    // x,y, z
    // x: criticité calculée avec cap basé sur le max finalement
    // y: the angle (output of dict to make sure they end up on the right quadrant, min: 45, max:-45) -> done on BE
    // z: the size of item (exposition = dependence x penetration) based on a dict, -> done on BE
    // label: name of the 3rd party entity
    Angles start at 56,25 (45+45/4) and end at -45-45/4 = 303,75
    """

    c_data = {"clst1": [], "clst2": [], "clst3": [], "clst4": []}
    r_data = {"clst1": [], "clst2": [], "clst3": [], "clst4": []}
    angle_offset = {"client": 135, "partner": 225, "supplier": 45}

    max_val = GlobalSettings.objects.get(name="general").value.get("ebios_radar_max", 6)

    for sh in qs:
        # current
        c_reliability = sh.current_maturity * sh.current_trust
        c_exposure = sh.current_dependency * sh.current_penetration
        c_exposure_val = get_exposure_segment_id(c_exposure) * 4

        c_criticality = (
            math.floor(sh.current_criticality * 100) / 100.0
            if sh.current_criticality <= max_val
            else max_val - 1 + 0.25
        )

        category_name = sh.category.name if sh.category else "partner"
        angle = angle_offset.get(category_name, 225) + (
            get_exposure_segment_id(c_exposure) * (45 / 4)
        )

        vector = [c_criticality, add_jitter(angle, 10), c_exposure_val, str(sh)]

        cluser_id = get_reliability_cluster(c_reliability)
        c_data[cluser_id].append(vector)

        # residual
        r_reliability = sh.residual_maturity * sh.residual_trust
        r_exposure = sh.residual_dependency * sh.residual_penetration
        r_exposure_val = get_exposure_segment_id(r_exposure) * 4

        r_criticality = (
            math.floor(sh.residual_criticality * 100) / 100.0
            if sh.residual_criticality <= max_val
            else max_val - 1 + 0.25
        )

        angle = angle_offset.get(category_name, 225) + (
            get_exposure_segment_id(r_exposure) * (45 / 4)
        )

        vector = [r_criticality, add_jitter(angle, 10), r_exposure_val, str(sh)]

        cluser_id = get_reliability_cluster(r_reliability)
        r_data[cluser_id].append(vector)

    return {"current": c_data, "residual": r_data}


def wrap_text(text, width=30):
    return textwrap.fill(text, width=width)


def ebios_rm_visual_analysis(study):
    tree = list()  # list of dict with strucuted data
    rotos = (
        RoTo.objects.filter(ebios_rm_study=study)
        .prefetch_related("feared_events__assets")
        .distinct()
    )
    nodes = []
    links = []
    nodes_idx = dict()
    N = 0
    categories = [
        {"name": "Asset"},
        {"name": "Feared Event"},
        {"name": "Risk Origin"},
        {"name": "Target Objective"},
        {"name": "Entity"},
        {"name": "Strategic scenario"},
        {"name": "Attack Path"},
        {"name": "Operational scenario"},
        {"name": "Operating Mode"},
        {"name": "Elementary action"},
    ]
    feared_events = FearedEvent.objects.filter(ebios_rm_study=study).distinct()
    assets = study.assets.all()
    stakeholders = Stakeholder.objects.filter(ebios_rm_study=study).distinct()
    for a in assets:
        nodes.append(
            {"name": a.name, "category": 0, "symbol": "diamond", "symbolSize": 40}
        )
        nodes_idx[f"{a.id}-AS"] = N
        N += 1
    for fe in feared_events:
        nodes.append(
            {
                "name": wrap_text(f"({fe.get_gravity_display()['name']}) {fe.name}"),
                "category": 1,
            }
        )
        nodes_idx[f"{fe.id}-FE"] = N
        N += 1
    for ro_to in rotos:
        nodes.append(
            {
                "name": ro_to.risk_origin.get_name_translated,
                "category": 2,
                "symbolSize": 25,
            }
        )
        nodes_idx[f"{ro_to.id}-RO"] = N
        N += 1
        nodes.append(
            {
                "name": wrap_text(ro_to.target_objective),
                "category": 3,
            }
        )
        nodes_idx[f"{ro_to.id}-TO"] = N
        N += 1
        links.append(
            {
                "source": nodes_idx[f"{ro_to.id}-RO"],
                "target": nodes_idx[f"{ro_to.id}-TO"],
                "value": "aims",
                "lineStyle": {"type": "dotted"},
            }
        )
        entry = {
            "ro": ro_to.risk_origin.get_name_translated,
            "to": ro_to.target_objective,
            "feared_events": [
                {"name": fe.name, "assets": [a.name for a in fe.assets.all()]}
                for fe in ro_to.feared_events.all()
            ],
        }
        for fe in ro_to.feared_events.all():
            links.append(
                {
                    "source": nodes_idx[f"{ro_to.id}-RO"],
                    "target": nodes_idx[f"{fe.id}-FE"],
                    "value": "generates",
                }
            )
            for a in fe.assets.all():
                links.append(
                    {
                        "source": nodes_idx[f"{fe.id}-FE"],
                        "target": nodes_idx[f"{a.id}-AS"],
                        "value": "concerns",
                    }
                )
        tree.append(entry)
    for stakeholder in stakeholders:
        nodes.append({"name": str(stakeholder), "category": 4, "symbol": "square"})
        nodes_idx[f"{stakeholder.id}-SH"] = N
        N += 1
    strategic_scenarios = StrategicScenario.objects.filter(
        ebios_rm_study=study
    ).prefetch_related("attack_paths__stakeholders")
    for ss in strategic_scenarios:
        nodes.append(
            {
                "name": f"{ss.name}",
                "symbol": "roundRect",
                "category": 5,
                "symbolSize": 25,
            }
        )
        nodes_idx[f"{ss.id}-SS"] = N
        N += 1

        # link to ss.ro_to_couple
        links.append(
            {
                "source": nodes_idx[f"{ss.id}-SS"],
                "target": nodes_idx[f"{ss.ro_to_couple.id}-RO"],
                "value": "through",
            }
        )
        for ap in AttackPath.objects.filter(strategic_scenario=ss):
            nodes.append(
                {
                    "name": ap.name,
                    "category": 6,
                }
            )
            nodes_idx[f"{ap.id}-AP"] = N
            N += 1

            links.append(
                {
                    "source": nodes_idx[f"{ap.id}-AP"],
                    "target": nodes_idx[f"{ss.id}-SS"],
                    "value": "used in",
                }
            )

            for sh in ap.stakeholders.all():
                links.append(
                    {
                        "source": nodes_idx[f"{ap.id}-AP"],
                        "target": nodes_idx[f"{sh.id}-SH"],
                        "lineStyle": {"type": "dashed"},
                        "value": "involves",
                    }
                )
    operational_scenarios = OperationalScenario.objects.filter(
        ebios_rm_study=study
    ).prefetch_related(
        "threats",
        "attack_path__strategic_scenario",
        "operating_modes__kill_chain_steps__elementary_action",
    )
    for os in operational_scenarios:
        # Use strategic scenario name + attack path name as display name
        display_name = (
            f"{os.attack_path.strategic_scenario.name} - {os.attack_path.name}"
        )
        nodes.append(
            {
                "name": f"{wrap_text(display_name)}",
                "category": 7,
            }
        )
        nodes_idx[f"{os.id}-OS"] = N
        N += 1
        links.append(
            {
                "source": nodes_idx[f"{os.id}-OS"],
                "target": nodes_idx[f"{os.attack_path.id}-AP"],
                "value": "involves",
            }
        )

        # Add operating modes for this operational scenario
        for om in os.operating_modes.all():
            nodes.append(
                {
                    "name": f"{wrap_text(om.name)}",
                    "category": 8,
                    "symbol": "circle",
                    "symbolSize": 20,
                }
            )
            nodes_idx[f"{om.id}-OM"] = N
            N += 1
            links.append(
                {
                    "source": nodes_idx[f"{om.id}-OM"],
                    "target": nodes_idx[f"{os.id}-OS"],
                    "value": "part of",
                }
            )

            # Link operating mode to its elementary actions (from kill chain)
            for step in om.kill_chain_steps.all():
                ea = step.elementary_action
                if nodes_idx.get(f"{ea.id}-EA") is None:
                    nodes.append({"name": ea.name, "category": 9, "symbol": "triangle"})
                    nodes_idx[f"{ea.id}-EA"] = N
                    N += 1
                links.append(
                    {
                        "source": nodes_idx[f"{om.id}-OM"],
                        "target": nodes_idx[f"{ea.id}-EA"],
                        "value": "uses",
                    }
                )

        # Also link OS to threats (if not already covered by operating modes)
        for ua in os.threats.all().distinct():
            if nodes_idx.get(f"{ua.id}-UA") is None:
                nodes.append({"name": ua.name, "category": 9, "symbol": "triangle"})
                nodes_idx[f"{ua.id}-UA"] = N
                N += 1
            links.append(
                {
                    "source": nodes_idx[f"{os.id}-OS"],
                    "target": nodes_idx[f"{ua.id}-UA"],
                    "value": "exploits",
                }
            )

    return {
        "tree": tree,
        "graph": {"nodes": nodes, "links": links, "categories": categories},
    }


# --- EBIOS RM → Risk Assessment sync helpers ---


def detect_sync_sources(ebios_rm_study):
    """
    Detect all available sync sources from the study.
    Handles hybrid cases: e.g. some feared events have attack paths, others don't.
    Each source level absorbs the feared events it covers, leaving uncovered ones
    to be handled at the feared_events level.

    Returns a dict with keys: operational_scenarios, attack_paths, feared_events.
    Each value is a list of source objects (may be empty).
    Returns None if nothing is selected at all.
    """
    result = {
        "operational_scenarios": [],
        "attack_paths": [],
        "feared_events": [],
    }

    # Track which feared events are already covered by higher-level objects
    covered_fe_ids = set()

    # Level 1: selected operational scenarios (full EBIOS)
    selected_os = [
        os for os in ebios_rm_study.operational_scenarios.all() if os.is_selected
    ]
    if selected_os:
        result["operational_scenarios"] = selected_os
        for os_obj in selected_os:
            covered_fe_ids.update(
                os_obj.ro_to.feared_events.filter(is_selected=True).values_list(
                    "id", flat=True
                )
            )

    # Level 2: selected attack paths not already covered by an operational scenario
    selected_ap = list(ebios_rm_study.attackpath_set.filter(is_selected=True))
    # Exclude attack paths that already have an operational scenario in the selected set
    covered_ap_ids = (
        {os_obj.attack_path_id for os_obj in selected_os} if selected_os else set()
    )
    uncovered_ap = [ap for ap in selected_ap if ap.id not in covered_ap_ids]
    if uncovered_ap:
        result["attack_paths"] = uncovered_ap
        for ap in uncovered_ap:
            covered_fe_ids.update(
                ap.ro_to_couple.feared_events.filter(is_selected=True).values_list(
                    "id", flat=True
                )
            )

    # Level 3: selected feared events not already covered
    selected_fe = list(ebios_rm_study.feared_events.filter(is_selected=True))
    uncovered_fe = [fe for fe in selected_fe if fe.id not in covered_fe_ids]
    if uncovered_fe:
        result["feared_events"] = uncovered_fe

    if not any(result.values()):
        return None

    return result


def build_sync_preview(ebios_rm_study, sources):
    """Build preview data for the sync confirmation modal."""
    parsed_matrix = ebios_rm_study.parsed_matrix
    source_data = []

    for os_obj in sources.get("operational_scenarios", []):
        gravity_display = FearedEvent.format_gravity(os_obj.gravity, parsed_matrix)
        likelihood_display = OperationalScenario.format_likelihood(
            os_obj.likelihood, parsed_matrix
        )
        source_data.append(
            {
                "id": str(os_obj.id),
                "name": os_obj.name,
                "source_type": "operational_scenario",
                "impact": gravity_display,
                "likelihood": likelihood_display,
            }
        )

    for ap in sources.get("attack_paths", []):
        gravity_display = FearedEvent.format_gravity(ap.gravity, parsed_matrix)
        source_data.append(
            {
                "id": str(ap.id),
                "name": str(ap),
                "source_type": "attack_path",
                "impact": gravity_display,
                "likelihood": None,
            }
        )

    for fe in sources.get("feared_events", []):
        gravity_display = fe.get_gravity_display()
        source_data.append(
            {
                "id": str(fe.id),
                "name": fe.name,
                "source_type": "feared_event",
                "impact": gravity_display,
                "likelihood": None,
            }
        )

    # Determine the sync mode label for the frontend
    active_modes = [k for k, v in sources.items() if v]
    if len(active_modes) == 1:
        sync_mode = active_modes[0]
    else:
        sync_mode = "mixed"

    return {
        "sync_mode": sync_mode,
        "source_objects": source_data,
        "count": len(source_data),
    }


def _set_risk_level(risk_scenario, impact, likelihood):
    """Set impact/likelihood on a risk scenario respecting the inherent_risk feature flag."""
    if ff_is_enabled("inherent_risk"):
        risk_scenario.inherent_proba = likelihood
        risk_scenario.inherent_impact = impact
    else:
        risk_scenario.current_proba = likelihood
        risk_scenario.current_impact = impact


def _find_existing_risk_scenario(risk_assessment, name):
    """Try to find an existing risk scenario by name (with or without [ARCHIVED] prefix)."""
    clean_name = name.replace("[ARCHIVED] ", "")
    try:
        return risk_assessment.risk_scenarios.get(name=clean_name)
    except RiskScenario.DoesNotExist:
        try:
            return risk_assessment.risk_scenarios.get(name=f"[ARCHIVED] {clean_name}")
        except RiskScenario.DoesNotExist:
            return None


def _get_assets_with_descendants(assets_qs):
    """Expand an asset queryset to include all descendants."""
    assets = set()
    for asset in assets_qs:
        assets.add(asset)
        assets.update(asset.get_descendants())
    return Asset.objects.filter(id__in=[a.id for a in assets])


# --- Description building blocks ---


def _describe_feared_events(feared_events):
    """Build feared events description section from a queryset."""
    if not feared_events.exists():
        return None
    fe_list = []
    for fe in feared_events:
        gravity_display = fe.get_gravity_display()
        gravity_text = (
            f" [{_('Gravity').capitalize()}: {gravity_display['name']}]"
            if gravity_display["value"] >= 0
            else ""
        )
        fe_text = f"- {fe.name}{gravity_text}"
        if fe.description:
            fe_text += f": {fe.description}"
        fe_list.append(fe_text)
    return f"**{_('Feared events').capitalize()}:**\n" + "\n".join(fe_list)


def _describe_ro_to(ro_to):
    """Build risk origin / target objective description section."""
    risk_origin_name = (
        ro_to.risk_origin.get_name_translated
        if hasattr(ro_to.risk_origin, "get_name_translated")
        else str(ro_to.risk_origin)
    )
    return (
        f"**{_('Risk origin').capitalize()}:** {risk_origin_name}\n"
        f"**{_('Target objective').capitalize()}:** {ro_to.target_objective}"
    )


def _describe_named_object(label, obj):
    """Build a description section for an object with name and optional description."""
    if obj.description:
        return f"**{_(label).capitalize()}:** {obj.name}\n{obj.description}"
    elif obj.name:
        return f"**{_(label).capitalize()}:** {obj.name}"
    return None


def _describe_operating_modes(operational_scenario):
    """Build operating modes description section."""
    operating_modes = operational_scenario.operating_modes.all()
    if operating_modes.exists():
        om_list = []
        for om in operating_modes:
            likelihood_display = om.get_likelihood_display()
            likelihood_text = (
                f" [{_('Likelihood').capitalize()}: {likelihood_display['name']}]"
                if likelihood_display["value"] >= 0
                else ""
            )
            om_text = f"- {om.name}{likelihood_text}"
            if om.description:
                om_text += f": {om.description}"
            om_list.append(om_text)
        return f"**{_('operating modes').capitalize()}:**\n" + "\n".join(om_list)
    elif operational_scenario.operating_modes_description:
        return (
            f"**{_('operating modes').capitalize()}:**\n"
            f"{operational_scenario.operating_modes_description}"
        )
    return None


def _build_description(*parts):
    """Join non-None description parts."""
    return "\n\n".join(p for p in parts if p)


# --- Upsert helper ---


def _upsert_risk_scenario(
    risk_assessment,
    name,
    ref_id,
    description,
    impact,
    likelihood,
    assets=None,
    threats=None,
    existing_controls=None,
    risk_origin=None,
    extra_fields=None,
):
    """
    Find-or-create a risk scenario and set its fields.
    Returns (risk_scenario, created: bool).
    """
    risk_scenario = _find_existing_risk_scenario(risk_assessment, name)
    created = risk_scenario is None

    if risk_scenario:
        risk_scenario.name = name.replace("[ARCHIVED] ", "")
        risk_scenario.description = description
        if risk_origin is not None:
            risk_scenario.risk_origin = risk_origin
        if extra_fields:
            for k, v in extra_fields.items():
                setattr(risk_scenario, k, v)
    else:
        risk_scenario = RiskScenario(
            risk_assessment=risk_assessment,
            name=name,
            ref_id=ref_id or RiskScenario.get_default_ref_id(risk_assessment),
            description=description,
            risk_origin=risk_origin,
            **(extra_fields or {}),
        )

    _set_risk_level(risk_scenario, impact, likelihood)
    risk_scenario.save()

    if assets is not None:
        risk_scenario.assets.set(assets)
    if threats is not None:
        risk_scenario.threats.set(threats)
    if existing_controls is not None:
        if not created:
            # Merge: keep user-added + update from EBIOS RM
            current = set(risk_scenario.existing_applied_controls.all())
            risk_scenario.existing_applied_controls.set(
                current | set(existing_controls)
            )
        else:
            risk_scenario.existing_applied_controls.set(existing_controls)

    return risk_scenario, created


def _archive_unprocessed(risk_assessment, processed_names):
    """Archive risk scenarios whose name is not in the processed set."""
    archived_count = 0
    for risk_scenario in risk_assessment.risk_scenarios.all():
        clean_name = risk_scenario.name.replace("[ARCHIVED] ", "")
        if clean_name not in processed_names:
            if not risk_scenario.name.startswith("[ARCHIVED] "):
                risk_scenario.name = f"[ARCHIVED] {risk_scenario.name}"
                risk_scenario.save()
                archived_count += 1
    return archived_count


# --- Sync functions ---


def _sync_operational_scenarios(risk_assessment, selected):
    """Full EBIOS sync path using operational scenarios."""
    updated_count = 0
    created_count = 0

    for operational_scenario in selected:
        scenario_name = operational_scenario.name
        ro_to = operational_scenario.ro_to
        feared_events = ro_to.feared_events.filter(is_selected=True)

        description = _build_description(
            _describe_feared_events(feared_events),
            _describe_ro_to(ro_to),
            _describe_named_object(
                "Strategic Scenario",
                operational_scenario.attack_path.strategic_scenario,
            ),
            _describe_named_object("Attack path", operational_scenario.attack_path),
            _describe_operating_modes(operational_scenario),
        )

        _rs, created = _upsert_risk_scenario(
            risk_assessment=risk_assessment,
            name=scenario_name,
            ref_id=operational_scenario.ref_id,
            description=description,
            impact=operational_scenario.gravity,
            likelihood=operational_scenario.likelihood,
            assets=operational_scenario.get_assets(),
            threats=operational_scenario.threats.all(),
            existing_controls=operational_scenario.get_applied_controls(),
            risk_origin=ro_to.risk_origin,
            extra_fields={"operational_scenario": operational_scenario},
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    return updated_count, created_count, {os.name for os in selected}


def _sync_attack_paths(risk_assessment, selected):
    """Light sync from WS3 attack paths. Likelihood is left unset (-1)."""
    updated_count = 0
    created_count = 0

    for attack_path in selected:
        ro_to = attack_path.ro_to_couple
        feared_events = ro_to.feared_events.filter(is_selected=True)

        description = _build_description(
            _describe_feared_events(feared_events),
            _describe_ro_to(ro_to),
            _describe_named_object(
                "Strategic Scenario", attack_path.strategic_scenario
            ),
            _describe_named_object("Attack path", attack_path),
        )

        _rs, created = _upsert_risk_scenario(
            risk_assessment=risk_assessment,
            name=str(attack_path),
            ref_id=attack_path.ref_id,
            description=description,
            impact=attack_path.gravity,
            likelihood=-1,
            assets=_get_assets_with_descendants(
                Asset.objects.filter(feared_events__in=feared_events)
            ),
            existing_controls=AppliedControl.objects.filter(
                stakeholders__in=attack_path.stakeholders.all()
            ),
            risk_origin=ro_to.risk_origin,
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    return updated_count, created_count, {str(ap) for ap in selected}


def _sync_feared_events(risk_assessment, selected):
    """Light sync from WS1 feared events. Likelihood is left unset (-1)."""
    updated_count = 0
    created_count = 0

    for fe in selected:
        gravity_display = fe.get_gravity_display()
        gravity_text = (
            f" [{_('Gravity').capitalize()}: {gravity_display['name']}]"
            if gravity_display["value"] >= 0
            else ""
        )
        fe_desc = f"**{_('Feared event').capitalize()}:** {fe.name}{gravity_text}"

        qual_desc = None
        qualifications = fe.qualifications.all()
        if qualifications.exists():
            qual_names = ", ".join(
                q.get_name_translated if hasattr(q, "get_name_translated") else str(q)
                for q in qualifications
            )
            qual_desc = f"**{_('Qualifications').capitalize()}:** {qual_names}"

        description = _build_description(fe_desc, fe.description, qual_desc)

        _rs, created = _upsert_risk_scenario(
            risk_assessment=risk_assessment,
            name=fe.name,
            ref_id=fe.ref_id,
            description=description,
            impact=fe.gravity,
            likelihood=-1,
            assets=_get_assets_with_descendants(fe.assets.all()),
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    return updated_count, created_count, {fe.name for fe in selected}


def sync_risk_assessment(risk_assessment, sources):
    """
    Unified sync entry point. Runs all applicable sync paths from the sources dict.
    Creates or updates risk scenarios, and archives those no longer covered.
    """
    total_updated = 0
    total_created = 0
    all_processed_names = set()
    active_modes = []

    sync_funcs = {
        "operational_scenarios": _sync_operational_scenarios,
        "attack_paths": _sync_attack_paths,
        "feared_events": _sync_feared_events,
    }

    for mode, func in sync_funcs.items():
        selected = sources.get(mode, [])
        if selected:
            updated, created, processed_names = func(risk_assessment, selected)
            total_updated += updated
            total_created += created
            all_processed_names.update(processed_names)
            active_modes.append(mode)

    # Archive risk scenarios that are no longer covered by any source
    total_archived = _archive_unprocessed(risk_assessment, all_processed_names)

    sync_mode = active_modes[0] if len(active_modes) == 1 else "mixed"

    return {
        "success": True,
        "sync_mode": sync_mode,
        "updated": total_updated,
        "created": total_created,
        "archived": total_archived,
        "total_scenarios": risk_assessment.risk_scenarios.count(),
    }
