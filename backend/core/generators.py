import io
from math import ceil

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from django.db.models import Count
from django.utils.timezone import now
from docx.shared import Cm
from docxtpl import InlineImage
from library.helpers import get_referential_translation

from .utils import is_field_visible_to

from .models import (
    AppliedControl,
    Commitment,
    ComplianceAssessment,
    RequirementAssessment,
    RequirementNode,
    TaskTemplate,
)

matplotlib.use("Agg")


def plot_horizontal_bar(data, colors=None, title=None):
    """
    Create a horizontal bar chart from the input data

    Args:
        data (list): List of dictionaries with 'category' and 'value' keys
        colors (list, optional): Custom color palette
        title (str, optional): Chart title

    Returns:
        io.BytesIO: Buffer containing the horizontal bar chart image
    """
    plt.close("all")

    categories = [item["category"] for item in data]
    values = [item["value"] for item in data]

    default_colors = [
        "#2196F3",  # Blue
        "#4CAF50",  # Green
        "#FFC107",  # Amber
        "#F44336",  # Red
        "#9C27B0",  # Purple
    ]

    plt.figure(figsize=(10, 6))
    plot_colors = colors if colors is not None else default_colors[: len(categories)]
    plt.barh(categories, values, color=plot_colors)
    for i, v in enumerate(values):
        plt.text(v, i, f" {v}", va="center")

    if title:
        plt.title(title)

    plt.tight_layout()

    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format="png", dpi=300)
    chart_buffer.seek(0)
    plt.close()

    return chart_buffer


def plot_donut(data, colors=None):
    """
    Create a donut chart from the input data

    Args:
        data (list): List of dictionaries with 'category' and 'value' keys

    Returns:
        io.BytesIO: Buffer containing the donut chart image
    """
    plt.close("all")

    plt.figure(figsize=(10, 6))

    values = [item["value"] for item in data]
    labels = [item["category"] for item in data]

    default_colors = [
        "#4CAF50",  # Green for Compliant
        "#FFC107",  # Amber for Partially Compliant
        "#F44336",  # Red for Non-Compliant
        "#9C27B0",  # Purple for Not Applicable
        "#2196F3",  # Blue for Not Assessed
    ]

    if sum(values) == 0:
        values = [1]
        labels = ["Not assessed"]
        plot_colors = ["#2196F3"]
    else:
        plot_colors = colors if colors is not None else default_colors[: len(values)]
    plt.pie(
        values,
        labels=labels,
        colors=plot_colors,
        autopct="%1.f%%",  # Show percentage
        startangle=90,
        pctdistance=0.85,  # Distance of percentage from the center
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )

    center_circle = plt.Circle((0, 0), 0.60, fc="white", ec="white")
    fig = plt.gcf()
    fig.gca().add_artist(center_circle)

    plt.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle
    plt.tight_layout()

    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format="png", dpi=300)
    chart_buffer.seek(0)
    plt.close()

    return chart_buffer


def plot_completion_bar(data, colors=None, title=None):
    """
    Create a vertical bar chart showing completion percentage per category

    Args:
        data (list): List of dictionaries with 'category' and 'value' keys
        colors (list, optional): Custom color palette
        title (str, optional): Chart title

    Returns:
        io.BytesIO: Buffer containing the bar chart image
    """
    plt.close("all")

    categories = [item["category"] for item in data]
    values = [item["value"] for item in data]

    default_colors = [
        "#2196F3",  # Blue
        "#4CAF50",  # Green
        "#FFC107",  # Amber
        "#F44336",  # Red
        "#9C27B0",  # Purple
    ]

    plt.figure(figsize=(12, 6))
    ax = plt.gca()

    plot_colors = colors if colors is not None else default_colors[: len(categories)]
    bars = plt.bar(categories, values, color=plot_colors)

    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{int(height)}%",
            ha="center",
            va="bottom",
        )

    # Customize the chart
    plt.ylim(0, 100)  # Set y-axis from 0 to 100 for percentages
    plt.ylabel("Completion (%)")

    # Rotate x-axis labels for better readability if needed
    plt.xticks(rotation=45, ha="right")

    if title:
        plt.title(title)

    plt.tight_layout()

    # Save to buffer
    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format="png", dpi=300, bbox_inches="tight")
    chart_buffer.seek(0)
    plt.close()

    return chart_buffer


