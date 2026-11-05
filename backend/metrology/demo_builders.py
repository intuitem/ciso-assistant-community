"""Metrology demo builder: custom metrics with a year of samples, and dashboards.

Instances measure definitions from the Core Cybersecurity Metrics library.
Company-specific definitions are authored in the demo domain too, but no
instance uses them: MetricInstance.metric_definition is PROTECT, so an
instance on a domain-owned definition would block the scoped flush. Samples
are monthly and drift from a start value toward an end value with noise from
``ctx.rng``. Builtin metric samples are computed by
the system and never seeded.
"""

from datetime import UTC, datetime, time
from typing import ClassVar

from core.demo import COMPANY, PAY_ENTITY, DemoBuilder, register
from core.models import Terminology
from metrology.models import (
    CustomMetricSample,
    Dashboard,
    DashboardWidget,
    MetricDefinition,
    MetricInstance,
)

METRICS_LIBRARY = "urn:intuitem:risk:library:core-cybersecurity-metrics"

MATURITY_LEVELS = [
    ("Initial", "Ad hoc, undocumented practices."),
    ("Managed", "Practices exist on some lines, owner-dependent."),
    ("Defined", "Documented standard applied to every line."),
    ("Measured", "Monitored with KPIs and reviewed quarterly."),
    ("Optimised", "Continuously improved from incident and audit feedback."),
]

# ref_id, name, unit, higher_is_better, default target, description.
# A unit of None with choices makes a qualitative definition.
DEFINITIONS = [
    (
        "MET-01",
        "OTA rollout success rate",
        "percentage",
        True,
        99.5,
        (
            "Devices that installed an over-the-air firmware release and reported "
            "back healthy within 72 hours, over devices targeted by the rollout."
        ),
    ),
    (
        "MET-02",
        "Median days to fix critical firmware vulnerabilities",
        "days",
        False,
        30.0,
        (
            "Median days between PSIRT confirmation of a critical firmware "
            "vulnerability and general availability of the fixed release (CRA "
            "vulnerability handling)."
        ),
    ),
    (
        "MET-03",
        "Devices on supported firmware",
        "percentage",
        True,
        95.0,
        (
            "Share of active Kelvin, Lookout and Keystone devices running a firmware "
            "version still inside its declared support period."
        ),
    ),
    (
        "MET-04",
        "Plant unplanned downtime from cyber causes",
        "hours",
        False,
        0.0,
        (
            "Hours of unplanned stoppage of the Brno assembly lines attributed to a "
            "cyber event (malware, unauthorised change, OT network fault)."
        ),
    ),
    (
        "MET-05",
        "PCI DSS external scan pass rate",
        "percentage",
        True,
        100.0,
        (
            "Quarterly ASV external scans of the cardholder data environment passed "
            "at first attempt, over scans run."
        ),
    ),
    (
        "MET-06",
        "Vulnerability reports received through the disclosure programme",
        "count",
        True,
        None,
        (
            "Valid reports received from researchers and customers through the "
            "coordinated vulnerability disclosure page, per month."
        ),
    ),
    (
        "MET-07",
        "OT network segmentation maturity",
        None,
        True,
        4.0,
        (
            "Self-assessed maturity of zone and conduit segmentation on the Brno "
            "assembly lines (IEC 62443-3-2)."
        ),
    ),
]

