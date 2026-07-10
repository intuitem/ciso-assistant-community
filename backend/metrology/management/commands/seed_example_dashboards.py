"""
Management command to seed example analytics dashboards.

Creates two opinionated dashboards (Operations Overview and Compliance Snapshot)
populated with widgets driven by the builtin-metrics registry on the root
folder (i.e. whole-organization scope). Idempotent: re-running updates the
widget set in place rather than duplicating dashboards.

Seed-managed dashboards are identified by a stable `ref_id` (not by name),
so a user-created dashboard with the same name will never be touched. Use
--force to overwrite a dashboard that the seed owns but a user has edited.

Usage:
    python manage.py seed_example_dashboards
    python manage.py seed_example_dashboards --force
"""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from iam.models import Folder
from metrology.models import Dashboard, DashboardWidget


# Two seed dashboards. Each widget targets the root folder ("Global" scope)
# so the metrics reflect the whole organization.
# `ref_id` is the stable seed identifier — never reuse one across seeds.
SEEDS = [
    {
        "ref_id": "seed:operations-overview",
        "name": "Operations Overview",
        "description": "Incidents, controls, exceptions, tasks at a glance.",
        "widgets": [
            {
                "title": "Total Incidents",
                "metric_key": "total_incidents",
                "chart_type": DashboardWidget.ChartType.KPI_CARD,
                "position_x": 0,
                "position_y": 0,
                "width": 3,
                "height": 1,
            },
            {
                "title": "Open Security Exceptions",
                "metric_key": "total_security_exceptions",
                "chart_type": DashboardWidget.ChartType.KPI_CARD,
                "position_x": 3,
                "position_y": 0,
                "width": 3,
                "height": 1,
            },
            {
                "title": "Risk Acceptances",
                "metric_key": "total_risk_acceptances",
                "chart_type": DashboardWidget.ChartType.KPI_CARD,
                "position_x": 6,
                "position_y": 0,
                "width": 3,
                "height": 1,
            },
            {
                "title": "Total Controls",
                "metric_key": "total_controls",
                "chart_type": DashboardWidget.ChartType.KPI_CARD,
                "position_x": 9,
                "position_y": 0,
                "width": 3,
                "height": 1,
            },
            {
                "title": "Incidents by Severity",
                "metric_key": "incidents_severity_breakdown",
                "chart_type": DashboardWidget.ChartType.DONUT,
                "position_x": 0,
                "position_y": 1,
                "width": 6,
                "height": 2,
            },
            {
                "title": "Incidents by Status",
                "metric_key": "incidents_status_breakdown",
                "chart_type": DashboardWidget.ChartType.DONUT,
                "position_x": 6,
                "position_y": 1,
                "width": 6,
                "height": 2,
            },
            {
                "title": "Applied Controls by Status",
                "metric_key": "controls_status_breakdown",
                "chart_type": DashboardWidget.ChartType.BAR,
                "position_x": 0,
                "position_y": 3,
                "width": 6,
                "height": 2,
            },
            {
                "title": "Task Templates by Status",
                "metric_key": "task_templates_status_breakdown",
                "chart_type": DashboardWidget.ChartType.DONUT,
                "position_x": 6,
                "position_y": 3,
                "width": 6,
                "height": 2,
            },
        ],
    },
    {
        "ref_id": "seed:compliance-snapshot",
        "name": "Compliance Snapshot",
        "description": "Frameworks in use, control coverage, risk landscape.",
        "widgets": [
            {
                "title": "Frameworks In Use",
                "metric_key": "total_frameworks_in_use",
                "chart_type": DashboardWidget.ChartType.KPI_CARD,
                "position_x": 0,
                "position_y": 0,
                "width": 4,
                "height": 1,
            },
            {
                "title": "Total Controls",
                "metric_key": "total_controls",
                "chart_type": DashboardWidget.ChartType.KPI_CARD,
                "position_x": 4,
                "position_y": 0,
                "width": 4,
                "height": 1,
            },
            {
                "title": "Total Risk Acceptances",
                "metric_key": "total_risk_acceptances",
                "chart_type": DashboardWidget.ChartType.KPI_CARD,
                "position_x": 8,
                "position_y": 0,
                "width": 4,
                "height": 1,
            },
            {
                "title": "Controls by Category",
                "metric_key": "controls_category_breakdown",
                "chart_type": DashboardWidget.ChartType.DONUT,
                "position_x": 0,
                "position_y": 1,
                "width": 6,
                "height": 2,
            },
            {
                "title": "Risk Scenarios by Qualification",
                "metric_key": "risk_scenarios_qualifications_breakdown",
                "chart_type": DashboardWidget.ChartType.BAR,
                "position_x": 6,
                "position_y": 1,
                "width": 6,
                "height": 2,
            },
            {
                "title": "Security Exceptions by Status",
                "metric_key": "security_exceptions_status_breakdown",
                "chart_type": DashboardWidget.ChartType.DONUT,
                "position_x": 0,
                "position_y": 3,
                "width": 6,
                "height": 2,
            },
            {
                "title": "Security Exceptions by Severity",
                "metric_key": "security_exceptions_severity_breakdown",
                "chart_type": DashboardWidget.ChartType.DONUT,
                "position_x": 6,
                "position_y": 3,
                "width": 6,
                "height": 2,
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed example analytics dashboards (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            default=None,
            help="Folder ID to attach the dashboards to. Defaults to the root folder.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Overwrite the layout even if the seed-managed dashboard's widget "
                "set differs from the seed config (i.e. someone edited it)."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        folder_id = options.get("folder")
        force = options.get("force", False)
        folder = (
            Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
        )
        folder_ct = ContentType.objects.get_for_model(Folder)

        for seed in SEEDS:
            ref_id = seed["ref_id"]
            seed_widgets = seed["widgets"]

            # Match strictly on ref_id so user dashboards with the same name
            # are never touched.
            dashboard, created = Dashboard.objects.get_or_create(
                ref_id=ref_id,
                defaults={
                    "name": seed["name"],
                    "description": seed["description"],
                    "folder": folder,
                },
            )

            if created:
                verb = "Created"
            else:
                # Detect divergence from the seed config to catch user edits.
                existing = list(dashboard.widgets.all())
                seed_signature = sorted(
                    (w["metric_key"], w["chart_type"], w["position_x"], w["position_y"])
                    for w in seed_widgets
                )
                existing_signature = sorted(
                    (w.metric_key, w.chart_type, w.position_x, w.position_y)
                    for w in existing
                )
                if existing_signature != seed_signature and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped '{dashboard.name}' ({ref_id}) — widget set "
                            f"differs from seed config (likely user-edited). "
                            f"Re-run with --force to overwrite."
                        )
                    )
                    continue
                verb = "Refreshed"

            dashboard.widgets.all().delete()
            for w in seed_widgets:
                DashboardWidget.objects.create(
                    dashboard=dashboard,
                    folder=folder,
                    target_content_type=folder_ct,
                    target_object_id=folder.id,
                    **w,
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{verb} dashboard '{dashboard.name}' with "
                    f"{len(seed_widgets)} widgets."
                )
            )