def plot_category_radar(category_scores, max_score=100, colors=None, title=None):
    """
    Create a radar/spider chart showing scores per category

    Args:
        category_scores (dict): Dictionary containing category scores from aggregate_category_scores()
        max_score (float): Maximum possible score value (default: 100)
        colors (list, optional): Custom color palette
        title (str, optional): Chart title

    Returns:
        io.BytesIO: Buffer containing the radar chart image
    """
    plt.close("all")

    # Extract data
    categories = [data["name"] for data in category_scores.values()]
    scores = [data["average_score"] for data in category_scores.values()]

    # Number of categories
    N = len(categories)

    default_colors = [
        "#2196F3",  # Blue
        "#4CAF50",  # Green
        "#FFC107",  # Amber
        "#F44336",  # Red
        "#9C27B0",  # Purple
    ]

    # Compute angle for each axis
    angles = [n / float(N) * 2 * np.pi for n in range(N)]

    # Close the plot by appending the first value and angle
    values = scores + scores[:1]
    angles = angles + [angles[0]]

    # Create the plot
    plt.figure(figsize=(12, 12))
    ax = plt.subplot(111, polar=True)

    plot_colors = colors if colors is not None else default_colors[: len(categories)]

    # Plot the scores
    ax.plot(angles, values, "o-", linewidth=2, color=plot_colors[0])
    ax.fill(angles, values, alpha=0.25, color=plot_colors[0])

    # Fix axis to go in the right order and start at 12 o'clock
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Draw axis lines for each angle and label
    plt.xticks(angles[:-1], categories)

    # Set y-axis limits based on provided max_score with 10% padding
    ax.set_ylim(0, max_score * 1.1)

    if title:
        plt.title(title)

    plt.tight_layout()

    # Save to buffer
    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format="png", dpi=300, bbox_inches="tight")
    chart_buffer.seek(0)
    plt.close()

    return chart_buffer


def plot_spider_chart(data, colors=None, title=None):
    """
    Create a spider/radar chart from the input data

    Args:
        data (list): List of dictionaries with 'category' and 'value' keys
        colors (list, optional): Custom color palette
        title (str, optional): Chart title

    Returns:
        io.BytesIO: Buffer containing the spider chart image
    """
    plt.close("all")

    categories = [item["category"] for item in data]
    values = [item["value"] for item in data]

    N = len(categories)

    default_colors = [
        "#2196F3",  # Blue
        "#4CAF50",  # Green
        "#FFC107",  # Amber
        "#F44336",  # Red
        "#9C27B0",  # Purple
    ]

    # Compute angle for each axis
    angles = [n / float(N) * 2 * np.pi for n in range(N)]

    # Close the plot by appending the first value and angle
    values += values[:1]
    angles += angles[:1]

    # Create the plot
    plt.figure(figsize=(12, 12))
    ax = plt.subplot(111, polar=True)

    plot_colors = colors if colors is not None else default_colors[: len(categories)]

    ax.plot(angles, values, "o-", linewidth=2, color=plot_colors[0])
    ax.fill(angles, values, alpha=0.25, color=plot_colors[0])

    # Fix axis to go in the right order and start at 12 o'clock
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Draw axis lines for each angle and label
    plt.xticks(angles[:-1], categories)

    # Set y-axis limits (optional, adjust as needed)
    ax.set_ylim(0, max(values) * 1.1)

    plt.tight_layout()
    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format="png", dpi=300, bbox_inches="tight")
    chart_buffer.seek(0)
    plt.close()

    return chart_buffer


def calculate_depths(framework):
    depth_map = dict()
    req_nodes = RequirementNode.objects.filter(framework=framework)
    # pass 1 for top levels
    for rn in req_nodes:
        depth_map[rn.urn] = 1 if rn.parent_urn is None else None
    # pass 2+ for children levels
    changed = True
    while changed:
        changed = False
        for rn in req_nodes:
            if (
                depth_map[rn.urn] is None
                and rn.parent_urn in depth_map
                and depth_map[rn.parent_urn] is not None
            ):
                depth_map[rn.urn] = depth_map[rn.parent_urn] + 1
                changed = True
    return depth_map


def _answer_rows(ra):
    """Questions and the respondent's answers, resolved the way the zip index does.

    Mirrors `get_answers` in core_extras so the PDF and `audit_report.html` agree:
    a `urn:` value is a choice reference and renders as the choice's label.
    """
    from core.utils import build_answers_dict, visible_questions

    answers = build_answers_dict(ra.answers.all())
    # `visible_questions` drops questions hidden by an unsatisfied `depends_on`,
    # so a conditional question that does not apply is not listed as unanswered.
    questions = visible_questions(ra.requirement.get_questions_translated, answers)
    if not questions:
        return []

    def resolve(question, value):
        if value is None or value == "":
            return None
        if isinstance(value, list):
            resolved = [resolve(question, item) for item in value]
            return ", ".join(item for item in resolved if item) or None
        if not str(value).startswith("urn:"):
            return str(value)
        for choice in question.get("choices", []):
            if choice["urn"] == value:
                return choice["value"]
        return None

    rows = []
    for urn, question in questions.items():
        rows.append(
            {
                "question": question.get("text", "-"),
                "answer": resolve(question, answers.get(urn)) or "-",
            }
        )
    return rows


# Status ordering and fills for the action plan, keyed on the raw enum so the
# colour never depends on a localised label (house style, §9b).
_ACTION_PLAN_STATUS_FILLS = {
    "to_do": "#fff8f0",
    "in_progress": "#e8e4f0",
    "on_hold": "#fdf3d3",
    "active": "#e3f4f2",
    "deprecated": "#ffe8d6",
    "--": "#f1f5f9",
}