# ref_id, name, library definition ref_id, status,
# frequency, (start, end) or None for no samples, months of samples, months
# since the last sample, decimals, observation for the latest sample.
INSTANCES = [
    (
        "KPI.01",
        "Phishing simulation click rate — all staff",
        "AWR-02",
        "active",
        "monthly",
        (14.0, 4.5),
        12,
        0,
        1,
        "Lowest rate since the programme started; Brno shift supervisors still above 8%.",
    ),
    (
        "KPI.02",
        "Security awareness training completion",
        "AWR-01",
        "active",
        "monthly",
        (62.0, 93.0),
        12,
        0,
        1,
        "",
    ),
    (
        "KPI.03",
        "OTA rollout success rate — Kelvin and Keystone fleet",
        "VULN-03",
        "active",
        "monthly",
        (95.8, 99.3),
        12,
        0,
        1,
        "Staged rollout halted twice at the 5% canary ring; both fixed before wider release.",
    ),
    (
        "KPI.04",
        "Devices on supported firmware — connected fleet",
        "VULN-03",
        "active",
        "monthly",
        (76.0, 91.0),
        12,
        0,
        1,
        "First-generation Lookout cameras reach end of support in March.",
    ),
    (
        "KPI.05",
        "Median days to fix critical firmware vulnerabilities",
        "VULN-02",
        "active",
        "monthly",
        (64.0, 21.0),
        12,
        0,
        0,
        "Below the 30-day CRA readiness target for the third month running.",
    ),
    (
        "KPI.06",
        "PCI DSS external scan pass rate",
        "GOV-01",
        "active",
        "monthly",
        (78.0, 97.0),
        12,
        0,
        0,
        "Last failure was a TLS cipher on the instalment API, fixed within 48 hours.",
    ),
    (
        "KPI.07",
        "Mean time to respond to incidents",
        "INC-03",
        "active",
        "monthly",
        (11.0, 5.0),
        12,
        0,
        1,
        "",
    ),
    (
        "KPI.08",
        "Brno plant unplanned downtime from cyber causes",
        "RES-06",
        "active",
        "monthly",
        (14.0, 1.5),
        12,
        0,
        1,
        "One USB-borne infection on a packing-line HMI, contained in 90 minutes.",
    ),
    (
        "KPI.09",
        "Security monitoring maturity — Brno plant OT",
        "MON-01",
        "active",
        "quarterly",
        (1.0, 3.0),
        4,
        0,
        0,
        "OT network traffic now mirrored to the SOC sensor.",
    ),
    (
        "KPI.10",
        "Open vulnerability reports from the disclosure programme",
        "VULN-01",
        "active",
        "monthly",
        (23.0, 8.0),
        12,
        0,
        0,
        "Report volume doubled after the bug bounty launch; triage SLA held.",
    ),
    (
        "KPI.11",
        "Backup test success rate — Brno warehouse systems",
        "RES-03",
        "stale",
        "monthly",
        (80.0, 92.0),
        8,
        4,
        0,
        "Restore tests paused during the warehouse management system migration.",
    ),
    (
        "KPI.12",
        "Supplier assessment coverage — critical vendors",
        "TPR-01",
        "draft",
        "quarterly",
        None,
        0,
        0,
        0,
        "",
    ),
    (
        "KPI.13",
        "Open critical and high vulnerabilities — legacy MES",
        "VULN-01",
        "deprecated",
        "monthly",
        (42.0, 35.0),
        6,
        6,
        0,
        "Legacy MES decommissioned at Brno, metric retired.",
    ),
    (
        "KPI.14",
        "MFA adoption — workforce accounts",
        "IAM-01",
        "active",
        "monthly",
        (71.0, 97.5),
        12,
        0,
        1,
        "Remaining accounts are shared kiosks on the Brno packing line, under exception.",
    ),
    (
        "KPI.15",
        "Open critical and high vulnerabilities — cardholder data environment",
        "VULN-01",
        "active",
        "monthly",
        (17.0, 3.0),
        12,
        0,
        0,
        "",
    ),
    (
        "KPI.16",
        "Immutable backup coverage — device cloud",
        "RES-02",
        "active",
        "monthly",
        (58.0, 91.0),
        12,
        0,
        1,
        "Telemetry store moved to object-locked snapshots on Kestrava Cloud.",
    ),
    (
        "KPI.17",
        "Critical vulnerability remediation time — corporate IT",
        "VULN-02",
        "active",
        "monthly",
        (24.0, 9.0),
        12,
        0,
        0,
        "Laptop patching now enforced through the MDM within 7 days.",
    ),
]

