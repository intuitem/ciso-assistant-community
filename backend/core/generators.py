import io
import matplotlib
from numpy import char
from .models import *
from math import ceil
from docxtpl import InlineImage
from docx.shared import Cm
import matplotlib.pyplot as plt

matplotlib.use("Agg")


def plot_bar(data):
    plt.figure(figsize=(10, 6))
    plt.bar(
        [item["category"] for item in data],
        [item["value"] for item in data],
    )
    plt.tight_layout()
    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format="png")
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

    # Use provided colors or fall back to default
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


def gen_audit_context(id, doc):
    context = dict()
    audit = ComplianceAssessment.objects.get(id=id)

    authors = ", ".join([a.email for a in audit.authors.all()])
    reviewers = ", ".join([a.email for a in audit.reviewers.all()])

    cnt_per_result = audit.get_requirements_result_count()
    total = sum([res[0] for res in cnt_per_result])

    donut_data = [
        {"category": "Conforme", "value": cnt_per_result[3][0]},
        {"category": "Partiellement conforme", "value": cnt_per_result[1][0]},
        {"category": "Non conforme", "value": cnt_per_result[2][0]},
        {"category": "Non applicable", "value": cnt_per_result[4][0]},
        {"category": "Non évalué", "value": cnt_per_result[0][0]},
    ]

    res_donut = InlineImage(doc, plot_donut(donut_data), width=Cm(15))

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
        "chart_progress_donut": res_donut,
    }

    return context