def action_plan_context(assessment, controls, lang="en", linked=None):
    """Payload for the action plan, grouped by status and sorted by ETA.

    `assessment` is whatever the controls hang off — a compliance assessment or a
    risk assessment; the template renders whichever subject it is given, so one
    document serves both. `linked` maps a control id to the requirement or
    scenario labels shown in the last column.

    Deliberately narrow: an A4 page cannot carry nine columns legibly, so this
    keeps what an action plan is actually read for — what, who, by when, against
    which item — and drops CSF function, effort, cost and expiry date.
    """
    linked = linked or {}
    states = dict(AppliedControl.Status.choices)
    buckets = {key: [] for key in _ACTION_PLAN_STATUS_FILLS}

    for control in controls:
        buckets.setdefault(control.status or "--", []).append(
            {
                "name": control.name or "-",
                "description": control.description or "-",
                "category": control.get_category_display() or "-",
                "owner": ", ".join(str(actor) for actor in control.owner.all()) or "-",
                "eta": _date_str(control.eta),
                "linked": linked.get(control.id, []),
            }
        )

    groups = [
        {
            "status_key": key,
            "status": str(states.get(key, "")) if key != "--" else "",
            "fill": _ACTION_PLAN_STATUS_FILLS.get(key, "#f1f5f9"),
            "controls": rows,
        }
        for key, rows in buckets.items()
        if rows
    ]

    perimeter = getattr(assessment, "perimeter", None)
    framework = getattr(assessment, "framework", None)
    return {
        "subject": {
            "domain": str(assessment.folder) if assessment.folder else "-",
            "perimeter": str(perimeter.name) if perimeter else "-",
            "name": assessment.name or "-",
            "version": str(assessment.version or "-"),
            "framework": str(framework) if framework else "",
        },
        "id": str(assessment.id),
        "date": now().strftime("%d/%m/%Y"),
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "groups": groups,
        "total": sum(len(g["controls"]) for g in groups),
    }


# Severity is an IntegerChoices whose labels are lowercase keys ("critical"),
# so the locale template maps them; the raw key also drives the badge colour.
_SEVERITY_ORDER = [4, 3, 2, 1, 0, -1]
_SEVERITY_KEYS = {
    4: "critical",
    3: "high",
    2: "medium",
    1: "low",
    0: "info",
    -1: "undefined",
}

_CLOSED_FINDING_STATUSES = (
    "dismissed",
    "mitigated",
    "resolved",
    "closed",
    "deprecated",
)


def findings_assessment_context(assessment, findings, lang="en"):
    """Payload for the findings report.

    Findings are grouped by severity, worst first: a reader triages by severity,
    and one block per page (what the HTML template did) turns fifty findings into
    fifty pages.
    """
    metrics = assessment.get_findings_metrics()
    severity_counts = metrics.get("severity_distribution", {})

    rows = []
    for finding in findings:
        rows.append(
            {
                "ref_id": finding.ref_id or "-",
                "name": finding.name or "-",
                "severity_key": _SEVERITY_KEYS.get(finding.severity, "undefined"),
                "status_key": finding.status or "--",
                "description": finding.description or "",
                "observation": getattr(finding, "observation", "") or "",
                "owners": ", ".join(str(a) for a in finding.owner.all()) or "-",
                "eta": _date_str(finding.eta),
                "due_date": _date_str(finding.due_date),
                "controls": [c.name for c in finding.applied_controls.all()],
                "evidences": [e.name for e in finding.evidences.all()],
                "labels": [str(label) for label in finding.filtering_labels.all()],
            }
        )

    groups = [
        {
            "severity_key": _SEVERITY_KEYS[value],
            "findings": [
                row for row in rows if row["severity_key"] == _SEVERITY_KEYS[value]
            ],
        }
        for value in _SEVERITY_ORDER
    ]
    groups = [group for group in groups if group["findings"]]

    closed = sum(
        count
        for status, count in metrics.get("status_distribution", {}).items()
        if status in _CLOSED_FINDING_STATUSES
    )
    total = metrics.get("total_count", 0)

    return {
        "assessment": {
            "name": assessment.name or "-",
            "ref_id": assessment.ref_id or "-",
            "description": assessment.description or "",
            "category": assessment.get_category_display() or "-",
            "status": assessment.get_status_display() or "-",
            "folder": str(assessment.folder) if assessment.folder else "-",
            "observation": getattr(assessment, "observation", "") or "",
            "authors": ", ".join(str(a) for a in assessment.authors.all()) or "-",
            "reviewers": ", ".join(str(r) for r in assessment.reviewers.all()) or "-",
        },
        "id": str(assessment.id),
        "date": now().strftime("%d/%m/%Y"),
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "metrics": {
            "total": total,
            "closed": closed,
            "open": total - closed,
            "unresolved_important": metrics.get("unresolved_important_count", 0),
        },
        "severity_rows": [
            {
                "key": _SEVERITY_KEYS[value],
                "count": severity_counts.get(_SEVERITY_KEYS[value], 0),
            }
            for value in _SEVERITY_ORDER
        ],
        "groups": groups,
    }


