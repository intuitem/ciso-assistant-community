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


def detect_sync_mode(ebios_rm_study):
    """
    Auto-detect the best sync mode based on available study data.
    Priority: operational_scenarios > attack_paths > feared_events.
    Returns (sync_mode, source_objects) or (None, None) if nothing is selected.
    """
    # Priority 1: selected operational scenarios (full EBIOS)
    selected_os = [
        os for os in ebios_rm_study.operational_scenarios.all() if os.is_selected
    ]
    if selected_os:
        return "operational_scenarios", selected_os

    # Priority 2: selected attack paths (WS3 light)
    selected_ap = list(ebios_rm_study.attackpath_set.filter(is_selected=True))
    if selected_ap:
        return "attack_paths", selected_ap

    # Priority 3: selected feared events (WS1 light)
    selected_fe = list(ebios_rm_study.feared_events.filter(is_selected=True))
    if selected_fe:
        return "feared_events", selected_fe

    return None, None


def build_sync_preview(ebios_rm_study, sync_mode, source_objects):
    """Build preview data for the sync confirmation modal."""
    parsed_matrix = ebios_rm_study.parsed_matrix
    source_data = []

    if sync_mode == "operational_scenarios":
        for os_obj in source_objects:
            gravity_display = FearedEvent.format_gravity(os_obj.gravity, parsed_matrix)
            likelihood_display = OperationalScenario.format_likelihood(
                os_obj.likelihood, parsed_matrix
            )
            source_data.append(
                {
                    "id": str(os_obj.id),
                    "name": os_obj.name,
                    "impact": gravity_display,
                    "likelihood": likelihood_display,
                }
            )
    elif sync_mode == "attack_paths":
        for ap in source_objects:
            gravity_display = FearedEvent.format_gravity(ap.gravity, parsed_matrix)
            source_data.append(
                {
                    "id": str(ap.id),
                    "name": str(ap),
                    "impact": gravity_display,
                    "likelihood": None,
                }
            )
    elif sync_mode == "feared_events":
        for fe in source_objects:
            gravity_display = fe.get_gravity_display()
            source_data.append(
                {
                    "id": str(fe.id),
                    "name": fe.name,
                    "impact": gravity_display,
                    "likelihood": None,
                }
            )

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


def _get_assets_from_feared_events(feared_events):
    """Get assets (with descendants) linked to a set of feared events."""
    initial_assets = Asset.objects.filter(feared_events__in=feared_events)
    assets = set()
    for asset in initial_assets:
        assets.add(asset)
        assets.update(asset.get_descendants())
    return Asset.objects.filter(id__in=[a.id for a in assets])