# Dashboard: ref_id, name, description, widgets.
# Widget: (instance ref_id or None for text, chart type, x, y, w, h, title, text).
DASHBOARDS = [
    (
        "DB.01",
        "Monthly security KPIs",
        (
            "Board pack: the headline indicators reviewed at the monthly security "
            "steering committee chaired by the CISO."
        ),
        [
            (
                None,
                "text",
                0,
                0,
                12,
                1,
                None,
                (
                    "**Security steering committee.** Targets come from the FY2026 "
                    "security plan; red lines on charts are the committed targets."
                ),
            ),
            ("KPI.01", "kpi_card", 0, 1, 3, 2, None, None),
            ("KPI.03", "kpi_card", 3, 1, 3, 2, None, None),
            ("KPI.14", "gauge", 6, 1, 3, 2, None, None),
            ("KPI.07", "kpi_card", 9, 1, 3, 2, None, None),
            ("KPI.01", "line", 0, 3, 6, 3, "Phishing click rate trend", None),
            ("KPI.02", "area", 6, 3, 6, 3, "Training completion trend", None),
            ("KPI.05", "bar", 0, 6, 6, 3, None, None),
            ("KPI.08", "line", 6, 6, 6, 3, None, None),
        ],
    ),
    (
        "DB.02",
        "Brno plant resilience",
        "Cyber downtime, restore readiness and OT monitoring for the plant management.",
        [
            ("KPI.09", "kpi_card", 0, 0, 4, 2, None, None),
            ("KPI.11", "sparkline", 4, 0, 4, 2, None, None),
            ("KPI.08", "kpi_card", 8, 0, 4, 2, None, None),
            ("KPI.08", "line", 0, 2, 12, 3, "Cyber downtime over the year", None),
        ],
    ),
    (
        "DB.03",
        "Product security (CRA)",
        (
            "PSIRT and firmware indicators reviewed monthly by the Head of Product "
            "Security, the evidence base for the CRA vulnerability handling duties."
        ),
        [
            (
                None,
                "text",
                0,
                0,
                12,
                1,
                None,
                (
                    "**PSIRT monthly review.** Kelvin, Lookout and Keystone fleets. "
                    "Fix times count from PSIRT confirmation to fixed release."
                ),
            ),
            ("KPI.03", "gauge", 0, 1, 4, 2, None, None),
            ("KPI.04", "kpi_card", 4, 1, 4, 2, None, None),
            ("KPI.10", "kpi_card", 8, 1, 4, 2, None, None),
            ("KPI.05", "line", 0, 3, 6, 3, "Critical firmware fix time", None),
            ("KPI.04", "area", 6, 3, 6, 3, "Fleet on supported firmware", None),
            ("KPI.16", "sparkline", 0, 6, 12, 2, None, None),
        ],
    ),
    (
        "DB.04",
        f"{PAY_ENTITY} security posture",
        (
            "PCI DSS and DORA indicators reported quarterly to the Payments Risk "
            "Officer and the subsidiary board."
        ),
        [
            ("KPI.06", "kpi_card", 0, 0, 6, 2, None, None),
            ("KPI.15", "kpi_card", 6, 0, 6, 2, None, None),
            ("KPI.06", "bar", 0, 2, 6, 3, "ASV scan pass rate", None),
            ("KPI.15", "line", 6, 2, 6, 3, "CDE vulnerabilities over the year", None),
        ],
    ),
]


