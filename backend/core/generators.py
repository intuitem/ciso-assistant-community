import io
import matplotlib
from numpy import char
from .models import *
from math import ceil
from docxtpl import InlineImage
from docx.shared import Cm
import matplotlib.pyplot as plt
import numpy as np

# from icecream import ic

from django.db.models import Count

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


def gen_audit_context(id, doc, tree):
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

    context = dict()
    audit = ComplianceAssessment.objects.get(id=id)

    authors = ", ".join([a.email for a in audit.authors.all()])
    reviewers = ", ".join([a.email for a in audit.reviewers.all()])

    spider_data = list()
    result_counts = count_category_results(tree)

    agg_drifts = list()

    for key, content in tree.items():
        total = sum(result_counts[content["urn"]].values())
        ok_items = result_counts[content["urn"]].get("compliant", 0) + result_counts[
            content["urn"]
        ].get("not_applicable", 0)
        ok_perc = ceil(ok_items / total * 100) if total > 0 else 0
        not_ok_count = total - ok_items
        spider_data.append({"category": content["node_content"], "value": ok_perc})
        agg_drifts.append(
            {"name": content["node_content"], "drift_count": not_ok_count}
        )

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

    aggregated["total"] = total

    donut_data = [
        {"category": "Conforme", "value": aggregated["compliant"]},
        {
            "category": "Partiellement conforme",
            "value": aggregated["partially_compliant"],
        },
        {"category": "Non conforme", "value": aggregated["non_compliant"]},
        {"category": "Non applicable", "value": aggregated["not_applicable"]},
        {"category": "Non évalué", "value": aggregated["not_assessed"]},
    ]

    custom_colors = ["#2196F3"]
    spider_chart_buffer = plot_spider_chart(
        spider_data,
        colors=custom_colors,
    )

    requirement_assessments_objects = audit.get_requirement_assessments(
        include_non_assessable=True
    )
    applied_controls = AppliedControl.objects.filter(
        requirement_assessments__in=requirement_assessments_objects
    ).distinct()
    ac_total = applied_controls.count()
    status_cnt = applied_controls.values("status").annotate(count=Count("id"))
    ac_chart_data = [
        {"category": item["status"], "value": item["count"]} for item in status_cnt
    ]
    p1_controls = list()
    for ac in applied_controls.filter(priority=1):
        requirements_count = (
            RequirementAssessment.objects.filter(compliance_assessment=audit)
            .filter(applied_controls=ac.id)
            .count()
        )
        p1_controls.append(
            {
                "name": ac.name,
                "description": ac.description,
                "status": ac.status,
                "category": ac.category,
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
    hbar_buffer = plot_horizontal_bar(ac_chart_data, colors=custom_colors)

    res_donut = InlineImage(doc, plot_donut(donut_data), width=Cm(15))
    chart_spider = InlineImage(doc, spider_chart_buffer, width=Cm(15))
    ac_chart = InlineImage(doc, hbar_buffer, width=Cm(15))
    IGs = ", ".join(audit.get_selected_implementation_groups())
    context = {
        "audit": audit,
        "date": now().strftime("%d/%m/%Y"),
        "contributors": f"{authors}\n{reviewers}",
        "req": aggregated,
        "compliance_donut": res_donut,
        "compliance_radar": chart_spider,
        "drifts_per_domain": agg_drifts,
        "chart_controls": ac_chart,
        "p1_controls": p1_controls,
        "ac_count": ac_total,
        "igs": IGs,
    }

    return context
