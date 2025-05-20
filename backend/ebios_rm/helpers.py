from django.db.models.query import QuerySet
import math
import random
from global_settings.models import GlobalSettings
from .models import (
    AttackPath,
    EbiosRMStudy,
    FearedEvent,
    OperationalScenario,
    RoTo,
    Stakeholder,
    StrategicScenario,
)
from core.models import Asset

import textwrap


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

        angle = angle_offset[sh.category] + (
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

        angle = angle_offset[sh.category] + (
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
        {"name": "Ecosystem entity"},
        {"name": "Strategic scenario"},
        {"name": "Attack Path"},
        {"name": "Operational scenario"},
        {"name": "Techniques/Unitary actions"},
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
                "name": ro_to.risk_origin,
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
            "ro": ro_to.risk_origin,
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
    ).prefetch_related("threats", "attack_path")
    for os in operational_scenarios:
        nodes.append(
            {
                "name": f"{wrap_text(os.operating_modes_description)}",
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
        for ua in os.threats.all().distinct():
            if nodes_idx.get(f"{ua.id}-UA") is None:
                nodes.append({"name": ua.name, "category": 8, "symbol": "triangle"})
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
