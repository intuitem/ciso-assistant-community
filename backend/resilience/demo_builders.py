"""Resilience demo: business impact analyses and DORA incident reporting.

The BIAs cover the online store and checkout, the Brno assembly line and the
device cloud (connectivity and OTA), each in its sub-domain. They rate the
assets from ``core`` on the 5x5 ISO 27005 matrix, with escalation thresholds
laid out on a shared timeline (1h .. 1 week) so the impact table renders as a
staircase. DORA reports belong to the payments subsidiary and need a
``core.Incident``; ``build_dora`` creates four of them in the "Online Store &
Payments" sub-domain, under ref_ids and names no other builder uses.
"""

from datetime import UTC, datetime, time
from decimal import Decimal
from typing import ClassVar

from core.demo import PAY_ENTITY, DemoBuilder, register
from core.models import Incident, RiskMatrix, Terminology
from resilience.models import (
    AssetAssessment,
    BusinessImpactAnalysis,
    DoraIncidentReport,
    EscalationThreshold,
)

MATRIX_LIBRARY = "urn:intuitem:risk:library:risk-matrix-5x5-iso27005"
PAYMENTS = "Online Store & Payments"

HOUR = 3600
DAY = 24 * HOUR

# key (used below only), name, status, perimeter ref_id, sub-domain,
# due offset, description.
BIAS = [
    (
        "BIA.2026.01",
        "2026 BIA — online store and checkout",
        "in_progress",
        "PER.002",
        PAYMENTS,
        45,
        (
            "Annual impact analysis of the revenue chain, from browsing and card "
            f"authorisation to dispatch from Brno. Feeds the {PAY_ENTITY} DORA "
            "ICT business continuity plan."
        ),
    ),
    (
        "BIA.2026.02",
        "2026 BIA — Brno assembly line",
        "in_review",
        "PER.003",
        "Manufacturing",
        20,
        (
            "Impact of an OT outage on the two assembly lines (Kelvin and "
            "Lookout) and the end-of-line firmware flashing station. Reviewed "
            "with the Plant OT Engineering Manager after the RS.01 ransomware "
            "tabletop."
        ),
    ),
    (
        "BIA.2025.03",
        "2025 BIA — device cloud connectivity and OTA",
        "done",
        "PER.001",
        "Connected Products",
        -75,
        (
            "What happens to installed devices when the device cloud is down: "
            "cameras stop uploading, thermostats fall back to local schedules, "
            "OTA campaigns pause. Signed off by the CIO and the Head of Product "
            "Security."
        ),
    ),
    (
        "BIA.2026.04",
        "2026 BIA — Keystone hub v3 launch readiness",
        "planned",
        "PER.004",
        "Connected Products",
        120,
        "Scoping only: workshops with the Keystone programme leads are booked for Q3.",
    ),
]