@register
class MetrologyBuilder(DemoBuilder):
    """Authored metric definitions, instances with samples, and four dashboards."""

    name = "metrology"
    libraries = (METRICS_LIBRARY,)
    depends = ("core",)
    covers: ClassVar[dict] = {
        MetricDefinition: "folder",
        MetricInstance: "folder",
        CustomMetricSample: "folder",
        Dashboard: "folder",
        DashboardWidget: "folder",
    }

    def stamps(self, ctx):
        folders = ctx.folders()
        return [
            (MetricDefinition, {"folder__in": folders}, ("ref_id",)),
            (MetricInstance, {"folder__in": folders}, ("ref_id",)),
            (
                CustomMetricSample,
                {"folder__in": folders},
                ("metric_instance__ref_id", "timestamp"),
            ),
            (Dashboard, {"folder__in": folders}, ("ref_id",)),
            (
                DashboardWidget,
                {"folder__in": folders},
                ("dashboard__ref_id", "position_y", "position_x"),
            ),
        ]

    def build(self, ctx):
        definitions = self.build_definitions(ctx)
        definitions.update(
            {
                d.ref_id: d
                for d in MetricDefinition.objects.filter(
                    library__urn=METRICS_LIBRARY
                ).order_by("ref_id")
            }
        )
        instances = self.build_instances(ctx, definitions)
        self.build_dashboards(ctx, instances)

    def build_definitions(self, ctx):
        units = {
            term.name: term
            for term in Terminology.objects.filter(
                field_path=Terminology.FieldPath.METRIC_UNIT, builtin=True
            )
        }
        definitions = {}
        for ref_id, name, unit, higher, target, description in DEFINITIONS:
            qualitative = unit is None
            definition, _ = MetricDefinition.objects.get_or_create(
                ref_id=ref_id,
                folder=ctx.domain,
                defaults={
                    "name": name,
                    "description": description,
                    "category": MetricDefinition.Category.QUALITATIVE
                    if qualitative
                    else MetricDefinition.Category.QUANTITATIVE,
                    "unit": units.get(unit),
                    "choices_definition": [
                        {"name": label, "description": text}
                        for label, text in MATURITY_LEVELS
                    ]
                    if qualitative
                    else None,
                    "higher_is_better": higher,
                    "default_target": target,
                    "provider": COMPANY,
                },
            )
            definitions[ref_id] = definition
        return definitions

    def build_instances(self, ctx, definitions):
        instances = {}
        for (
            ref_id,
            name,
            definition_ref,
            status,
            frequency,
            trend,
            months,
            gap,
            decimals,
            note,
        ) in INSTANCES:
            definition = definitions.get(definition_ref)
            if definition is None:
                ctx.err(f"metric definition {definition_ref} not loaded")
                continue
            # save() copies the definition's default target, as in the UI.
            instance, created = MetricInstance.objects.get_or_create(
                ref_id=ref_id,
                folder=ctx.domain,
                defaults={
                    "name": name,
                    "metric_definition": definition,
                    "status": status,
                    "collection_frequency": frequency,
                },
            )
            instances[ref_id] = instance
            if created and trend:
                self.build_samples(
                    ctx, instance, frequency, trend, months, gap, decimals, note
                )
        return instances

    def build_samples(
        self, ctx, instance, frequency, trend, months, gap, decimals, note
    ):
        start, end = trend
        qualitative = (
            instance.metric_definition.category == MetricDefinition.Category.QUALITATIVE
        )
        step = 91 if frequency == "quarterly" else 30
        spread = abs(end - start) * 0.08
        for index in range(months):
            progress = index / max(months - 1, 1)
            # Oldest first; the latest sample sits two days before the anchor so
            # it is never in the future, whatever the seeding time of day.
            offset = -2 - step * (gap + months - 1 - index)
            moment = datetime.combine(ctx.day(offset), time(8, 0), tzinfo=UTC)
            level = start + (end - start) * progress
            if qualitative:
                value = {"choice_index": round(level)}
            else:
                noisy = level + ctx.rng.uniform(-spread, spread)
                value = {"result": round(max(noisy, 0), decimals or None)}
            CustomMetricSample.objects.create(
                metric_instance=instance,
                folder=instance.folder,
                timestamp=moment,
                value=value,
                observation=note if index == months - 1 and note else None,
            )

    def build_dashboards(self, ctx, instances):
        for ref_id, name, description, widgets in DASHBOARDS:
            dashboard, created = Dashboard.objects.get_or_create(
                ref_id=ref_id,
                folder=ctx.domain,
                defaults={"name": name, "description": description},
            )
            if not created:
                continue
            for instance_ref, chart, x, y, w, h, title, text in widgets:
                instance = instances.get(instance_ref) if instance_ref else None
                if instance_ref and instance is None:
                    continue
                widget = DashboardWidget(
                    dashboard=dashboard,
                    folder=dashboard.folder,
                    metric_instance=instance,
                    chart_type=chart,
                    position_x=x,
                    position_y=y,
                    width=w,
                    height=h,
                    title=title,
                    text_content=text,
                    # Charts span the whole sample history: a relative window
                    # would empty them on a frozen-date screenshot dataset.
                    time_range=DashboardWidget.TimeRange.ALL_TIME,
                )
                widget.full_clean(exclude=["folder"])
                widget.save()