def sync_from_operational_scenarios(
    risk_assessment, ebios_rm_study, selected_operational_scenarios
):
    """Full EBIOS sync path using operational scenarios."""
    processed_os_ids = set()
    updated_count = 0
    created_count = 0
    archived_count = 0

    def build_description(operational_scenario):
        description_parts = []

        # Feared events
        ro_to = operational_scenario.ro_to
        feared_events = ro_to.feared_events.filter(is_selected=True)
        if feared_events.exists():
            feared_events_list = []
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
                feared_events_list.append(fe_text)
            feared_events_text = (
                f"**{_('Feared events').capitalize()}:**\n"
                + "\n".join(feared_events_list)
            )
            description_parts.append(feared_events_text)

        # Risk origin and target objective
        risk_origin_name = (
            ro_to.risk_origin.get_name_translated
            if hasattr(ro_to.risk_origin, "get_name_translated")
            else str(ro_to.risk_origin)
        )
        ro_to_text = f"**{_('Risk origin').capitalize()}:** {risk_origin_name}\n**{_('Target objective').capitalize()}:** {ro_to.target_objective}"
        description_parts.append(ro_to_text)

        # Strategic scenario
        strategic_scenario = operational_scenario.attack_path.strategic_scenario
        if strategic_scenario.description:
            description_parts.append(
                f"**{_('Strategic Scenario').capitalize()}:** {strategic_scenario.name}\n{strategic_scenario.description}"
            )
        elif strategic_scenario.name:
            description_parts.append(
                f"**{_('Strategic Scenario').capitalize()}:** {strategic_scenario.name}"
            )

        # Attack path
        attack_path = operational_scenario.attack_path
        if attack_path.description:
            description_parts.append(
                f"**{_('Attack path').capitalize()}:** {attack_path.name}\n{attack_path.description}"
            )
        elif attack_path.name:
            description_parts.append(
                f"**{_('Attack path').capitalize()}:** {attack_path.name}"
            )

        # Operating modes
        operating_modes = operational_scenario.operating_modes.all()
        if operating_modes.exists():
            operating_modes_list = []
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
                operating_modes_list.append(om_text)
            operating_modes_text = (
                f"**{_('operating modes').capitalize()}:**\n"
                + "\n".join(operating_modes_list)
            )
            description_parts.append(operating_modes_text)
        elif operational_scenario.operating_modes_description:
            description_parts.append(
                f"**{_('operating modes').capitalize()}:**\n{operational_scenario.operating_modes_description}"
            )

        return "\n\n".join(description_parts)

    for operational_scenario in selected_operational_scenarios:
        processed_os_ids.add(operational_scenario.id)
        scenario_name = operational_scenario.name

        # Try to find existing risk scenario
        risk_scenario = None
        try:
            risk_scenario = risk_assessment.risk_scenarios.get(
                operational_scenario=operational_scenario
            )
        except RiskScenario.DoesNotExist:
            risk_scenario = _find_existing_risk_scenario(risk_assessment, scenario_name)
            if risk_scenario:
                risk_scenario.operational_scenario = operational_scenario

        if risk_scenario:
            risk_scenario.name = scenario_name.replace("[ARCHIVED] ", "")
            risk_scenario.description = build_description(operational_scenario)
            risk_scenario.risk_origin = operational_scenario.ro_to.risk_origin
            _set_risk_level(
                risk_scenario,
                operational_scenario.gravity,
                operational_scenario.likelihood,
            )
            risk_scenario.save()
            risk_scenario.assets.set(operational_scenario.get_assets())
            risk_scenario.threats.set(operational_scenario.threats.all())
            current_existing_controls = set(
                risk_scenario.existing_applied_controls.all()
            )
            ebios_controls = set(operational_scenario.get_applied_controls())
            risk_scenario.existing_applied_controls.set(
                current_existing_controls | ebios_controls
            )
            updated_count += 1
        else:
            risk_scenario = RiskScenario(
                risk_assessment=risk_assessment,
                operational_scenario=operational_scenario,
                name=scenario_name,
                ref_id=operational_scenario.ref_id
                if operational_scenario.ref_id
                else RiskScenario.get_default_ref_id(risk_assessment),
                description=build_description(operational_scenario),
                risk_origin=operational_scenario.ro_to.risk_origin,
            )
            _set_risk_level(
                risk_scenario,
                operational_scenario.gravity,
                operational_scenario.likelihood,
            )
            risk_scenario.save()
            risk_scenario.assets.set(operational_scenario.get_assets())
            risk_scenario.threats.set(operational_scenario.threats.all())
            risk_scenario.existing_applied_controls.set(
                operational_scenario.get_applied_controls()
            )
            created_count += 1

    # Archive risk scenarios linked to operational scenarios no longer selected
    for risk_scenario in risk_assessment.risk_scenarios.filter(
        operational_scenario__isnull=False
    ):
        if risk_scenario.operational_scenario_id not in processed_os_ids:
            if not risk_scenario.name.startswith("[ARCHIVED] "):
                risk_scenario.name = f"[ARCHIVED] {risk_scenario.name}"
                risk_scenario.save()
                archived_count += 1

    return {
        "success": True,
        "sync_mode": "operational_scenarios",
        "updated": updated_count,
        "created": created_count,
        "archived": archived_count,
        "total_scenarios": risk_assessment.risk_scenarios.count(),
    }