# bia key, asset, dependencies, controls (ref_id), documented, tested,
# targets met, observation, thresholds.
# Thresholds: (seconds, matrix impact index 0..4, quanti, unit,
# qualifications, justification).
ASSESSMENTS = [
    # Online store and checkout
    (
        "BIA.2026.01",
        "Store checkout and payments",
        [
            "Online store web front",
            "Device cloud Kubernetes cluster",
            "PostgreSQL primary",
        ],
        ["AC.003", "AC.008", "AC.016"],
        True,
        True,
        False,
        (
            "RTO 2h / RPO 5 min agreed with Finance. The last failover test met "
            "the RPO but took 3h10 to restore authorisations via the backup "
            "Pellion Payments endpoint, so the RTO is not yet met."
        ),
        [
            (
                HOUR,
                1,
                1100,
                "gu",
                ["financial"],
                "About 1,100 orders lost or abandoned; retries absorb part of it.",
            ),
            (
                4 * HOUR,
                3,
                310000,
                "currency",
                ["financial", "reputation"],
                "Launch-day traffic lost to retail partners; instalment sign-ups stop.",
            ),
            (
                DAY,
                4,
                1450000,
                "currency",
                ["financial", "legal", "reputation"],
                (
                    "Maximum tolerable period of disruption: DORA major-incident "
                    f"criteria met for {PAY_ENTITY} and card scheme SLA breached."
                ),
            ),
        ],
    ),
    (
        "BIA.2026.01",
        "Customer and device accounts",
        ["PostgreSQL primary", "Device cloud Kubernetes cluster"],
        ["AC.001", "AC.011"],
        True,
        False,
        False,
        (
            "RTO 4h / RPO 15 min. Restore runbook drafted, not exercised since "
            "the account service moved to the second Kestrava Cloud region."
        ),
        [
            (
                HOUR,
                1,
                8000,
                "people",
                ["availability"],
                "Customers cannot sign in to the store or the companion app.",
            ),
            (
                4 * HOUR,
                2,
                95000,
                "people",
                ["availability", "operational"],
                "New devices cannot be paired; support call volume triples.",
            ),
            (
                3 * DAY,
                3,
                120000,
                "records",
                ["operational", "legal"],
                "Data subject requests miss their statutory deadline.",
            ),
            (
                7 * DAY,
                4,
                900000,
                "currency",
                ["financial", "reputation"],
                "Returns and churn of retail partner customers beyond one week.",
            ),
        ],
    ),
    (
        "BIA.2026.01",
        "Order fulfilment",
        ["Corporate VPN gateway", "PostgreSQL primary"],
        ["AC.003", "AC.012"],
        False,
        False,
        False,
        (
            "RTO 24h / RPO 4h proposed by Logistics, pending validation. The Brno "
            "warehouse can print picking lists manually, but this is not "
            "documented as a recovery procedure; Tallbridge Logistics overflow "
            "warehousing not contracted for outages."
        ),
        [
            (
                4 * HOUR,
                0,
                60,
                "man_hours",
                ["operational"],
                "Warehouse switches to paper picking lists.",
            ),
            (
                DAY,
                2,
                3200,
                "gu",
                ["financial", "operational"],
                "About 3,200 parcels miss the Tallbridge collection.",
            ),
            (
                3 * DAY,
                3,
                750000,
                "currency",
                ["financial", "reputation"],
                "Backlog exceeds two days of shipping capacity; retail orders slip.",
            ),
        ],
    ),
    (
        "BIA.2026.01",
        "Online store web front",
        ["Device cloud Kubernetes cluster"],
        ["AC.010"],
        True,
        True,
        True,
        (
            "Static catalogue served from the CDN for up to 12h; checkout needs "
            "the origin. Region failover rehearsed in January (22 min)."
        ),
        [
            (
                HOUR,
                1,
                45000,
                "currency",
                ["financial"],
                "Browsing works from cache; checkout errors for some customers.",
            ),
            (
                12 * HOUR,
                3,
                520000,
                "currency",
                ["financial", "reputation"],
                "Store effectively closed; social media escalation.",
            ),
        ],
    ),
    (
        "BIA.2026.01",
        "PostgreSQL primary",
        ["Device cloud Kubernetes cluster"],
        ["AC.003"],
        True,
        True,
        True,
        (
            "Streaming replica in the second region; promotion rehearsed "
            "quarterly (last run: 38 min, RPO under 1 min)."
        ),
        [
            (
                HOUR,
                2,
                120000,
                "currency",
                ["availability", "financial"],
                "Orders, payments and account changes all stop writing.",
            ),
            (
                4 * HOUR,
                4,
                900000,
                "currency",
                ["financial", "reputation"],
                "Every primary activity in scope is down.",
            ),
        ],
    ),
    # Brno assembly line
    (
        "BIA.2026.02",
        "Production line control",
        ["Plant SCADA server", "Assembly cell PLCs", "Firmware CI build farm"],
        ["AC.007", "AC.017"],
        True,
        False,
        False,
        (
            "RTO 8h agreed with the plant director: two shifts of stock buffer "
            "for retail partners. Line restart after a full OT rebuild has never "
            "been tested end to end."
        ),
        [
            (
                HOUR,
                0,
                180,
                "gu",
                ["operational"],
                "About 180 devices not assembled; recovered on the next shift.",
            ),
            (
                8 * HOUR,
                2,
                1450,
                "gu",
                ["operational", "financial"],
                "One full shift lost (about 1,450 devices); overtime needed.",
            ),
            (
                3 * DAY,
                3,
                1200000,
                "currency",
                ["financial", "reputation"],
                "Retail partner deliveries missed; penalty clauses triggered.",
            ),
            (
                7 * DAY,
                4,
                2800000,
                "currency",
                ["financial", "reputation", "legal"],
                "Seasonal launch stock missed; Shenwa cannot absorb Kelvin volumes.",
            ),
        ],
    ),
    (
        "BIA.2026.02",
        "Plant SCADA server",
        ["Corporate VPN gateway"],
        ["AC.007", "AC.003"],
        True,
        True,
        False,
        (
            "Cold standby server in the SCADA room; restore from the offline "
            "backup took 6h in the last test, against a 4h target."
        ),
        [
            (
                HOUR,
                1,
                40,
                "man_hours",
                ["operational"],
                "Lines keep running on PLC logic; no supervision or batch records.",
            ),
            (
                4 * HOUR,
                3,
                2,
                "gu",
                ["operational", "safety"],
                "Both lines stopped as a precaution; traceability gap for QA.",
            ),
        ],
    ),
    (
        "BIA.2026.02",
        "Assembly cell PLCs",
        ["Plant SCADA server"],
        ["AC.017"],
        False,
        False,
        False,
        (
            "Spare PLCs on site for cells 1 to 6; program backups held by "
            "Linterra Automation, not in the plant's own repository yet."
        ),
        [
            (
                4 * HOUR,
                2,
                720,
                "gu",
                ["operational"],
                "One cell down: about 720 devices not assembled per 4h.",
            ),
            (
                DAY,
                3,
                95,
                "man_hours",
                ["operational", "financial"],
                "Linterra on-site intervention needed to reload programs.",
            ),
        ],
    ),
    # Device cloud connectivity and OTA
    (
        "BIA.2025.03",
        "MQTT device gateway",
        ["Device cloud Kubernetes cluster"],
        ["AC.003", "AC.018"],
        True,
        True,
        True,
        (
            "Active-active across two Kestrava Cloud regions; devices reconnect "
            "with jittered backoff. Last regional failover: 14 min."
        ),
        [
            (
                HOUR,
                2,
                410000,
                "gu",
                ["availability", "reputation"],
                "About 410,000 devices offline: no remote control, no live view.",
            ),
            (
                4 * HOUR,
                3,
                410000,
                "gu",
                ["availability", "safety", "reputation"],
                "Lookout motion alerts not delivered; security value lost.",
            ),
            (
                DAY,
                4,
                1900000,
                "currency",
                ["financial", "reputation", "legal"],
                "Subscription refunds and mass support contacts; press coverage.",
            ),
        ],
    ),
    (
        "BIA.2025.03",
        "Device cloud Kubernetes cluster",
        ["Workforce identity provider"],
        ["AC.003", "AC.008"],
        True,
        True,
        False,
        (
            "Cluster rebuild from code takes about 5h; RTO is 2h. Accepted "
            "until the second region becomes warm standby."
        ),
        [
            (
                HOUR,
                2,
                410000,
                "gu",
                ["availability"],
                "Device APIs, clip storage and the store back end degrade together.",
            ),
            (
                12 * HOUR,
                4,
                1300000,
                "currency",
                ["financial", "reputation"],
                "All connected services down; contractual credits to partners.",
            ),
        ],
    ),
    (
        "BIA.2025.03",
        "Device firmware and signing keys",
        ["Firmware signing HSM", "Firmware CI build farm"],
        ["AC.013", "AC.014", "AC.015"],
        True,
        True,
        True,
        (
            "OTA can pause for up to a week without impact; the constraint is "
            "shipping a critical security fix within the CRA-driven 72h target."
        ),
        [
            (
                DAY,
                1,
                0,
                "gu",
                ["operational"],
                "OTA campaigns paused; no customer-visible impact.",
            ),
            (
                3 * DAY,
                3,
                410000,
                "gu",
                ["legal", "reputation"],
                "Critical fix cannot reach the installed base within 72h.",
            ),
            (
                7 * DAY,
                4,
                410000,
                "gu",
                ["legal", "reputation", "safety"],
                "Exploited vulnerability left open on every device; CRA reporting.",
            ),
        ],
    ),
    (
        "BIA.2025.03",
        "Companion mobile app",
        ["MQTT device gateway", "Customer and device accounts"],
        ["AC.010"],
        True,
        False,
        False,
        (
            "Devices keep working locally over Matter/Thread when the app back "
            "end is down; pairing and remote access do not."
        ),
        [
            (
                4 * HOUR,
                1,
                30000,
                "people",
                ["availability"],
                "App users cannot reach devices away from home.",
            ),
            (
                DAY,
                3,
                4500,
                "gu",
                ["reputation", "operational"],
                "About 4,500 extra support contacts and app store review drop.",
            ),
        ],
    ),
]


