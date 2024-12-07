import io
import matplotlib
from numpy import char
from .models import *
from math import ceil
from docxtpl import InlineImage
from docx.shared import Cm
import matplotlib.pyplot as plt
import numpy as np
from icecream import ic

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
    plt.figure(figsize=(10, 10))
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
        # Dictionary to store result counts for top-level nodes
        category_result_counts = {}

        for node_id, node_data in data.items():
            # Check if this is a top-level node (no parent URN)
            if node_data.get("parent_urn") is None:
                # Initialize result count for this category
                category_result_counts[node_data["urn"]] = {}

                # Aggregate results from assessable children
                for child_id, child_data in node_data.get("children", {}).items():
                    if child_data.get("assessable", False):
                        result = child_data.get("result", "unknown")
                        category_result_counts[node_data["urn"]][result] = (
                            category_result_counts[node_data["urn"]].get(result, 0) + 1
                        )

        return category_result_counts

    context = dict()
    audit = ComplianceAssessment.objects.get(id=id)

    authors = ", ".join([a.email for a in audit.authors.all()])
    reviewers = ", ".join([a.email for a in audit.reviewers.all()])

    cnt_per_result = audit.get_requirements_result_count()
    total = sum([res[0] for res in cnt_per_result])

    spider_data = list()
    result_counts = count_category_results(tree)
    ic(result_counts)
    for key, content in tree.items():
        ic(content["node_content"])
        total = sum(result_counts[content["urn"]].values())
        ok_items = result_counts[content["urn"]].get("compliant", 0) + result_counts[
            content["urn"]
        ].get("not_applicable", 0)
        ok_perc = ceil(ok_items / total * 100) if total > 0 else 0
        spider_data.append({"category": content["node_content"], "value": ok_perc})

    donut_data = [
        {"category": "Conforme", "value": cnt_per_result[3][0]},
        {"category": "Partiellement conforme", "value": cnt_per_result[1][0]},
        {"category": "Non conforme", "value": cnt_per_result[2][0]},
        {"category": "Non applicable", "value": cnt_per_result[4][0]},
        {"category": "Non évalué", "value": cnt_per_result[0][0]},
    ]

    custom_colors = ["#2196F3"]
    spider_chart_buffer = plot_spider_chart(
        spider_data,
        colors=custom_colors,
    )
    horizontal_bar_data = [
        {"category": "--", "value": 85},
        {"category": "A faire", "value": 70},
        {"category": "En cours", "value": 90},
        {"category": "Bloquées", "value": 90},
        {"category": "Actives", "value": 75},
        {"category": "Obsolètes", "value": 80},
    ]

    # Custom color (optional)
    custom_colors = [
        "#1976D2",  # Deep Blue
        "#388E3C",  # Green
        "#FFA000",  # Amber
        "#D32F2F",  # Red
        "#7B1FA2",  # Purple
    ]

    horizontal_bar_buffer = plot_horizontal_bar(
        horizontal_bar_data, colors=custom_colors
    )

    # Create InlineImage for the document
    res_donut = InlineImage(doc, plot_donut(donut_data), width=Cm(15))
    chart_spider = InlineImage(doc, spider_chart_buffer, width=Cm(15))
    chart_horizontal_bar = InlineImage(doc, horizontal_bar_buffer, width=Cm(15))

    context = {
        "audit": audit,
        "date": now().strftime("%d/%m/%Y"),
        "contributors": f"{authors}\n{reviewers}",
        "req": {
            "total": total,
            "compliant": cnt_per_result[3][0],
            "part_compliant": cnt_per_result[1][0],
            "non_compliant": cnt_per_result[2][0],
            "not_applicable": cnt_per_result[4][0],
            "not_assessed": cnt_per_result[0][0],
        },
        "compliance_donut": res_donut,
        "compliance_radar": chart_spider,
        "chart_controls": chart_horizontal_bar,
        "p1_controls": [
            {"name": "sample", "type": "govern"},
            {"name": "another", "type": "user"},
        ],
    }

    return context