def sync_from_attack_paths(risk_assessment, ebios_rm_study, selected_attack_paths):
    """Light sync from WS3 attack paths. Likelihood is left unset (-1)."""
    processed_names = set()
    updated_count = 0
    created_count = 0

    for attack_path in selected_attack_paths:
        scenario_name = str(attack_path)
        processed_names.add(scenario_name)

        # Build description
        description_parts = []
        ro_to = attack_path.ro_to_couple
        feared_events = ro_to.feared_events.filter(is_selected=True)
        if feared_events.exists():
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
            description_parts.append(
                f"**{_('Feared events').capitalize()}:**\n" + "\n".join(fe_list)
            )

        risk_origin_name = (
            ro_to.risk_origin.get_name_translated
            if hasattr(ro_to.risk_origin, "get_name_translated")
            else str(ro_to.risk_origin)
        )
        description_parts.append(
            f"**{_('Risk origin').capitalize()}:** {risk_origin_name}\n"
            f"**{_('Target objective').capitalize()}:** {ro_to.target_objective}"
        )

        strategic_scenario = attack_path.strategic_scenario
        if strategic_scenario.description:
            description_parts.append(
                f"**{_('Strategic Scenario').capitalize()}:** {strategic_scenario.name}\n{strategic_scenario.description}"
            )
        elif strategic_scenario.name:
            description_parts.append(
                f"**{_('Strategic Scenario').capitalize()}:** {strategic_scenario.name}"
            )

        if attack_path.description:
            description_parts.append(
                f"**{_('Attack path').capitalize()}:** {attack_path.name}\n{attack_path.description}"
            )
        elif attack_path.name:
            description_parts.append(
                f"**{_('Attack path').capitalize()}:** {attack_path.name}"
            )

        description = "\n\n".join(description_parts)
        asset_qs = _get_assets_from_feared_events(feared_events)

        # Get controls from stakeholders
        applied_controls = AppliedControl.objects.filter(
            stakeholders__in=attack_path.stakeholders.all()
        )

        risk_scenario = _find_existing_risk_scenario(risk_assessment, scenario_name)

        if risk_scenario:
            risk_scenario.name = scenario_name.replace("[ARCHIVED] ", "")
            risk_scenario.description = description
            risk_scenario.risk_origin = ro_to.risk_origin
            _set_risk_level(risk_scenario, attack_path.gravity, -1)
            risk_scenario.save()
            risk_scenario.assets.set(asset_qs)
            current_existing_controls = set(
                risk_scenario.existing_applied_controls.all()
            )
            risk_scenario.existing_applied_controls.set(
                current_existing_controls | set(applied_controls)
            )
            updated_count += 1
        else:
            risk_scenario = RiskScenario(
                risk_assessment=risk_assessment,
                name=scenario_name,
                ref_id=attack_path.ref_id
                if attack_path.ref_id
                else RiskScenario.get_default_ref_id(risk_assessment),
                description=description,
                risk_origin=ro_to.risk_origin,
            )
            _set_risk_level(risk_scenario, attack_path.gravity, -1)
            risk_scenario.save()
            risk_scenario.assets.set(asset_qs)
            risk_scenario.existing_applied_controls.set(applied_controls)
            created_count += 1

    archived_count = _archive_unprocessed(risk_assessment, processed_names)

    return {
        "success": True,
        "sync_mode": "attack_paths",
        "updated": updated_count,
        "created": created_count,
        "archived": archived_count,
        "total_scenarios": risk_assessment.risk_scenarios.count(),
    }


def sync_from_feared_events(risk_assessment, ebios_rm_study, selected_feared_events):
    """Light sync from WS1 feared events. Likelihood is left unset (-1)."""
    processed_names = set()
    updated_count = 0
    created_count = 0

    for fe in selected_feared_events:
        scenario_name = fe.name
        processed_names.add(scenario_name)

        # Build description
        description_parts = []
        gravity_display = fe.get_gravity_display()
        gravity_text = (
            f" [{_('Gravity').capitalize()}: {gravity_display['name']}]"
            if gravity_display["value"] >= 0
            else ""
        )
        description_parts.append(
            f"**{_('Feared event').capitalize()}:** {fe.name}{gravity_text}"
        )
        if fe.description:
            description_parts.append(fe.description)

        qualifications = fe.qualifications.all()
        if qualifications.exists():
            qual_names = ", ".join(
                q.get_name_translated if hasattr(q, "get_name_translated") else str(q)
                for q in qualifications
            )
            description_parts.append(
                f"**{_('Qualifications').capitalize()}:** {qual_names}"
            )

        description = "\n\n".join(description_parts)

        # Get assets from feared event
        initial_assets = fe.assets.all()
        assets = set()
        for asset in initial_assets:
            assets.add(asset)
            assets.update(asset.get_descendants())
        asset_qs = Asset.objects.filter(id__in=[a.id for a in assets])

        risk_scenario = _find_existing_risk_scenario(risk_assessment, scenario_name)

        if risk_scenario:
            risk_scenario.name = scenario_name.replace("[ARCHIVED] ", "")
            risk_scenario.description = description
            _set_risk_level(risk_scenario, fe.gravity, -1)
            risk_scenario.save()
            risk_scenario.assets.set(asset_qs)
            updated_count += 1
        else:
            risk_scenario = RiskScenario(
                risk_assessment=risk_assessment,
                name=scenario_name,
                ref_id=fe.ref_id
                if fe.ref_id
                else RiskScenario.get_default_ref_id(risk_assessment),
                description=description,
            )
            _set_risk_level(risk_scenario, fe.gravity, -1)
            risk_scenario.save()
            risk_scenario.assets.set(asset_qs)
            created_count += 1

    archived_count = _archive_unprocessed(risk_assessment, processed_names)

    return {
        "success": True,
        "sync_mode": "feared_events",
        "updated": updated_count,
        "created": created_count,
        "archived": archived_count,
        "total_scenarios": risk_assessment.risk_scenarios.count(),
    }