def at(ctx, offset, hour, minute=0):
    return datetime.combine(ctx.day(offset), time(hour, minute), tzinfo=UTC)


# name, ref_id, status, severity, detection, occurred (offset, h, m), reported,
# resolved (or None), description, resolution, assets.
INCIDENTS = [
    (
        "Pellion Payments processor outage",
        "INC-DORA-01",
        Incident.Status.CLOSED,
        Incident.Severity.SEV1,
        Incident.Detection.EXTERNAL,
        (-40, 7, 12),
        (-40, 7, 25),
        (-40, 15, 52),
        (
            "Pellion Payments, the card acquirer and processor, lost its primary "
            "authorisation platform. Every card and instalment payment on the "
            "online store was declined for 8h40."
        ),
        (
            "Pellion restored service from its secondary site. Checkout now "
            "fails over to a second acquiring route, tested monthly."
        ),
        ["Store checkout and payments"],
    ),
    (
        "Kestrava Cloud region degradation slows checkout",
        "INC-DORA-02",
        Incident.Status.RESOLVED,
        Incident.Severity.SEV3,
        Incident.Detection.INTERNAL,
        (-21, 18, 5),
        (-21, 18, 40),
        (-21, 22, 15),
        (
            "Storage latency in the primary Kestrava Cloud region pushed checkout "
            "response times above 20 s during the evening peak."
        ),
        "Checkout traffic moved to the second region; session cache TTL raised.",
        ["Store checkout and payments", "Online store web front"],
    ),
    (
        "Card-testing attack on the checkout tokenisation endpoint",
        "INC-DORA-03",
        Incident.Status.RESOLVED,
        Incident.Severity.SEV2,
        Incident.Detection.INTERNAL,
        (-11, 2, 30),
        (-11, 3, 5),
        (-10, 16, 0),
        (
            "Botnet submitted about 61,000 low-value authorisations with stolen "
            "card numbers through the tokenisation API used by the checkout."
        ),
        (
            "Velocity rules and device fingerprinting added on the tokenisation "
            "endpoint; scheme chargeback monitoring raised with Pellion."
        ),
        ["Store checkout and payments"],
    ),
    (
        "Tokenisation vault misconfiguration breaks instalment collections",
        "INC-DORA-04",
        Incident.Status.ONGOING,
        Incident.Severity.SEV2,
        Incident.Detection.INTERNAL,
        (-3, 6, 0),
        (-3, 9, 20),
        None,
        (
            "A key rotation on the tokenisation vault made stored card tokens "
            "unusable for recurring charges: monthly instalment collections "
            "failed for about 9,400 plans."
        ),
        "",
        ["Store checkout and payments", "PostgreSQL primary"],
    ),
]