def _timestamp_str(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "-"


def incident_context(incident, timeline_entries, lang="en"):
    """Payload for the incident report.

    The timeline is the substance: entries in chronological order, each keyed by
    its raw `entry_type` so the locale template supplies the label and the accent
    colour without depending on a translated string.
    """
    entries = []
    for entry in timeline_entries:
        entries.append(
            {
                "entry": entry.entry or "-",
                "type_key": entry.entry_type or "observation",
                "timestamp": _timestamp_str(entry.timestamp),
                "author": str(entry.author) if entry.author else "",
                "observation": entry.observation or "",
                "evidences": [e.name for e in entry.evidences.all()],
            }
        )

    counts = {}
    for entry in entries:
        counts[entry["type_key"]] = counts.get(entry["type_key"], 0) + 1

    return {
        "incident": {
            "ref_id": incident.ref_id or "",
            "name": incident.name or "-",
            "severity": incident.get_severity_display() or "-",
            "status": incident.get_status_display() or "-",
            "detection": incident.get_detection_display() or "-",
            "folder": str(incident.folder) if incident.folder else "-",
            "description": incident.description or "",
            "resolution": getattr(incident, "resolution", "") or "",
            "is_bcp_activated": bool(incident.is_bcp_activated),
            "owners": ", ".join(str(o) for o in incident.owners.all()) or "-",
            "qualifications": [q.name for q in incident.qualifications.all()],
            "entities": [e.name for e in incident.entities.all()],
            "assets": [a.name for a in incident.assets.all()],
            "threats": [t.name for t in incident.threats.all()],
            "reported_at": _timestamp_str(incident.reported_at),
            "occurred_at": _timestamp_str(incident.occurred_at),
            "resolved_at": _timestamp_str(incident.resolved_at),
        },
        "id": str(incident.id),
        "date": now().strftime("%d/%m/%Y"),
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "counts": {
            "total": len(entries),
            "detection": counts.get("detection", 0),
            "mitigation": counts.get("mitigation", 0),
        },
        "timeline": entries,
    }


def gen_audit_context(id, tree, lang, assessments=None, charts=True):
    def count_category_results(data):
        def recursive_result_count(node_data):
            # Initialize result counts for this node
            result_counts = {}

            # Check if the current node is assessable
            if node_data.get("assessable", False):
                result = node_data.get("result", "unknown")
                result_counts[result] = 1

            # Recursively process children
            for child_id, child_data in node_data.get("children", {}).items():
                child_results = recursive_result_count(child_data)

                # Merge child results into current results
                for result, count in child_results.items():
                    result_counts[result] = result_counts.get(result, 0) + count

            return result_counts

        # Dictionary to store result counts for top-level nodes
        category_result_counts = {}

        # Process only top-level nodes
        for node_id, node_data in data.items():
            if node_data.get("parent_urn") is None:
                category_result_counts[node_data["urn"]] = recursive_result_count(
                    node_data
                )

        return category_result_counts

    def aggregate_category_scores(data):
        """
        Aggregate scores per category from the tree structure, using existing score values.
        Each scoreable item has a standard max_score of 100.

        Args:
            data (dict): Tree structure containing assessment data with score values

        Returns:
            dict: Dictionary with category URNs as keys and score information as values
        """

        def recursive_score_calculation(node_data):
            # Initialize score tracking for this node
            scores = {
                "total_score": 0,  # Sum of all scores
                "item_count": 0,  # Number of scoreable items
                "scored_count": 0,  # Number of items that have been scored
            }

            # Check if the current node is scoreable
            if node_data.get("is_scored", False):
                scores["item_count"] = 1

                if node_data.get("score") is not None:
                    scores["total_score"] = node_data["score"]
                    scores["scored_count"] = 1

            # Recursively process children
            for child_id, child_data in node_data.get("children", {}).items():
                child_scores = recursive_score_calculation(child_data)

                # Aggregate child scores
                scores["total_score"] += child_scores["total_score"]
                scores["item_count"] += child_scores["item_count"]
                scores["scored_count"] += child_scores["scored_count"]

            return scores

        # Dictionary to store category scores
        category_scores = {}
        for node_id, node_data in data.items():
            # this acts only at the top level nodes since it's not crawling the children.
            # TODO: we need a new param to control on which depth we want to report now that we have the depth map
            scores = recursive_score_calculation(node_data)

            # Calculate average score for the category
            average_score = 0
            if scores["scored_count"] > 0:
                average_score = scores["total_score"] / scores["scored_count"]

            category_scores[node_data["urn"]] = {
                "name": node_data["node_content"].split(":")[0],
                "total_score": scores["total_score"],
                "item_count": scores["item_count"],
                "scored_count": scores["scored_count"],
                "average_score": round(average_score, 1),
            }

        return category_scores

    def _build_safe_audit_context(audit):
        return {
            "id": str(audit.id),
            "name": audit.name or "-",
            "description": audit.description or "-",
            "ref_id": audit.ref_id or "-",
            "framework": {
                "name": audit.framework.name or "-",
                "description": audit.framework.description or "-",
                "ref_id": audit.framework.ref_id or "-",
                "min_score": audit.min_score
                if audit.min_score is not None
                else audit.framework.min_score,
                "max_score": audit.max_score
                if audit.max_score is not None
                else audit.framework.max_score,
            },
            "selected_implementation_groups": [
                str(x) for x in audit.get_selected_implementation_groups()
            ],
        }

    audit = ComplianceAssessment.objects.get(id=id)

    context = dict()

    authors = ", ".join(
        dict.fromkeys(email for a in audit.authors.all() for email in a.get_emails())
    )
    reviewers = ", ".join(
        dict.fromkeys(email for r in audit.reviewers.all() for email in r.get_emails())
    )

    spider_data = list()
    result_counts = count_category_results(tree)

    agg_drifts = list()

    # Calculate category scores
    category_scores = aggregate_category_scores(tree)

    max_score = 100  # default
    for node in tree.values():
        if node.get("max_score") is not None:
            max_score = node["max_score"]
            break
    print(category_scores)

    for key, content in tree.items():
        total = sum(result_counts[content["urn"]].values())
        ok_items = result_counts[content["urn"]].get("compliant", 0) + result_counts[
            content["urn"]
        ].get("not_applicable", 0)
        ok_perc = ceil(ok_items / total * 100) if total > 0 else 0
        not_ok_count = total - ok_items
        name = content["node_content"].split(":")[0]
        spider_data.append({"category": name, "value": ok_perc})
        agg_drifts.append({"name": name, "drift_count": not_ok_count})

    aggregated = {
        "compliant": 0,
        "non_compliant": 0,
        "not_applicable": 0,
        "not_assessed": 0,
        "partially_compliant": 0,
    }

    for node in result_counts.values():
        for status, count in node.items():
            if status in aggregated:
                aggregated[status] += count

    total = sum([v for v in aggregated.values()])
    if total == 0:
        print("Error:: No requirments found, something is wrong. aborting ..")
        # NOTICE: We aren't aborting here, lead to a division by zero in the plot_donut function
    aggregated["total"] = total

    # temporary hack since the gettext_lazy wasn't consistent
    i18n_dict = {
        "en": {
            "compliant": "Compliant",
            "partially_compliant": "Partially compliant",
            "non_compliant": "Non compliant",
            "not_applicable": "Not applicable",
            "not_assessed": "Not assessed",
            "to_do": "To do",
            "on_hold": "On hold",
            "in_progress": "In progress",
            "deprecated": "Deprecated",
            "active": "Active",
            "policy": "Policy",
            "process": "Process",
            "technical": "Technical",
            "physical": "Physical",
            "procedure": "Procedure",
            "in_review": "In review",
            "done": "Done",
            "major_nonconformity": "Major nonconformity",
            "minor_nonconformity": "Minor nonconformity",
            "observation_sensitive_point": "Observation / sensitive point",
            "opportunity_for_improvement": "Opportunity for improvement",
            "good_practice": "Good practice",
        },
        "fr": {
            "compliant": "Conformes",
            "partially_compliant": "Partiellement conformes",
            "non_compliant": "Non conformes",
            "not_applicable": "Non applicables",
            "not_assessed": "Non évalués",
            "to_do": "À faire",
            "on_hold": "En attente",
            "in_progress": "En cours",
            "deprecated": "Déprécié",
            "active": "Actif",
            "policy": "Politique",
            "process": "Processus",
            "technical": "Technique",
            "physical": "Physique",
            "procedure": "Procédure",
            "in_review": "En revue",
            "done": "Terminé",
            "major_nonconformity": "Non-conformité majeure",
            "minor_nonconformity": "Non-conformité mineure",
            "observation_sensitive_point": "Observation / point sensible",
            "opportunity_for_improvement": "Opportunité d'amélioration",
            "good_practice": "Bonne pratique",
        },
        "nl": {
            "compliant": "Compliant",
            "partially_compliant": "Gedeeltelijk compliant",
            "non_compliant": "Niet compliant",
            "not_applicable": "Niet van toepassing",
            "not_assessed": "Niet beoordeeld",
            "to_do": "Te doen",
            "on_hold": "In de wacht",
            "in_progress": "In uitvoering",
            "deprecated": "Verouderd",
            "active": "Actief",
            "policy": "Beleid",
            "process": "Proces",
            "technical": "Technisch",
            "physical": "Fysiek",
            "procedure": "Procedure",
            "in_review": "In beoordeling",
            "done": "Gedaan",
            "major_nonconformity": "Ernstige niet-naleving",
            "minor_nonconformity": "Kleine niet-naleving",
            "observation_sensitive_point": "Observatie / aandachtspunt",
            "opportunity_for_improvement": "Verbetermogelijkheid",
            "good_practice": "Goede praktijk",
        },
    }

    def safe_translate(lang: str, key: str) -> str:
        if key is None or key == "--":
            return "-"
        return i18n_dict.get(lang, i18n_dict["en"]).get(key, key)

    donut_data = [
        {
            "category": safe_translate(lang, "compliant"),
            "value": aggregated["compliant"],
        },
        {
            "category": safe_translate(lang, "partially_compliant"),
            "value": aggregated["partially_compliant"],
        },
        {
            "category": safe_translate(lang, "non_compliant"),
            "value": aggregated["non_compliant"],
        },
        {
            "category": safe_translate(lang, "not_applicable"),
            "value": aggregated["not_applicable"],
        },
        {
            "category": safe_translate(lang, "not_assessed"),
            "value": aggregated["not_assessed"],
        },
    ]

    custom_colors = ["#2196F3"]
    # Charts are ~99% of this function's cost (matplotlib at dpi=300); a caller
    # that drops them — the countersigned export does — should not pay for them.
    spider_chart_buffer = (
        plot_spider_chart(spider_data, colors=custom_colors) if charts else None
    )
    category_radar_buffer = (
        plot_category_radar(category_scores, max_score=max_score, colors=custom_colors)
        if charts
        else None
    )
    # `assessments` lets a caller pass a row-level-scoped set (see
    # `scoped_requirement_assessments`); without it every assessment is included.
    requirement_assessments_objects = (
        audit.get_requirement_assessments(include_non_assessable=True)
        if assessments is None
        else assessments
    )

    # Build flat list of requirement assessments for Word template
    requirement_assessments_list = []
    for ra in [
        ra for ra in requirement_assessments_objects if ra.requirement.assessable
    ]:
        requirement_assessments_list.append(
            {
                "ref_id": ra.requirement.ref_id or "-",
                "name": get_referential_translation(ra.requirement, "name", lang)
                or "-",
                "description": get_referential_translation(
                    ra.requirement, "description", lang
                )
                or "-",
                "status": safe_translate(lang, ra.status),
                "result": safe_translate(lang, ra.result),
                # The label is localised; the colour must key off the raw value.
                "result_key": ra.result or "",
                "extended_result": safe_translate(lang, ra.extended_result),
                "score": ra.score,
                "max_score": audit.framework.max_score if ra.is_scored else None,
                "observation": ra.observation or "-",
                "answers": _answer_rows(ra),
                "evidences": [e.name for e in ra.evidences.all()],
                "task_templates": [t.name for t in ra.task_templates.all()],
                "applied_controls": ", ".join(
                    ac.name for ac in ra.applied_controls.all()
                )
                or "-",
            }
        )

    applied_controls = AppliedControl.objects.filter(
        requirement_assessments__in=requirement_assessments_objects
    ).distinct()
    ac_total = applied_controls.count()
    status_cnt = applied_controls.values("status").annotate(count=Count("id"))
    ac_chart_data = [
        {
            "category": safe_translate(lang, item["status"]),
            "value": item["count"],
        }
        for item in status_cnt
    ]
    p1_controls = list()
    full_controls = list()
    for ac in applied_controls.filter(priority=1):
        requirements_count = (
            RequirementAssessment.objects.filter(compliance_assessment=audit)
            .filter(applied_controls=ac.id)
            .count()
        )
        print(f"[{ac.name}] {ac.category}: {type(ac.category)}")
        p1_controls.append(
            {
                "name": ac.name,
                "description": safe_translate(lang, ac.description),  # None -> "-"
                "status": safe_translate(lang, ac.status),
                "category": safe_translate(lang, ac.category),
                "coverage": requirements_count,
            }
        )

    for ac in applied_controls.all():
        requirements_count = (
            RequirementAssessment.objects.filter(compliance_assessment=audit)
            .filter(applied_controls=ac.id)
            .count()
        )
        full_controls.append(
            {
                "name": ac.name,
                "description": safe_translate(lang, ac.description),  # None -> "-"
                "prio": f"P{ac.priority}" if ac.priority else "-",
                "status": safe_translate(lang, ac.status),
                "eta": safe_translate(lang, ac.eta),  # None -> "-"
                "category": safe_translate(lang, ac.category),
                "coverage": requirements_count,
            }
        )

    custom_colors = [
        "#CCC",
        "#46D39A",
        "#E55759",
        "#392F5A",
        "#F4D06F",
        "#BFDBFE",
    ]
    hbar_buffer = (
        plot_horizontal_bar(ac_chart_data, colors=custom_colors) if charts else None
    )
    completion_bar_buffer = (
        plot_completion_bar(spider_data, colors=custom_colors) if charts else None
    )
    donut_buffer = plot_donut(donut_data) if charts else None
    IGs = ", ".join([str(x) for x in audit.get_selected_implementation_groups()])
    context = {
        "audit": _build_safe_audit_context(audit),
        "date": now().strftime("%d/%m/%Y"),
        # Traceability on the cover: which render, of which audit.
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "contributors": f"{authors}\n{reviewers}",
        "req": aggregated,
        "compliance_donut": donut_buffer,
        "completion_bar": completion_bar_buffer,
        "compliance_radar": spider_chart_buffer,
        "drifts_per_domain": agg_drifts,
        "chart_controls": hbar_buffer,
        "p1_controls": p1_controls,
        "full_controls": full_controls,
        "ac_count": ac_total,
        "igs": IGs,
        "category_scores": category_scores,
        "category_radar": category_radar_buffer,
        "requirement_assessments": requirement_assessments_list,
        "ra_count": len(requirement_assessments_list),
    }

    return context


AUDIT_CHART_KEYS = (
    "compliance_donut",
    "completion_bar",
    "compliance_radar",
    "chart_controls",
    "category_radar",
)


def inline_charts_for_docx(context, doc, width=Cm(15)):
    """Wrap the chart buffers of `gen_audit_context` for docxtpl.

    The context stays engine-agnostic so other renderers consume the same
    buffers; the rewind lets one assembly feed several renders.
    """
    wrapped = dict(context)
    for key in AUDIT_CHART_KEYS:
        buffer = wrapped.get(key)
        if buffer is None:
            continue
        buffer.seek(0)
        wrapped[key] = InlineImage(doc, buffer, width=width)
    return wrapped


# Requirement-assessment fields governed by the audit's `field_visibility`;
# `max_score` is not itself governed but is meaningless once `score` is dropped.
_REDACTABLE_RA_FIELDS = (
    "answers",
    "evidences",
    "task_templates",
    "status",
    "result",
    "extended_result",
    "score",
    "observation",
    "applied_controls",
)

# Data derived from a governed field. Redacting the field does not redact an
# aggregate or an image computed from it, so they have to be dropped together —
# otherwise the PDF discloses as a total or a picture what the rows withheld.
_FIELD_DERIVED_CHARTS = {
    "score": ("category_radar",),
    "result": ("compliance_donut", "compliance_radar", "completion_bar"),
}
_FIELD_DERIVED_KEYS = {
    "score": ("category_scores",),
    "result": ("req", "drifts_per_domain"),
    "applied_controls": ("p1_controls", "full_controls", "ac_count"),
}

# Report profiles. `sections` drives layout; `drops` drives the payload. Both are
# needed: a template flag alone would leave excluded values in the JSON, and the
# template is overridable, so anything a reader must not see is removed here.
REPORT_PROFILES = {
    "full": {
        # Each profile has its own self-contained template per locale, so
        # customising one cannot affect the others.
        "template": "audit_report",
        # The reader's own role still applies on top; this is the ceiling.
        "role": "auditor",
        "discloses": (),
        "sections": (
            "summary",
            "charts",
            "scope",
            "drifts",
            "categories",
            "controls",
            "requirements",
            "answers",
            "commitments",
            "tasks",
        ),
    },
    "attestation": {
        "template": "attestation",
        "role": "respondent",
        # The questionnaire deliberately withholds the auditor's verdict while the
        # respondent is answering (THIRD_PARTY_VISIBILITY marks `result` auditor-only).
        # The attestation exists to state that verdict for agreement, so it is
        # disclosed back — explicitly and in one place, rather than by a parallel
        # redaction list that could drift from the audit's own configuration.
        "discloses": ("result",),
        # A record of what was recorded, not an analysis: no aggregate counts,
        # percentages, drift tallies or charts — the same content selection as the
        # zip's `audit_report.html`, which walks the requirements and prints what
        # is on them.
        "sections": (
            "scope",
            "requirements",
            "answers",
            "commitments",
            "tasks",
            "signatures",
        ),
    },
}

# Template chrome, keyed the way `frontend/messages/*.json` keys it so this can be
# swapped for the shared catalog without touching the template. English literals
# stand in until then — see docs/backend_i18n_catalog_shaping.md.


# Commitment states are row data, so they are localised here rather than in the
# per-locale template. Same category as `i18n_dict` above, retired by the same
# catalog work; a new locale template needs an entry here too.
_STATE_LABELS = {
    "en": {
        Commitment.State.UNDEFINED: "Undefined",
        Commitment.State.IN_NEGOTIATION: "In negotiation",
        Commitment.State.COMMITTED: "Committed",
        Commitment.State.DECLINED: "Declined",
        Commitment.State.FULFILLED: "Fulfilled",
    },
    "fr": {
        Commitment.State.UNDEFINED: "Non défini",
        Commitment.State.IN_NEGOTIATION: "En négociation",
        Commitment.State.COMMITTED: "Engagé",
        Commitment.State.DECLINED: "Refusé",
        Commitment.State.FULFILLED: "Réalisé",
    },
}


def _date_str(value):
    return value.isoformat() if value else "-"


def _commitment_row(obj, lang, kind):
    state = obj.commitment_state
    states = _STATE_LABELS.get(lang, _STATE_LABELS["en"])
    return {
        "kind": kind,
        "name": obj.name or "-",
        "state": states.get(state, state),
        "committed_eta": _date_str(obj.committed_eta),
        "current_date": _date_str(obj.commitment_date),
        "has_slipped": obj.commitment_has_slipped,
        "notes": obj.commitment_notes or "",
    }


def audit_undertakings(audit, lang="en"):
    """Applied controls and tasks attached to the audit, with commitment state.

    Returns ``(commitments, tasks)``: the first is everything carrying a live
    commitment — the promises a counterparty would countersign — the second is the
    task list regardless of commitment.
    """
    ras = audit.get_requirement_assessments(include_non_assessable=False)
    controls = (
        AppliedControl.objects.filter(requirement_assessments__in=ras)
        .distinct()
        .prefetch_related("commitments")
        .order_by("eta")
    )
    task_templates = (
        TaskTemplate.objects.filter(requirement_assessments__in=ras)
        .distinct()
        .prefetch_related("commitments")
        .order_by("name")
    )

    tasks = [_commitment_row(t, lang, "task") for t in task_templates]
    commitments = [
        _commitment_row(obj, lang, kind)
        for obj, kind in (
            [(c, "control") for c in controls] + [(t, "task") for t in task_templates]
        )
        if obj.commitment_state != Commitment.State.UNDEFINED
    ]
    return commitments, tasks


def counterparty_context(audit):
    """The assessed entity behind this audit, when it is a third-party questionnaire.

    An audit reached through an entity assessment identifies a counterparty; a plain
    internal audit does not, and the cover simply omits the block.
    """
    entity_assessment = audit.entityassessment_set.select_related("entity").first()
    if entity_assessment is None or entity_assessment.entity is None:
        return None
    entity = entity_assessment.entity
    identifiers = entity.legal_identifiers or {}
    return {
        "entity": entity.name,
        "ref_id": entity.ref_id or "",
        "address": entity.address or "",
        "legal_identifiers": [
            {"label": key, "value": value}
            for key, value in identifiers.items()
            if value
        ],
        "expiry_date": _date_str(entity_assessment.expiry_date),
        "assessment": entity_assessment.name,
    }


def audit_context_for_typst(context, audit, role="auditor", lang="en", profile="full"):
    """Split `gen_audit_context` output into a JSON payload and chart images.

    Fields hidden from `role` are dropped here rather than in the template:
    templates are overridable, so a guard living in one could be removed by an
    override and leak auditor-only values to a respondent.
    """
    payload = {
        key: value for key, value in context.items() if key not in AUDIT_CHART_KEYS
    }

    spec = REPORT_PROFILES.get(profile, REPORT_PROFILES["full"])
    # Least privilege of the two: an auditor exporting the external document gets
    # the respondent's field set, and a respondent never escalates by asking for
    # the internal one.
    effective_role = "respondent" if "respondent" in (role, spec["role"]) else "auditor"
    hidden = {
        field
        for field in _REDACTABLE_RA_FIELDS
        if not is_field_visible_to(audit, field, effective_role)
    }
    # Disclose only what the auditor themselves can see: a field the *framework*
    # hides from everyone (a maturity questionnaire that does not use `result`, say)
    # is a stronger statement than the third-party base's auditor-only default, and
    # the external copy must never show more than the internal one.
    hidden -= {
        field
        for field in spec["discloses"]
        if is_field_visible_to(audit, field, "auditor")
    }
    if hidden:
        payload["requirement_assessments"] = [
            {
                key: value
                for key, value in ra.items()
                if key not in hidden
                and not (key == "max_score" and "score" in hidden)
                and not (key == "result_key" and "result" in hidden)
            }
            for ra in payload.get("requirement_assessments", [])
        ]
    payload["hidden_fields"] = sorted(hidden)

    images = {}
    for key in AUDIT_CHART_KEYS:
        buffer = context.get(key)
        if buffer is None:
            continue
        buffer.seek(0)
        images[f"{key}.png"] = buffer.read()
    if "categories" not in spec["sections"]:
        payload.pop("category_scores", None)

    for field in hidden:
        for key in _FIELD_DERIVED_KEYS.get(field, ()):
            payload.pop(key, None)
        for name in _FIELD_DERIVED_CHARTS.get(field, ()):
            images.pop(f"{name}.png", None)

    if {"commitments", "tasks"} & set(spec["sections"]):
        commitments, tasks = audit_undertakings(audit, lang)
        payload["commitments"] = commitments
        payload["tasks"] = tasks

    if "charts" not in spec["sections"]:
        images = {}

    payload["counterparty"] = counterparty_context(audit)
    payload["profile"] = profile
    payload["sections"] = list(spec["sections"])
    payload["charts"] = sorted(images)
    return payload, images