@register
class ResilienceBuilder(DemoBuilder):
    """BIAs with asset assessments and thresholds; DORA incident reports."""

    name = "resilience"
    depends = ("core",)
    libraries = (MATRIX_LIBRARY,)
    covers: ClassVar[dict] = {
        BusinessImpactAnalysis: "folder",
        AssetAssessment: "folder",
        EscalationThreshold: "folder",
        DoraIncidentReport: "folder",
    }

    def stamps(self, ctx):
        scope = {"folder__in": ctx.folders()}
        return [
            (BusinessImpactAnalysis, scope, ("name",)),
            (AssetAssessment, scope, ("bia__name", "asset__name")),
            (
                EscalationThreshold,
                scope,
                (
                    "asset_assessment__bia__name",
                    "asset_assessment__asset__name",
                    "point_in_time",
                ),
            ),
            (
                DoraIncidentReport,
                scope,
                ("incident__name", "incident_submission"),
            ),
        ]

    def build(self, ctx):
        self.build_bias(ctx)
        self.build_dora(ctx)

    def subdomain(self, ctx, name):
        return next((f for f in ctx.refs["subdomains"] if f.name == name), ctx.domain)

    def build_bias(self, ctx):
        matrix = RiskMatrix.objects.filter(urn__icontains="5x5-iso27005").first()
        if matrix is None:
            ctx.err("risk matrix not loaded, skipping business impact analyses")
            return
        assets = {asset.name: asset for asset in ctx.refs["assets"]}
        controls = {control.ref_id: control for control in ctx.refs["controls"]}
        perimeters = {p.ref_id: p for p in ctx.refs["perimeters"]}
        qualifications = {
            term.name: term
            for term in Terminology.objects.filter(
                field_path=Terminology.FieldPath.QUALIFICATIONS
            )
        }
        bias = {}
        for key, name, status, perimeter, folder, offset, description in BIAS:
            bia, _ = BusinessImpactAnalysis.objects.get_or_create(
                name=name,
                folder=self.subdomain(ctx, folder),
                defaults={
                    "risk_matrix": matrix,
                    "perimeter": perimeters.get(perimeter),
                    "status": status,
                    "due_date": ctx.day(offset),
                    "description": description,
                },
            )
            bias[key] = bia
        for (
            bia_ref,
            asset_name,
            dependencies,
            control_refs,
            documented,
            tested,
            met,
            observation,
            thresholds,
        ) in ASSESSMENTS:
            assessment, created = AssetAssessment.objects.get_or_create(
                bia=bias[bia_ref],
                asset=assets[asset_name],
                defaults={
                    "folder": bias[bia_ref].folder,
                    "recovery_documented": documented,
                    "recovery_tested": tested,
                    "recovery_targets_met": met,
                    "observation": observation,
                },
            )
            if created:
                assessment.dependencies.set([assets[n] for n in dependencies])
                assessment.associated_controls.set([controls[r] for r in control_refs])
            for seconds, impact, quanti, unit, quals, justification in thresholds:
                threshold, created = EscalationThreshold.objects.get_or_create(
                    asset_assessment=assessment,
                    point_in_time=seconds,
                    defaults={
                        "folder": assessment.folder,
                        "quali_impact": impact,
                        "quanti_impact": quanti,
                        "quanti_impact_unit": unit,
                        "justification": justification,
                    },
                )
                if created:
                    threshold.qualifications.set(
                        [qualifications[q] for q in quals if q in qualifications]
                    )
        ctx.out(f"{len(bias)} business impact analyses seeded")

    def build_dora(self, ctx):
        assets = {asset.name: asset for asset in ctx.refs["assets"]}
        folder = self.subdomain(ctx, PAYMENTS)
        incidents = {}
        for (
            name,
            ref_id,
            status,
            severity,
            detection,
            occurred,
            reported,
            resolved,
            description,
            resolution,
            asset_names,
        ) in INCIDENTS:
            incident, created = Incident.objects.get_or_create(
                ref_id=ref_id,
                folder=folder,
                defaults={
                    "name": name,
                    "status": status,
                    "severity": severity,
                    "description": description,
                    "detection": detection,
                    "occurred_at": at(ctx, *occurred),
                    "reported_at": at(ctx, *reported),
                    "resolved_at": at(ctx, *resolved) if resolved else None,
                    "resolution": resolution,
                    "is_bcp_activated": severity == Incident.Severity.SEV1,
                },
            )
            if created:
                incident.assets.set([assets[n] for n in asset_names])
            incidents[ref_id] = incident
        for ref_id, submission, fields, submitted in self.reports(ctx):
            report, created = DoraIncidentReport.objects.get_or_create(
                incident=incidents[ref_id],
                incident_submission=submission,
                defaults={**fields, "is_submitted": submitted is not None},
            )
            if created and submitted is not None:
                # save() stamps submitted_at with the wall clock.
                DoraIncidentReport.objects.filter(pk=report.pk).update(
                    submitted_at=submitted
                )
        ctx.out("DORA incident reports seeded")

    def reports(self, ctx):
        sub = DoraIncidentReport.SubmissionType
        contacts = {
            "report_currency": "EUR",
            "financial_entity_code": "9695005PAYINSTQ7LY42",
            "competent_authority_code": "FR-ACPR",
            "primary_contact_name": "Claire Morand, Payments Risk Officer",
            "primary_contact_email": "ict-risk@pay.example.com",
            "primary_contact_phone": "+33 4 72 10 20 30",
            "secondary_contact_name": "Tomas Dvorak, SOC lead",
            "secondary_contact_email": "soc@example.com",
            "secondary_contact_phone": "+420 530 100 200",
        }

        # INC-DORA-01: third-party processor outage, major, full cycle.
        processor = {
            **contacts,
            "detection_date_time": at(ctx, -40, 7, 25),
            "classification_date_time": at(ctx, -40, 9, 30),
            "incident_description": (
                "Card acquirer and processor Pellion Payments suffered a full "
                "outage of its authorisation platform; all online store card and "
                "instalment payments were declined."
            ),
            "incident_discovery": "monitoring_systems",
            "originates_from_third_party_provider": (
                "Pellion Payments (card acquiring and processing)"
            ),
            "classification_types": [
                {
                    "classificationCriterion": (
                        "clients_financial_counterparts_and_transactions_affected"
                    )
                },
                {"classificationCriterion": "critical_services_affected"},
                {
                    "classificationCriterion": "geographical_spread",
                    "countryCodeMaterialityThresholds": ["FR", "BE", "NL", "DE"],
                    "memberStatesImpactType": ["clients"],
                },
                {"classificationCriterion": "duration_and_service_downtime"},
            ],
            "incident_type": {
                "incidentClassification": ["external_event", "payment-related"]
            },
            "impact_assessment": {
                "hasImpactOnRelevantClients": True,
                "criticalServicesAffected": (
                    "Online store card acceptance and instalment payment initiation."
                ),
                "affectedAssets": {
                    "affectedClients": {"number": 14200, "percentage": 100},
                    "affectedTransactions": {"number": 17600, "percentage": 100},
                    "valueOfAffectedTransactions": 2310000,
                    "numbersActualEstimate": [
                        "actual_figures_for_clients_affected",
                        "actual_figures_for_transactions_affected",
                    ],
                },
                "isAffectedInfrastructureComponents": "no",
                "isImpactOnFinancialInterest": "yes",
                "serviceImpact": {
                    "serviceDowntime": "000:08:40",
                    "isTemporaryActionsMeasuresForRecovery": True,
                    "descriptionOfTemporaryActionsMeasuresForRecovery": (
                        "Banner on the store; orders kept in basket and customers "
                        "emailed a payment link once service resumed."
                    ),
                },
            },
            "reporting_to_other_authorities": ["none"],
        }
        # INC-DORA-03: card testing, cybersecurity-related.
        card_testing = {
            **contacts,
            "detection_date_time": at(ctx, -11, 3, 5),
            "classification_date_time": at(ctx, -11, 7, 45),
            "incident_description": (
                "Automated card-testing campaign against the checkout "
                "tokenisation API: about 61,000 authorisation attempts of EUR 1 "
                "to 2 with stolen card numbers in 13 hours."
            ),
            "incident_discovery": "it_security",
            "classification_types": [
                {
                    "classificationCriterion": (
                        "clients_financial_counterparts_and_transactions_affected"
                    )
                },
                {
                    "classificationCriterion": "reputational_impact",
                    "reputationalImpactType": [
                        (
                            "the_major_ict-related_incident_has_resulted_in_"
                            "repetitive_complaints_from_different_clients_or_"
                            "financial_counterparts_on_client-facing_services_or_"
                            "critical_business_relationships"
                        )
                    ],
                },
                {"classificationCriterion": "economic_impact"},
            ],
            "incident_type": {
                "incidentClassification": ["cybersecurity-related", "payment-related"],
                "threatTechniques": ["other"],
                "otherThreatTechniques": (
                    "Card testing: enumeration of stolen card numbers through "
                    "low-value authorisations."
                ),
                "indicatorsOfCompromise": (
                    "Requests from 3,800 residential proxy IPs; reused device "
                    "fingerprints; burst of EUR 1.00 authorisations outside store "
                    "basket flows."
                ),
            },
            "impact_assessment": {
                "hasImpactOnRelevantClients": False,
                "criticalServicesAffected": "Card tokenisation for checkout.",
                "affectedAssets": {
                    "affectedTransactions": {"number": 61000, "percentage": 38},
                    "valueOfAffectedTransactions": 84500,
                    "numbersActualEstimate": [
                        "actual_figures_for_transactions_affected",
                        "no_impact_on_clients",
                    ],
                },
                "isAffectedInfrastructureComponents": "yes",
                "affectedInfrastructureComponents": (
                    "Tokenisation API gateway and fraud scoring service."
                ),
                "isImpactOnFinancialInterest": "yes",
            },
            "reporting_to_other_authorities": ["police_law_enforcement"],
        }
        return [
            (
                "INC-DORA-01",
                sub.INITIAL,
                {**processor, "other_information": "Awaiting Pellion root cause."},
                at(ctx, -40, 11, 0),
            ),
            (
                "INC-DORA-01",
                sub.INTERMEDIATE,
                {
                    **processor,
                    "incident_duration": "000:08:40",
                    "info_duration_service_downtime_actual_or_estimate": (
                        "actual_figures"
                    ),
                },
                at(ctx, -37, 16, 0),
            ),
            (
                "INC-DORA-01",
                sub.FINAL,
                {
                    **processor,
                    "incident_duration": "000:08:40",
                    "info_duration_service_downtime_actual_or_estimate": (
                        "actual_figures"
                    ),
                    "root_cause_hl_classification": ["external_event"],
                    "root_causes_detailed_classification": [
                        "external_event_third-party_failures"
                    ],
                    "root_causes_additional_classification": [
                        "monitoring_of_third-party_service_providers"
                    ],
                    "root_causes_information": (
                        "Storage controller failure at Pellion Payments' primary "
                        "site; failover to the secondary site required manual "
                        "approval and took 8h. Single acquiring route at the time."
                    ),
                    "root_cause_addressing_date_time": at(ctx, -20, 10, 0),
                    "incident_resolution_vs_planned": (
                        "Resolved within the BIA maximum tolerable period (24h); "
                        "the 2h RTO for checkout was not met."
                    ),
                    "assessment_of_risk_to_critical_functions": (
                        "Concentration risk on a single acquirer confirmed; second "
                        "acquiring route added to the ICT third-party register."
                    ),
                    "gross_amount_indirect_direct_costs": Decimal("186000.00"),
                    "financial_recoveries_amount": Decimal("40000.00"),
                },
                None,
            ),
            (
                "INC-DORA-02",
                sub.INITIAL,
                {
                    **contacts,
                    "detection_date_time": at(ctx, -21, 18, 40),
                    "classification_date_time": at(ctx, -21, 19, 30),
                    "incident_description": (
                        "Checkout response times above 20 s after a storage "
                        "degradation in the primary Kestrava Cloud region."
                    ),
                    "incident_discovery": "monitoring_systems",
                    "originates_from_third_party_provider": (
                        "Kestrava Cloud (IaaS hosting the store)"
                    ),
                    "classification_types": [
                        {"classificationCriterion": "critical_services_affected"},
                        {"classificationCriterion": "reputational_impact"},
                    ],
                    "incident_type": {"incidentClassification": ["system_failure"]},
                },
                at(ctx, -21, 21, 0),
            ),
            (
                "INC-DORA-02",
                sub.RECLASSIFIED,
                {
                    **contacts,
                    "incident_description": (
                        "Reassessed after resolution: 4h10 of degraded service, no "
                        "transactions lost, materiality thresholds not reached."
                    ),
                    "incident_duration": "000:04:10",
                    "info_duration_service_downtime_actual_or_estimate": (
                        "actual_figures"
                    ),
                },
                at(ctx, -19, 10, 0),
            ),
            (
                "INC-DORA-03",
                sub.INITIAL,
                card_testing,
                at(ctx, -11, 9, 30),
            ),
            (
                "INC-DORA-03",
                sub.INTERMEDIATE,
                {
                    **card_testing,
                    "incident_duration": "001:13:30",
                    "info_duration_service_downtime_actual_or_estimate": (
                        "no_information_available"
                    ),
                    "other_information": (
                        "No service downtime. Chargeback exposure still being "
                        "assessed with Pellion Payments."
                    ),
                },
                at(ctx, -8, 15, 0),
            ),
            (
                "INC-DORA-04",
                sub.INITIAL,
                {
                    **contacts,
                    "detection_date_time": at(ctx, -3, 9, 20),
                    "classification_date_time": at(ctx, -3, 12, 0),
                    "incident_description": (
                        "Key rotation on the tokenisation vault left stored card "
                        "tokens unusable for recurring charges; instalment "
                        "collections failing."
                    ),
                    "incident_discovery": "clients",
                    "classification_types": [
                        {
                            "classificationCriterion": (
                                "clients_financial_counterparts_and_transactions_"
                                "affected"
                            )
                        },
                        {
                            "classificationCriterion": "data_losses",
                            "dataLosseMaterialityThresholds": ["availability"],
                            "dataLossesDescription": (
                                "Stored tokens unavailable; no data disclosed."
                            ),
                        },
                    ],
                    "incident_type": {
                        "incidentClassification": [
                            "process_failure",
                            "payment-related",
                        ]
                    },
                    "impact_assessment": {
                        "hasImpactOnRelevantClients": True,
                        "criticalServicesAffected": "Instalment plan collections.",
                        "affectedAssets": {
                            "affectedClients": {"number": 9400, "percentage": 31},
                            "numbersActualEstimate": ["estimates_for_clients_affected"],
                        },
                        "isAffectedInfrastructureComponents": "yes",
                        "affectedInfrastructureComponents": "Tokenisation vault.",
                        "isImpactOnFinancialInterest": "information_not_available",
                    },
                    "other_information": (
                        "Collections paused; no late fees will be charged."
                    ),
                },
                at(ctx, -3, 13, 30),
            ),
        ]
