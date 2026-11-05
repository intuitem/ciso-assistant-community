"""Core demo builders: operations.

- ``evidence``: evidences with real attachments, recurring and one-off tasks
- ``findings``: follow-ups and findings, vulnerabilities, security exceptions,
  draft risk acceptances
- ``incidents``: incidents with their timelines

Evidences are filed against the core controls, the lead audit's requirement
assessments and the specialised audits (PCI DSS, IEC 62443, CRA), so control
and audit pages show what backs them.
"""

from datetime import UTC, datetime, time
from decimal import Decimal
from typing import ClassVar

from django.core.files.base import ContentFile

from core.demo import COMPANY, PAY_ENTITY, DemoBuilder, register
from core.models import (
    Evidence,
    EvidenceRevision,
    Finding,
    FindingsAssessment,
    Incident,
    Perimeter,
    RequirementAssessment,
    RiskAcceptance,
    SecurityException,
    TaskNode,
    TaskTemplate,
    Terminology,
    TimelineEntry,
    Vulnerability,
)
from core.utils import _generate_occurrences


def _ts(ctx, offset, hour, minute=0):
    return datetime.combine(ctx.day(offset), time(hour, minute), tzinfo=UTC)


def _controls(ctx, ref_ids):
    by_ref = {c.ref_id: c for c in ctx.refs.get("controls", [])}
    return [by_ref[r] for r in ref_ids if r in by_ref]


def _assets(ctx, names):
    by_name = {a.name: a for a in ctx.refs.get("assets", [])}
    return [by_name[n] for n in names if n in by_name]


def _audits(ctx):
    """Audit ref_id -> compliance assessment."""
    return {a.ref_id: a for a in ctx.refs.get("audits") or [] if a.ref_id}


def _lead_requirements(ctx):
    """Requirement ref_id -> assessment, on the lead audit."""
    audits = ctx.refs.get("audits") or []
    if not audits:
        return {}
    return {
        ra.requirement.ref_id: ra
        for ra in RequirementAssessment.objects.filter(
            compliance_assessment=audits[0]
        ).select_related("requirement")
    }


# ---------------------------------------------------------------------------
# Attachment content. Small, plausible files: CSV exports, JSON reports,
# Markdown minutes and single-page PDFs, so the preview and download work.
# Every value is fixed or derived from the date anchor: same anchor, same bytes.
# ---------------------------------------------------------------------------


def _pdf(title, lines):
    """A minimal, valid one-page PDF (Helvetica, ASCII text)."""

    def esc(text):
        text = text.encode("ascii", "replace").decode("ascii")
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    body = [
        "BT",
        "/F1 16 Tf",
        "56 780 Td",
        f"({esc(title)}) Tj",
        "/F1 10 Tf",
        "14 TL",
        "0 -10 Td",
    ]
    for line in lines:
        body.append(f"T* ({esc(line)}) Tj")
    body.append("ET")
    stream = "\n".join(body).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()
    return bytes(out)


def _text(lines):
    return ("\n".join(lines) + "\n").encode()


def _access_review_csv(ctx, offset):
    rows = [
        ("e.laurent", "Firmware engineering", "Firmware signing HSM", "custodian"),
        ("k.berg", "Firmware engineering", "Firmware CI build farm", "admin"),
        ("p.dubois", "Cloud platform", "Device cloud Kubernetes", "cluster-admin"),
        ("s.okafor", "Cloud platform", "PostgreSQL primary", "superuser"),
        ("t.novak", "Plant engineering", "Plant SCADA server", "engineer"),
        ("l.fischer", "Customer care", "Store admin console", "agent"),
        ("mireo-svc-12", "Customer care (Mireo Support)", "Support portal", "camera"),
        ("j.vermeer", "Hardware design", "Product PLM", "approver"),
        ("contractor-07", "Hardware design", "Product PLM", "editor"),
        ("m.horak", "Payments", "Payments back office", "refund-approver"),
    ]
    decisions = ["kept", "kept", "revoked", "downgraded", "kept"]
    # The decisions shift with the quarter, so two exports never look copied.
    shift = abs(offset) // 90
    return _text(
        [
            (
                f"# {COMPANY} - quarterly access review, Brightline Identity export "
                f"{ctx.day(offset)}"
            ),
            "account,department,system,entitlement,reviewer,decision",
            *(
                f"{a},{d},{s},{e},manager:{d.split()[0].lower()},"
                f"{decisions[(i + shift) % len(decisions)]}"
                for i, (a, d, s, e) in enumerate(rows)
            ),
        ]
    )


def _encryption_csv(ctx, offset):
    lines = [
        f"# MDM compliance export {ctx.day(offset)}",
        "device,site,platform,owner_department,disk_encryption,last_check_in",
    ]
    sites = ["LYO", "BRN", "EHV"]
    platforms = ["Windows 11", "macOS 14", "Windows 11", "Ubuntu 22.04"]
    departments = [
        "Firmware engineering",
        "Hardware design",
        "Plant engineering",
        "Customer care",
        "Finance",
        "Sales",
    ]
    for index in range(1, 31):
        status = "encrypted" if index % 13 else "pending_reboot"
        site = sites[index % 3]
        lines.append(
            f"LT-{site}-{index:04d},{site},{platforms[index % 4]},"
            f"{departments[index % 6]},{status},{ctx.day(offset - index % 3)}"
        )
    return _text(lines)


def _scan_csv(ctx, offset):
    return _text(
        [
            f"# Monthly vulnerability scan summary, run {ctx.day(offset)}",
            "asset_group,critical,high,medium,low,hosts_scanned",
            "Online store web front (DMZ),0,1,6,12,14",
            "Device cloud Kubernetes,1,3,10,27,52",
            "MQTT device gateway,0,1,2,5,8",
            "Corporate endpoints (Lyon, Eindhoven),0,3,22,58,388",
            "Brno plant office LAN,0,2,9,17,96",
            "Brno OT segment (passive),2,4,7,3,41",
        ]
    )


def _asv_csv(ctx, offset):
    return _text(
        [
            f"# {PAY_ENTITY} - external ASV scan summary, scanned {ctx.day(offset)}",
            "# Approved scanning vendor: Redhaven Security",
            "target,component,highest_cvss,result,note",
            "checkout.shop.example,web server,0.0,pass,",
            "checkout.shop.example,TLS configuration,0.0,pass,TLS 1.2+ only",
            "api.pay.example,API gateway,4.3,pass,medium below threshold",
            "pay-callbacks.pay.example,callback endpoint,0.0,pass,",
            "vpn.pay.example,VPN gateway,5.3,pass,disputed: patched before rescan",
            "Overall,,,pass,attestation issued",
        ]
    )


def _badge_csv(ctx, offset):
    return _text(
        [
            f"# Brno assembly plant - badge access audit, {ctx.day(offset)}",
            "badge_id,holder_type,zone,status,finding",
            "BRN-10021,employee,Firmware programming room,active,ok",
            "BRN-10087,employee,Firmware programming room,active,ok",
            (
                "BRN-20113,integrator (Linterra Automation),Line 2 control cabinet,"
                "active,contract task ended - deactivate"
            ),
            "BRN-10342,employee,SMT line,active,ok",
            "BRN-20151,temp agency,Warehouse,active,ok",
            "BRN-30007,visitor,Warehouse,expired,ok",
            "BRN-10519,employee,Server room,active,left company - deactivate",
        ]
    )


def _plc_backup_csv(ctx, offset):
    cells = [
        ("Cell 1 SMT", "PLC-C1-01", "v14.2"),
        ("Cell 1 SMT", "PLC-C1-02", "v14.2"),
        ("Cell 2 Kelvin assembly", "PLC-C2-01", "v9.8"),
        ("Cell 2 Kelvin assembly", "PLC-C2-02", "v9.8"),
        ("Cell 3 Keystone assembly", "PLC-C3-01", "v3.1"),
        ("Cell 4 end-of-line test", "PLC-C4-01", "v6.0"),
        ("Cell 4 firmware flashing", "PLC-C4-02", "v6.0"),
    ]
    lines = [
        f"# PLC program backup verification, Brno plant, {ctx.day(offset)}",
        "cell,plc,program_version,last_backup,hash_match,offline_copy",
    ]
    for index, (cell, plc, version) in enumerate(cells):
        match = "no - re-exported" if index == 5 else "yes"
        lines.append(
            f"{cell},{plc},{version},{ctx.day(offset - 1 - index % 2)},{match},yes"
        )
    return _text(lines)


def _supplier_csv(ctx, offset):
    return _text(
        [
            (
                f"# Supplier security questionnaire responses, received by "
                f"{ctx.day(offset)}"
            ),
            "supplier,service,iso27001,soc2_type2,mfa_enforced,breach_last_24m,score",
            "Kestrava Cloud,IaaS for the device cloud and store,yes,yes,yes,no,94",
            "Pellion Payments,Card acquiring and processing,yes,yes,yes,no,92",
            "Shenwa Contract Manufacturing,Lookout camera assembly,yes,no,partial,no,68",
            "Orbisil Semiconductors,Wi-Fi and Thread modules,yes,no,yes,no,81",
            (
                "Tallbridge Logistics,Parcel delivery and overflow warehousing,"
                "no,no,partial,no,59"
            ),
            "Mireo Support,Outsourced customer support,yes,yes,partial,yes,63",
            "Linterra Automation,PLC and SCADA integration,no,no,no,no,41",
            "Fennick Analytics,Companion app analytics SDK,no,yes,yes,no,74",
        ]
    )


def _log_retention_json(ctx, offset):
    return _text(
        [
            "{",
            f'  "exported_at": "{ctx.day(offset)}",',
            '  "siem": "central-log-platform",',
            (
                '  "retention_days": {"security": 365, "application": 90, '
                '"audit": 2555, "ot": 730},'
            ),
            '  "immutable_storage": true,',
            (
                '  "sources": ["brightline-identity", "kubernetes-audit", '
                '"mqtt-gateway", "vpn-gateway", "postgresql", "firmware-ci", '
                '"signing-hsm", "brno-ot-sensor"]'
            ),
            "}",
        ]
    )


def _ota_report(product, release, previous, devices):
    """Staged OTA rollout report: four rings, each a fraction of the fleet."""

    def make(ctx, offset):
        rings = [
            ("internal", 0.001, 0, 2),
            ("ring-1", 0.01, 3, 4),
            ("ring-2", 0.10, 3, 9),
            ("general", 1.0, 7, 31),
        ]
        lines = [
            "{",
            f'  "product": "{product}",',
            f'  "release": "{release}",',
            f'  "previous_release": "{previous}",',
            (
                '  "signature": {"key": "ota-release-2026", "hsm_slot": 3, '
                '"verified_on_device": true},'
            ),
            '  "sbom_published": true,',
            '  "rings": [',
        ]
        start = offset - 14
        for index, (ring, share, delay, failures) in enumerate(rings):
            start += delay
            target = max(1, int(devices * share))
            rate = round(100 - failures * 100 / target, 3)
            comma = "," if index < len(rings) - 1 else ""
            lines.append(
                f'    {{"ring": "{ring}", "started": "{ctx.day(start)}", '
                f'"devices": {target}, "failed_installs": {failures}, '
                f'"success_rate": {rate}, "halt_threshold": 99.0}}{comma}'
            )
        lines += [
            "  ],",
            '  "rollbacks": 0,',
            f'  "completed": "{ctx.day(offset)}"',
            "}",
        ]
        return _text(lines)

    return make


def _sbom(release, busybox, openssl):
    """CycloneDX excerpt for a Keystone hub firmware release."""

    def make(ctx, offset):
        components = [
            ("linux-kernel", "6.1.92", "GPL-2.0-only"),
            ("busybox", busybox, "GPL-2.0-only"),
            ("openssl", openssl, "Apache-2.0"),
            ("mbedtls", "3.5.2", "Apache-2.0"),
            ("openthread", "thread-reference-20230706", "BSD-3-Clause"),
            ("matter-sdk", "1.3.0.0", "Apache-2.0"),
            ("zlib", "1.3.1", "Zlib"),
            ("hub-agent", release, "LicenseRef-proprietary"),
        ]
        lines = [
            "{",
            '  "bomFormat": "CycloneDX",',
            '  "specVersion": "1.5",',
            '  "metadata": {',
            f'    "timestamp": "{ctx.day(offset)}T08:00:00Z",',
            (
                f'    "component": {{"type": "firmware", "name": "keystone-hub", '
                f'"version": "{release}"}},'
            ),
            f'    "supplier": {{"name": "{COMPANY}"}}',
            "  },",
            '  "components": [',
        ]
        for index, (name, version, licence) in enumerate(components):
            comma = "," if index < len(components) - 1 else ""
            lines.append(
                f'    {{"type": "library", "name": "{name}", "version": "{version}", '
                f'"purl": "pkg:generic/{name}@{version}", '
                f'"licenses": [{{"license": {{"id": "{licence}"}}}}]}}{comma}'
            )
        lines += ["  ]", "}"]
        return _text(lines)

    return make


def _tabletop_md(ctx, offset):
    return _text(
        [
            f"# Incident response tabletop - {ctx.day(offset)}",
            "",
            (
                "**Scenario:** the OTA release signing key is suspected stolen after a "
                "build-farm compromise; a malicious Kelvin thermostat update is staged "
                "for ring 1 (RS.07)."
            ),
            "",
            "## Participants",
            (
                "CISO, Head of Product Security (PSIRT), Kelvin firmware lead, SOC lead, "
                "DPO, Legal, Communications, Customer care (Mireo Support liaison)"
            ),
            "",
            "## Timeline exercised",
            (
                "- T+0: firmware CI raises an unexpected signing request outside a "
                "release window"
            ),
            "- T+30min: OTA rollout frozen for every product line",
            (
                "- T+2h: key revoked in the HSM, devices told to distrust it via the "
                "next certificate bundle"
            ),
            (
                "- T+20h: CRA early warning drafted (24h deadline) for the CSIRT and "
                "ENISA single reporting platform"
            ),
            "- T+3d: customer notice and NIS2 incident notification",
            "",
            "## Gaps",
            (
                "1. Nobody could say how long fielded Keystone hubs take to accept a "
                "new trust bundle."
            ),
            "2. No pre-approved customer notice for a product security incident.",
            "3. Out-of-band contact list for HSM custodians was out of date.",
            "",
            "## Actions",
            "- Measure trust-bundle propagation on the ring-1 fleet",
            "- Legal and PSIRT to draft CRA and customer notice templates",
            "- Refresh the custodian call tree quarterly",
        ]
    )


def _retention_md(ctx, offset):
    return _text(
        [
            f"# Data retention schedule - draft {ctx.day(offset)}",
            "",
            "| Record | Retention | Owner |",
            "|---|---|---|",
            (
                "| Lookout camera clips (cloud) | 30 days by default, 7-60 days "
                "chosen by the customer | Product (Lookout) |"
            ),
            (
                "| Kelvin thermostat telemetry | 24 months, then aggregated | "
                "Product (Kelvin) |"
            ),
            "| Customer and device accounts | Account lifetime + 3 years | DPO |",
            "| Customer orders | 10 years | Finance |",
            f"| Card transaction logs | 13 months | {PAY_ENTITY} |",
            "| Support tickets (Mireo Support) | 3 years | Customer care |",
            "| Brno plant CCTV | 30 days | Facilities |",
            "| Job applications | 2 years | HR |",
        ]
    )


def _ceremony_md(ctx, offset):
    return _text(
        [
            f"# OTA signing-key ceremony check - {ctx.day(offset)}",
            "",
            "**Location:** Lyon HQ, secure room 2. **Quorum:** 2 of 3 custodians.",
            "",
            "| Check | Result |",
            "|---|---|",
            "| HSM tamper seals match the register | ok |",
            "| Firmware signing HSM firmware and audit log integrity | ok |",
            (
                "| Signing operations since last check | 14, all matched to release "
                "tickets |"
            ),
            "| Unexpected signing requests from firmware CI | none |",
            "| Backup token in the Lyon safe, sealed | ok |",
            "| Custodian list current (joiners/leavers) | 1 change pending |",
            "",
            "Signed: two custodians, witnessed by the Head of Product Security.",
        ]
    )


def _triage_md(ctx, offset):
    return _text(
        [
            f"# CRA vulnerability triage review - {ctx.day(offset)}",
            "",
            (
                "**Chair:** Head of Product Security (PSIRT). **Attendees:** Kelvin, "
                "Lookout and Keystone firmware leads; companion app lead; DPO."
            ),
            "",
            "## Intake since last review",
            "- 6 reports through the vulnerability disclosure programme",
            "- 11 upstream advisories matched against published SBOMs",
            "",
            "## Decisions",
            "| Item | Products | Exploited? | Decision |",
            "|---|---|---|---|",
            (
                "| BusyBox DHCP client parsing flaw | Keystone 2.8.x | no | fix in "
                "2.9.0 within 30 days |"
            ),
            (
                "| OpenSSL advisory (unused cipher API) | all | no | not affected, "
                "VEX statement published |"
            ),
            (
                "| Companion app token storage (PT-02) | Android app | no | fix in next "
                "app release |"
            ),
            "| Debug UART shell on test pads | Keystone 2.8.0 | no | closed by 2.8.1 |",
            "",
            "No actively exploited vulnerability this cycle: no CRA notification due.",
        ]
    )


def _report(title, intro):
    def make(ctx, offset):
        return _pdf(title, [f"Date: {ctx.day(offset)}", "", *intro])

    return make


FILES = {
    "csv-access": _access_review_csv,
    "csv-encryption": _encryption_csv,
    "csv-scan": _scan_csv,
    "csv-asv": _asv_csv,
    "csv-badge": _badge_csv,
    "csv-plc": _plc_backup_csv,
    "csv-supplier": _supplier_csv,
    "json-logs": _log_retention_json,
    "json-ota-kelvin": _ota_report("Kelvin thermostat", "4.12.0", "4.11.3", 212000),
    "json-ota-lookout": _ota_report("Lookout camera", "3.5.1", "3.5.0", 96000),
    "json-sbom-280": _sbom("2.8.0", "1.35.0", "3.0.13"),
    "json-sbom-281": _sbom("2.8.1", "1.35.0", "3.0.14"),
    "md-tabletop": _tabletop_md,
    "md-retention": _retention_md,
    "md-ceremony": _ceremony_md,
    "md-triage": _triage_md,
    "pdf-backup": _report(
        "Backup restore test report",
        [
            "Scope: PostgreSQL primary (device cloud), store order database,",
            "Brno SCADA project files.",
            "Restore point: nightly snapshot, Kestrava Cloud secondary region.",
            "Result: device cloud database restored in 52 minutes (RTO 4 hours).",
            "Integrity: row counts and checksums matched the source.",
            "Issue: SCADA project restore needed a licence dongle re-binding.",
            "Conclusion: test passed with one observation.",
        ],
    ),
    "pdf-backup-2": _report(
        "Backup restore test report",
        [
            "Scope: PostgreSQL primary, store order database, Brno SCADA",
            "project files, firmware CI artefact store.",
            "Result: all four restores within RTO; SCADA licence step scripted.",
            "Conclusion: test passed, no observation.",
        ],
    ),
    "pdf-policy": _report(
        "Privileged access policy - signed copy",
        [
            "Version 2.1, approved by the Executive Committee.",
            "Privileged accounts are personal, MFA-protected and reviewed",
            "quarterly. Break-glass accounts are sealed and audited on use.",
            "Signing-key custodians and OT engineering accounts are in scope.",
            "Signed: Chief Information Security Officer.",
        ],
    ),
    "pdf-scope": _report(
        "ISMS scope statement",
        [
            "The ISMS covers the design, development, manufacturing and cloud",
            "operation of the Kelvin, Lookout and Keystone product lines, the",
            "companion app, the device cloud and the online store.",
            "Sites: Lyon HQ and R&D, Brno assembly plant and warehouse,",
            "Eindhoven hardware design office; hosting on Kestrava Cloud.",
            f"{PAY_ENTITY} is in scope for shared IT services only; its",
            "cardholder data environment is assessed under PCI DSS.",
            "Excluded: retail partner stores; Shenwa Contract Manufacturing",
            "(covered by supplier assurance).",
        ],
    ),
    "pdf-pentest": _report(
        "Penetration test - executive summary (Redhaven Security)",
        [
            "Targets: companion app (iOS, Android) and device cloud public API.",
            "Approach: grey box, two test accounts, one Kelvin and one Lookout.",
            "Findings: 1 high, 4 medium, 1 low, 1 informational.",
            "The high finding (broken object-level authorisation on thermostat",
            "schedules) was fixed during the test window and retested.",
        ],
    ),
}

# Each evidence: name, description, status, expiry offset, controls, lead-audit
# requirement ref_ids, revisions as (file name, content key, day offset,
# observation, link). Status follows the revisions the way a review would leave
# it: a fresh revision is "in review", nothing filed is "draft" or "missing".
EVIDENCES = [
    (
        "Quarterly access review export",
        "Brightline Identity entitlement export with the reviewers' decisions.",
        "approved",
        75,
        ("AC.001",),
        ("A.5.18", "A.8.2"),
        [
            ("Access review Q3 export.csv", "csv-access", -170, None, None),
            ("Access review Q4 export.csv", "csv-access", -80, None, None),
        ],
    ),
    (
        "Backup restore test report",
        "Results of the semi-annual restore test from the secondary region.",
        "approved",
        160,
        ("AC.003",),
        ("A.8.13",),
        [
            (
                "Backup restore test report H2.pdf",
                "pdf-backup",
                -200,
                "SCADA project restore needed a manual licence step.",
                None,
            ),
            (
                "Backup restore test report H1.pdf",
                "pdf-backup-2",
                -22,
                "All restores within RTO.",
                None,
            ),
        ],
    ),
    (
        "Privileged access policy (signed)",
        "Signed copy of the privileged access policy, version 2.1.",
        "approved",
        300,
        ("AC.001", "AC.002"),
        ("A.8.2", "A.5.15"),
        [("Privileged access policy v2.1 signed.pdf", "pdf-policy", -95, None, None)],
    ),
    (
        "Endpoint encryption compliance report",
        (
            "MDM export showing disk encryption for every laptop in Lyon, Brno and "
            "Eindhoven."
        ),
        "approved",
        30,
        ("AC.005",),
        ("A.8.1", "A.8.24"),
        [("MDM encryption status.csv", "csv-encryption", -12, None, None)],
    ),
    (
        "Incident response tabletop minutes",
        "Minutes and actions from the annual tabletop on a stolen OTA signing key.",
        "approved",
        250,
        ("AC.008",),
        ("A.5.24", "A.5.26"),
        [("IR tabletop minutes.md", "md-tabletop", -14, None, None)],
    ),
    (
        "Monthly vulnerability scan summary",
        "Severity counts per asset group from the authenticated scanner.",
        "in_review",
        20,
        ("AC.010",),
        ("A.8.8",),
        [
            ("Vulnerability scan summary.csv", "csv-scan", -35, None, None),
            (
                "Vulnerability scan summary (rescan).csv",
                "csv-scan",
                -4,
                "Rescan after the Brno OT patch window.",
                None,
            ),
        ],
    ),
    (
        "SIEM log retention configuration",
        "Retention settings exported from the log platform, IT and OT sources.",
        "approved",
        200,
        ("AC.009",),
        ("A.8.15",),
        [("siem-retention-config.json", "json-logs", -60, None, None)],
    ),
    (
        "Brno plant badge audit log",
        "Badge holders with access to restricted zones of the Brno plant.",
        "expired",
        -15,
        ("AC.012",),
        ("A.7.2",),
        [("Badge audit Brno plant.csv", "csv-badge", -190, None, None)],
    ),
    (
        "Supplier security questionnaire responses",
        "Consolidated, scored answers from critical suppliers.",
        "in_review",
        90,
        ("AC.004",),
        ("A.5.19", "A.5.21"),
        [("Supplier questionnaire responses.csv", "csv-supplier", -9, None, None)],
    ),
    (
        "Privileged session recording sample",
        "Sample of recorded admin sessions on the device cloud cluster.",
        "rejected",
        None,
        ("AC.002",),
        ("A.8.16",),
        [
            (
                "",
                None,
                -18,
                (
                    "Recordings are kept 7 days; the policy requires 90. Resubmit "
                    "once retention is fixed."
                ),
                "https://pam.corp.example/recordings/sample-2026",
            )
        ],
    ),
    (
        "Data retention schedule",
        "Retention periods per record type, pending DPO and Legal sign-off.",
        "draft",
        None,
        ("AC.011",),
        ("A.8.10", "A.5.34"),
        [("Data retention schedule draft.md", "md-retention", -6, None, None)],
    ),
    (
        "Secure firmware development training completion",
        "LMS completion report for the secure firmware development course.",
        "draft",
        None,
        ("AC.006",),
        ("A.6.3", "A.8.28"),
        [],
    ),
    (
        "IT/OT network segmentation diagram",
        (
            "Current-state zones and conduits between the Brno office LAN, SCADA and "
            "the assembly cells."
        ),
        "missing",
        None,
        ("AC.007",),
        ("A.8.22",),
        [],
    ),
    (
        "ISMS scope statement",
        "Approved scope of the information security management system.",
        "approved",
        330,
        (),
        ("4.3",),
        [("ISMS scope statement.pdf", "pdf-scope", -120, None, None)],
    ),
    (
        "Companion app and device cloud penetration test report",
        "Redhaven Security executive summary of the 2026 grey-box test.",
        "in_review",
        None,
        ("AC.010",),
        ("A.8.8", "A.8.29"),
        [("Pentest executive summary.pdf", "pdf-pentest", -25, None, None)],
    ),
    (
        "OTA staged rollout report",
        "Ring-by-ring install results for the latest firmware releases.",
        "approved",
        120,
        ("AC.013", "AC.014"),
        ("A.8.32",),
        [
            ("Kelvin 4.12.0 rollout report.json", "json-ota-kelvin", -48, None, None),
            (
                "Lookout 3.5.1 rollout report.json",
                "json-ota-lookout",
                -11,
                "Ring 2 paused for 24 hours on a Wi-Fi reconnect regression.",
                None,
            ),
        ],
    ),
    (
        "Keystone hub firmware SBOM",
        "CycloneDX SBOM published with each Keystone hub firmware release.",
        "approved",
        None,
        ("AC.015",),
        ("A.5.21", "A.8.28"),
        [
            ("keystone-hub-2.8.0.cdx.json", "json-sbom-280", -64, None, None),
            (
                "keystone-hub-2.8.1.cdx.json",
                "json-sbom-281",
                -16,
                "OpenSSL bumped; BusyBox update scheduled for 2.9.0.",
                None,
            ),
        ],
    ),
    (
        "PCI DSS ASV quarterly scan summary",
        f"External ASV scan of the {PAY_ENTITY} internet-facing components.",
        "in_review",
        85,
        ("AC.016", "AC.010"),
        ("A.8.8",),
        [("ASV scan summary.csv", "csv-asv", -7, None, None)],
    ),
    (
        "OTA signing-key ceremony checklist",
        "Monthly custodian check of the firmware signing HSM and its usage log.",
        "approved",
        25,
        ("AC.013",),
        ("A.8.24",),
        [("Signing-key ceremony check.md", "md-ceremony", -5, None, None)],
    ),
    (
        "PLC backup verification log",
        "Monthly check that every assembly cell PLC program has a verified backup.",
        "approved",
        28,
        ("AC.017", "AC.003"),
        ("A.8.13", "A.8.32"),
        [("PLC backup verification.csv", "csv-plc", -3, None, None)],
    ),
    (
        "CRA vulnerability triage review minutes",
        "PSIRT decisions on reported and SBOM-matched vulnerabilities.",
        "in_review",
        None,
        ("AC.010", "AC.015"),
        ("A.8.8",),
        [("CRA triage review.md", "md-triage", -10, None, None)],
    ),
]

# Evidences filed straight on audits, by audit ref_id.
AUDIT_EVIDENCES = {
    "AUD.2026.01": (
        "ISMS scope statement",
        "Privileged access policy (signed)",
        "Companion app and device cloud penetration test report",
    ),
    "AUD.2025.04": ("Brno plant badge audit log", "PLC backup verification log"),
    "AUD.2026.03": (
        "PCI DSS ASV quarterly scan summary",
        "Privileged access policy (signed)",
        "Quarterly access review export",
    ),
    "AUD.2026.04": (
        "PLC backup verification log",
        "Brno plant badge audit log",
        "IT/OT network segmentation diagram",
    ),
    "AUD.2026.05": (
        "Keystone hub firmware SBOM",
        "CRA vulnerability triage review minutes",
        "OTA staged rollout report",
        "OTA signing-key ceremony checklist",
    ),
    "AUD.2026.06": (
        "Incident response tabletop minutes",
        "Supplier security questionnaire responses",
    ),
}

# Recurring tasks: ref, name, description, schedule, start offset, controls,
# evidences (expected), state of the latest past occurrence ("completed",
# "in_progress" or "pending" when overdue), its observation, linked audit.
RECURRING_TASKS = [
    (
        "TSK.001",
        "Quarterly access review",
        (
            "Reviewers confirm or revoke entitlements on in-scope systems, including "
            "signing-key custodians and OT engineering accounts."
        ),
        {"frequency": "MONTHLY", "interval": 3},
        -275,
        ("AC.001",),
        ("Quarterly access review export",),
        "in_progress",
        "Started, waiting on the Payments and Plant engineering reviewers.",
        "AUD.2026.01",
    ),
    (
        "TSK.002",
        "Monthly vulnerability scan review",
        "Triage the scanner report, open findings for anything high or critical.",
        {"frequency": "MONTHLY", "interval": 1},
        -155,
        ("AC.010",),
        ("Monthly vulnerability scan summary",),
        "completed",
        None,
        None,
    ),
    (
        "TSK.003",
        "Weekly backup job verification",
        (
            "Check last week's backup jobs (device cloud, store, SCADA) and "
            "investigate any failure."
        ),
        {"frequency": "WEEKLY", "interval": 1},
        -45,
        ("AC.003",),
        (),
        "pending",
        None,
        None,
    ),
    (
        "TSK.004",
        "Semi-annual backup restore test",
        (
            "Restore the device cloud database, store orders and SCADA projects from "
            "the secondary region and time it."
        ),
        {"frequency": "MONTHLY", "interval": 6},
        -200,
        ("AC.003",),
        ("Backup restore test report",),
        "completed",
        None,
        None,
    ),
    (
        "TSK.005",
        "Annual incident response tabletop",
        "Run a tabletop with the crisis cell and the PSIRT on a current scenario.",
        {"frequency": "YEARLY", "interval": 1},
        -14,
        ("AC.008",),
        ("Incident response tabletop minutes",),
        "completed",
        None,
        "AUD.2026.06",
    ),
    (
        "TSK.006",
        "Quarterly plant badge access audit",
        (
            "Reconcile Brno restricted-zone badge holders against HR, temp agency and "
            "integrator lists."
        ),
        {"frequency": "MONTHLY", "interval": 3},
        -190,
        ("AC.012",),
        ("Brno plant badge audit log",),
        "pending",
        None,
        "AUD.2026.04",
    ),
    (
        "TSK.007",
        "Monthly OTA signing-key ceremony check",
        "Two custodians verify HSM seals, the signing log and the backup token.",
        {"frequency": "MONTHLY", "interval": 1},
        -150,
        ("AC.013",),
        ("OTA signing-key ceremony checklist",),
        "completed",
        None,
        "AUD.2026.05",
    ),
    (
        "TSK.008",
        "Monthly PLC backup verification",
        (
            "Export every assembly cell PLC program, compare hashes, refresh the "
            "offline copy."
        ),
        {"frequency": "MONTHLY", "interval": 1},
        -120,
        ("AC.017", "AC.003"),
        ("PLC backup verification log",),
        "completed",
        None,
        "AUD.2026.04",
    ),
    (
        "TSK.009",
        "Quarterly PCI DSS ASV scan",
        (
            f"External ASV scan of the {PAY_ENTITY} internet-facing components; "
            "rescan until a passing report is issued."
        ),
        {"frequency": "MONTHLY", "interval": 3},
        -260,
        ("AC.016", "AC.010"),
        ("PCI DSS ASV quarterly scan summary",),
        "completed",
        None,
        "AUD.2026.03",
    ),
    (
        "TSK.010",
        "Fortnightly CRA vulnerability triage review",
        (
            "PSIRT reviews disclosure reports and SBOM-matched advisories, decides "
            "fixes and whether a CRA notification is due."
        ),
        {"frequency": "WEEKLY", "interval": 2},
        -84,
        ("AC.010", "AC.015"),
        ("CRA vulnerability triage review minutes",),
        "in_progress",
        "Two advisories still waiting on the Keystone firmware lead.",
        "AUD.2026.05",
    ),
    (
        "TSK.011",
        "Semi-annual critical supplier reassessment",
        (
            "Send the security questionnaire to critical suppliers, score the answers "
            "and follow up on gaps."
        ),
        {"frequency": "MONTHLY", "interval": 6},
        -300,
        ("AC.004",),
        ("Supplier security questionnaire responses",),
        "in_progress",
        "Linterra Automation and Mireo Support answers still outstanding.",
        "AUD.2026.06",
    ),
]

OBSERVATIONS = [
    "Done, no exception raised.",
    "Completed; two stale entries cleaned up.",
    "Done. Evidence filed.",
    "Completed with one follow-up ticket opened.",
]

# One-off tasks: ref, name, description, date offset, status, observation,
# controls, linked audit ref_id.
ONE_OFF_TASKS = [
    (
        "TSK.101",
        "Renew TLS certificates for the store and device cloud API",
        (
            "Wildcard certificates expire soon; renew and deploy to the edge and the "
            "MQTT gateway."
        ),
        12,
        "pending",
        None,
        ("AC.010",),
        None,
    ),
    (
        "TSK.102",
        "Decommission the legacy Kelvin v1 firmware mirror",
        "Last v1 thermostats moved to signed OTA; shut down the HTTP-only mirror.",
        -20,
        "completed",
        "Host wiped, DNS record removed, firewall rule deleted.",
        ("AC.013", "AC.014"),
        None,
    ),
    (
        "TSK.103",
        "Rotate firmware CI deployment credentials",
        (
            "Rotate the build farm's registry and signing-request tokens after a "
            "contractor offboarding."
        ),
        -5,
        "in_progress",
        "Registry token rotated; signing-request token pending custodian quorum.",
        ("AC.001", "AC.013"),
        None,
    ),
    (
        "TSK.104",
        "Assemble the ISO 27001 certification audit evidence pack",
        "Collect and index the evidences Vantor Legal & Audit asked for.",
        30,
        "pending",
        None,
        (),
        "AUD.2026.01",
    ),
    (
        "TSK.105",
        "Review supplier SOC 2 reports",
        "Read the bridge letters and carve-outs for critical suppliers.",
        -40,
        "cancelled",
        "Replaced by the supplier questionnaire campaign.",
        ("AC.004",),
        None,
    ),
    (
        "TSK.106",
        "Run phishing simulation for firmware engineering",
        "Targeted simulation following the phishing of a firmware engineer.",
        21,
        "pending",
        None,
        ("AC.006",),
        None,
    ),
    (
        "TSK.107",
        "Publish the Keystone hub v3 support period and security contact",
        (
            "State the security update support period on the product page and the "
            "box, and publish security.txt for the disclosure programme."
        ),
        45,
        "pending",
        None,
        ("AC.010",),
        "AUD.2026.05",
    ),
    (
        "TSK.108",
        "Enforce MFA on Linterra Automation remote access",
        (
            "Move integrator sessions to the vendor access broker with MFA and "
            "session recording."
        ),
        -3,
        "in_progress",
        "Broker deployed in Brno; Linterra accounts enrolled, MFA not yet enforced.",
        ("AC.007",),
        "AUD.2026.04",
    ),
    (
        "TSK.109",
        "Replace shared PLC engineering passwords",
        (
            "Give every integrator and engineer a named account on the engineering "
            "workstations and PLCs."
        ),
        -12,
        "completed",
        "Named accounts on all cells; the shared password is disabled.",
        ("AC.017",),
        "AUD.2026.04",
    ),
    (
        "TSK.110",
        "Rehearse the CRA 24-hour early warning",
        (
            "Dry run of an actively exploited vulnerability notification to the CSIRT "
            "and the ENISA single reporting platform."
        ),
        40,
        "pending",
        None,
        ("AC.008", "AC.010"),
        "AUD.2026.05",
    ),
]


@register
class EvidenceBuilder(DemoBuilder):
    """Evidences with attachments, and the tasks that produce them."""

    name = "evidence"
    depends = ("core", "compliance")
    covers: ClassVar[dict] = {
        Evidence: "folder",
        EvidenceRevision: "folder",
        TaskTemplate: "folder",
        TaskNode: "folder",
    }

    def stamps(self, ctx):
        scope = {"folder__in": ctx.folders()}
        return [
            (Evidence, scope, ("name",)),
            (EvidenceRevision, scope, ("evidence__name", "version")),
            (TaskTemplate, scope, ("name",)),
            (TaskNode, scope, ("task_template__name", "due_date")),
        ]

    def build(self, ctx):
        evidences = self.build_evidences(ctx)
        self.build_tasks(ctx, evidences)
        ctx.out(f"{len(evidences)} evidences, {len(RECURRING_TASKS)} recurring tasks")

    def build_evidences(self, ctx):
        requirements = _lead_requirements(ctx)
        evidences = {}
        for (
            name,
            description,
            status,
            expiry,
            controls,
            requirement_refs,
            revisions,
        ) in EVIDENCES:
            evidence, created = Evidence.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "description": description,
                    "status": status,
                    "expiry_date": ctx.day(expiry) if expiry is not None else None,
                },
            )
            if created:
                for version, (filename, key, offset, observation, link) in enumerate(
                    revisions, start=1
                ):
                    revision = EvidenceRevision(
                        evidence=evidence,
                        version=version,
                        observation=observation,
                        link=link,
                    )
                    if key:
                        revision.attachment = ContentFile(
                            FILES[key](ctx, offset), name=filename
                        )
                    revision.save()
            for control in _controls(ctx, controls):
                control.evidences.add(evidence)
            for ref in requirement_refs:
                if ref in requirements:
                    requirements[ref].evidences.add(evidence)
            evidences[name] = evidence
        audits = _audits(ctx)
        for audit_ref, names in AUDIT_EVIDENCES.items():
            if audit_ref in audits:
                audits[audit_ref].evidences.add(*(evidences[n] for n in names))
        return evidences

    def build_tasks(self, ctx, evidences):
        audits = _audits(ctx)
        for (
            ref_id,
            name,
            description,
            schedule,
            start,
            controls,
            expected,
            latest,
            note,
            audit_ref,
        ) in RECURRING_TASKS:
            template, created = TaskTemplate.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "description": description,
                    "is_recurrent": True,
                    "schedule": dict(schedule, overdue_behavior="NO_IMPACT"),
                    "task_date": ctx.day(start),
                },
            )
            if created:
                template.applied_controls.set(_controls(ctx, controls))
                template.evidences.set([evidences[n] for n in expected])
                if audit_ref in audits:
                    template.compliance_assessments.set([audits[audit_ref]])
            self.materialize(
                ctx, template, latest, note, [evidences[n] for n in expected]
            )

        for (
            ref_id,
            name,
            description,
            offset,
            status,
            observation,
            controls,
            audit_ref,
        ) in ONE_OFF_TASKS:
            template, created = TaskTemplate.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "description": description,
                    "is_recurrent": False,
                    "task_date": ctx.day(offset),
                },
            )
            if created:
                template.applied_controls.set(_controls(ctx, controls))
                if audit_ref in audits:
                    template.compliance_assessments.set([audits[audit_ref]])
            # The serializer opens the single occurrence of a one-off task.
            TaskNode.objects.get_or_create(
                task_template=template,
                due_date=template.task_date,
                defaults={
                    "scheduled_date": template.task_date,
                    "status": status,
                    "observation": observation,
                    "folder": template.folder,
                },
            )

        # File each evidence's revisions against the occurrences that produced
        # them, newest revision on the newest completed occurrence.
        for _, name, *_rest, expected, _latest, _note, _audit in RECURRING_TASKS:
            if len(expected) != 1:
                continue
            template = TaskTemplate.objects.get(name=name, folder=ctx.domain)
            done = list(
                TaskNode.objects.filter(
                    task_template=template, status="completed"
                ).order_by("-due_date")
            )
            revisions = list(
                EvidenceRevision.objects.filter(
                    evidence=evidences[expected[0]]
                ).order_by("-version")
            )
            for revision, node in zip(revisions, done):
                if revision.task_node_id != node.id:
                    revision.task_node = node
                    revision.save(update_fields=["task_node"])

    def materialize(self, ctx, template, latest, note, expected):
        """Occurrences from the start date to three months ahead, as the
        calendar materializes them, with past ones carried out."""
        dates = [
            occurrence["due_date"]
            for occurrence in _generate_occurrences(
                template, template.task_date, ctx.day(90)
            )
        ]
        past = [d for d in dates if d < ctx.anchor]
        for index, due in enumerate(dates):
            if due >= ctx.anchor:
                status, observation = "pending", None
            elif due == past[-1] and latest != "completed":
                status, observation = latest, note
            else:
                status, observation = (
                    "completed",
                    OBSERVATIONS[index % len(OBSERVATIONS)],
                )
            node, created = TaskNode.objects.get_or_create(
                task_template=template,
                due_date=due,
                defaults={
                    "scheduled_date": due,
                    "status": status,
                    "observation": observation,
                    "folder": template.folder,
                },
            )
            if created and status == "completed" and expected:
                node.evidences.set(expected)


# ---------------------------------------------------------------------------
# Findings, vulnerabilities, exceptions, acceptances
# ---------------------------------------------------------------------------

# ref, name, category, status, perimeter ref, start, reported, due, budget,
# expenses, linked audit ref_id, description, objectives.
FOLLOW_UPS = [
    (
        "FA.2026.01",
        "2026 penetration test — companion app and device cloud API",
        "pentest",
        "in_progress",
        "PER.001",
        -45,
        -25,
        60,
        "32000.00",
        "32000.00",
        None,
        (
            "Grey-box test by Redhaven Security of the iOS and Android companion "
            "app and the device cloud public API."
        ),
        "Find exploitable weaknesses before the Keystone hub v3 launch; retest fixes.",
    ),
    (
        "FA.2026.02",
        "ISO 27001 internal audit follow-up",
        "audit",
        "in_progress",
        None,
        -60,
        -30,
        40,
        "6500.00",
        "4200.00",
        "AUD.2026.01",
        "Non-conformities and observations raised by the internal audit.",
        "Close every major non-conformity before the certification audit.",
    ),
    (
        "FA.2025.07",
        "Q4 2025 threat hunt — ransomware precursors in IT and OT",
        "threat_hunting",
        "done",
        "PER.003",
        -140,
        -110,
        -90,
        None,
        None,
        None,
        (
            "Hypothesis-driven hunt for initial access and staging behaviours on "
            "corporate endpoints and the Brno plant office LAN."
        ),
        "Confirm no active intrusion; improve detection coverage.",
    ),
    (
        "FA.2026.03",
        "Vulnerability disclosure programme reports",
        "responsible_disclosure",
        "in_progress",
        "PER.001",
        -100,
        -3,
        None,
        None,
        None,
        "AUD.2026.05",
        (
            "Reports received through security.txt and the product security inbox, "
            "triaged by the PSIRT."
        ),
        None,
    ),
    (
        "FA.2026.04",
        "Brno plant IEC 62443 walkthrough",
        "self_identified",
        "in_progress",
        "PER.003",
        -20,
        -8,
        75,
        "3000.00",
        "1800.00",
        "AUD.2026.04",
        (
            "On-site review of the assembly cells, SCADA, engineering workstations "
            "and integrator remote access."
        ),
        "Baseline the OT exposure against IEC 62443-3-3 before the line 4 retrofit.",
    ),
    (
        "FA.2026.05",
        f"PCI DSS pre-assessment — {PAY_ENTITY}",
        "audit",
        "in_progress",
        "PER.002",
        -35,
        -21,
        50,
        "14000.00",
        "9500.00",
        "AUD.2026.03",
        (
            "Gap review by the Vantor Legal & Audit QSA ahead of the PCI DSS 4.0.1 "
            "report on compliance."
        ),
        "Close the gaps on payment page scripts and CDE segmentation before the ROC.",
    ),
    (
        "FA.2026.06",
        "Keystone hub v3 pre-release penetration test",
        "pentest",
        "planned",
        "PER.004",
        20,
        None,
        80,
        "24000.00",
        None,
        "AUD.2026.05",
        (
            "Hardware, firmware and Matter/Thread commissioning test of the hub v3 "
            "engineering samples."
        ),
        "No high finding open at release, as the CRA conformity file requires.",
    ),
]

# follow-up, ref, name, severity, status, priority, controls, asset,
# lead-audit requirement, eta, due, observation, recommendation, vulnerabilities.
FINDINGS = [
    (
        "FA.2026.01",
        "PT-01",
        "Device cloud API lets a user read another account's thermostat schedule",
        3,
        "resolved",
        1,
        ("AC.010",),
        "Customer and device accounts",
        None,
        -30,
        -28,
        (
            "Changing the device id in /v2/devices/{id}/schedule returned another "
            "household's Kelvin schedule."
        ),
        "Enforce ownership checks server side on every device endpoint.",
        (),
    ),
    (
        "FA.2026.01",
        "PT-02",
        "Android companion app stores the refresh token in plain text",
        2,
        "in_progress",
        2,
        (),
        "Companion mobile app",
        None,
        10,
        20,
        "The refresh token sits unencrypted in shared preferences on rooted devices.",
        "Store tokens in the Android Keystore and shorten their lifetime.",
        (),
    ),
    (
        "FA.2026.01",
        "PT-03",
        "Verbose stack traces on device cloud API errors",
        2,
        "confirmed",
        3,
        (),
        "Device cloud Kubernetes cluster",
        None,
        25,
        45,
        "Unhandled exceptions return framework stack traces and library versions.",
        "Return generic error bodies; log details server side only.",
        ("VUL.006",),
    ),
    (
        "FA.2026.01",
        "PT-04",
        "No rate limiting on the companion app login endpoint",
        2,
        "assigned",
        2,
        ("AC.001",),
        "Customer and device accounts",
        None,
        15,
        30,
        "Thousands of login attempts per minute were accepted without throttling.",
        "Add per-IP and per-account throttling; alert on spikes.",
        (),
    ),
    (
        "FA.2026.01",
        "PT-05",
        "Analytics SDK bundles an outdated WebView component",
        1,
        "identified",
        4,
        (),
        "Companion mobile app",
        None,
        None,
        90,
        "The Fennick Analytics SDK ships a WebView helper with known XSS issues.",
        "Upgrade the SDK or disable its in-app message feature.",
        ("VUL.007",),
    ),
    (
        "FA.2026.01",
        "PT-06",
        "MQTT gateway banner discloses broker version",
        0,
        "dismissed",
        None,
        (),
        "MQTT device gateway",
        None,
        None,
        None,
        "The MQTT gateway returns its broker name and version on connect.",
        "Accepted as informational; devices authenticate with client certificates.",
        (),
    ),
    (
        "FA.2026.01",
        "PT-07",
        "iOS companion app does not pin the device cloud certificate",
        2,
        "identified",
        3,
        (),
        "Companion mobile app",
        None,
        None,
        60,
        "A user-installed root CA lets a proxy read pairing traffic.",
        "Pin the device cloud public keys, with a backup pin.",
        (),
    ),
    (
        "FA.2026.02",
        "NC-01",
        "Access reviews not evidenced for two quarters",
        3,
        "in_progress",
        1,
        ("AC.001",),
        None,
        "A.5.18",
        5,
        25,
        (
            "No signed review records for Q2 and Q3 on the store admin console and the "
            "firmware CI build farm."
        ),
        "Run the review from Brightline Identity and file the exports as evidence.",
        (),
    ),
    (
        "FA.2026.02",
        "NC-02",
        "Supplier security requirements missing from contracts",
        3,
        "assigned",
        1,
        ("AC.004",),
        None,
        "A.5.20",
        30,
        40,
        (
            "The Shenwa Contract Manufacturing, Linterra Automation and Fennick "
            "Analytics contracts have no security clauses."
        ),
        "Add the standard security annex at the next renewal.",
        (),
    ),
    (
        "FA.2026.02",
        "OBS-01",
        "Training records incomplete for Brno temporary staff",
        1,
        "identified",
        3,
        ("AC.006",),
        None,
        "A.6.3",
        None,
        60,
        (
            "Temp agency workers are not enrolled in the LMS, so completion cannot be "
            "shown."
        ),
        "Enrol them or keep signed attendance sheets from the induction.",
        (),
    ),
    (
        "FA.2026.02",
        "NC-03",
        "IT/OT segmentation review overdue",
        2,
        "confirmed",
        2,
        ("AC.007",),
        "Corporate VPN gateway",
        "A.8.22",
        45,
        60,
        "The annual segmentation review planned for last year did not take place.",
        "Schedule the review and publish the zone and conduit diagram.",
        (),
    ),
    (
        "FA.2026.02",
        "NC-04",
        "Signing-key custodian list out of date",
        2,
        "assigned",
        2,
        ("AC.013",),
        "Firmware signing HSM",
        "A.8.24",
        10,
        30,
        "One custodian left the company four months ago and is still listed.",
        "Update the custodian register at every joiner/leaver event.",
        (),
    ),
    (
        "FA.2025.07",
        "TH-01",
        "Dormant admin account used from a new country",
        4,
        "closed",
        1,
        ("AC.001", "AC.002"),
        "Workforce identity provider",
        None,
        -118,
        -115,
        "An admin account disabled in HR authenticated from an unfamiliar network.",
        "Account disabled; the joiner-mover-leaver sync now runs hourly.",
        (),
    ),
    (
        "FA.2025.07",
        "TH-02",
        "PowerShell download cradles on two plant engineering workstations",
        3,
        "mitigated",
        2,
        ("AC.005", "AC.007"),
        "Production line control",
        None,
        -100,
        -95,
        (
            "Encoded PowerShell fetching remote scripts, traced to an integrator's "
            "maintenance script."
        ),
        "Block encoded PowerShell via ASR rules; keep the EDR detection.",
        (),
    ),
    (
        "FA.2025.07",
        "TH-03",
        "Gaps in VPN log forwarding",
        2,
        "resolved",
        3,
        ("AC.009",),
        "Corporate VPN gateway",
        None,
        -95,
        -90,
        "VPN logs stopped reaching the SIEM for 9 days after a certificate change.",
        "Alert when a log source goes silent for more than 4 hours.",
        (),
    ),
    (
        "FA.2026.03",
        "RD-01",
        "Password reset token valid after use",
        3,
        "in_progress",
        1,
        (),
        "Customer and device accounts",
        None,
        7,
        14,
        "A researcher reused a companion app reset link twice within its validity.",
        "Invalidate the token on first use and shorten its lifetime.",
        (),
    ),
    (
        "FA.2026.03",
        "RD-02",
        "Open redirect on the online store logout endpoint",
        1,
        "identified",
        3,
        (),
        "Online store web front",
        None,
        None,
        45,
        "The next parameter accepts arbitrary external URLs.",
        "Allow-list redirect targets.",
        (),
    ),
    (
        "FA.2026.03",
        "RD-03",
        "Lookout clip links can be enumerated without authorisation",
        4,
        "resolved",
        1,
        ("AC.010",),
        "Customer and device accounts",
        None,
        -27,
        -26,
        (
            "Clip download links used sequential ids and the CDN did not check the "
            "session; see INC.2026.006."
        ),
        "Signed, expiring links bound to the account; authorisation at the CDN.",
        ("VUL.011",),
    ),
    (
        "FA.2026.03",
        "RD-04",
        "Root shell on Keystone hub debug UART",
        2,
        "mitigated",
        2,
        ("AC.018",),
        "Device firmware and signing keys",
        None,
        -16,
        -10,
        "Test pads expose a root console on production hubs; physical access needed.",
        "Disable the console in production builds; fuse it at end-of-line test.",
        ("VUL.012",),
    ),
    (
        "FA.2026.04",
        "OT-01",
        "Flat network between the plant office LAN and the assembly cells",
        4,
        "confirmed",
        1,
        ("AC.007",),
        "Assembly cell PLCs",
        None,
        60,
        75,
        (
            "Office workstations reach PLCs on cells 1 to 4 directly; no conduit or "
            "firewall between zones."
        ),
        "Create cell zones with an industrial firewall and an OT DMZ for SCADA.",
        (),
    ),
    (
        "FA.2026.04",
        "OT-02",
        "One shared PLC engineering password for all integrators",
        3,
        "resolved",
        1,
        ("AC.017",),
        "Assembly cell PLCs",
        None,
        -12,
        -10,
        "The same password, unchanged since commissioning, unlocks every cell.",
        "Named accounts per engineer and integrator; disable the shared password.",
        ("VUL.002",),
    ),
    (
        "FA.2026.04",
        "OT-03",
        "Linterra Automation remote access without MFA",
        3,
        "in_progress",
        1,
        ("AC.007",),
        "Plant SCADA server",
        None,
        14,
        30,
        "Integrator connects through a standing VPN account with a password only.",
        "Vendor access broker with MFA, approval and session recording.",
        (),
    ),
    (
        "FA.2026.04",
        "OT-04",
        "SCADA server runs an unsupported operating system",
        3,
        "confirmed",
        2,
        ("AC.007",),
        "Plant SCADA server",
        None,
        None,
        120,
        "The SCADA vendor does not support a newer OS until the line 4 retrofit.",
        "Isolate the server and cover it with a time-boxed security exception.",
        ("VUL.003",),
    ),
    (
        "FA.2026.04",
        "OT-05",
        "No offline copy of PLC programs",
        2,
        "resolved",
        3,
        ("AC.017", "AC.003"),
        "Production line control",
        None,
        -6,
        -5,
        "Programs existed only on the engineering workstation.",
        "Monthly export and hash check, offline copy in the plant safe.",
        (),
    ),
    (
        "FA.2026.05",
        "PCI-01",
        "Payment page scripts not inventoried or authorised",
        3,
        "in_progress",
        1,
        ("AC.016",),
        "Online store web front",
        None,
        20,
        35,
        (
            "Twelve third-party scripts load on the checkout page; no inventory or "
            "justification exists (PCI DSS 6.4.3)."
        ),
        "Inventory and justify each script; enforce a content security policy.",
        (),
    ),
    (
        "FA.2026.05",
        "PCI-02",
        "No change and tamper detection on the checkout page",
        3,
        "identified",
        1,
        ("AC.016",),
        "Store checkout and payments",
        None,
        None,
        45,
        (
            "Nothing alerts on unauthorised changes to payment page headers or scripts "
            "(PCI DSS 11.6.1)."
        ),
        "Deploy page integrity monitoring with weekly alert review.",
        (),
    ),
    (
        "FA.2026.05",
        "PCI-03",
        "CDE segmentation not retested after a network change",
        3,
        "assigned",
        2,
        ("AC.016",),
        "Store checkout and payments",
        None,
        25,
        40,
        "A new Kestrava Cloud peering was added without a segmentation test.",
        "Run the segmentation penetration test and retest after every change.",
        (),
    ),
    (
        "FA.2026.05",
        "PCI-04",
        "One quarterly internal vulnerability scan missing",
        2,
        "confirmed",
        3,
        ("AC.010",),
        "Store checkout and payments",
        None,
        10,
        20,
        "No internal scan of the CDE for the third quarter of last year.",
        "Schedule internal scans with the ASV calendar and file the reports.",
        (),
    ),
]

# ref, name, severity, status, assets, controls, detected, due,
# eta, description.
VULNERABILITIES = [
    (
        "VUL.001",
        "OpenSSH regreSSHion (CVE-2024-6387) on bastion hosts",
        4,
        "fixed",
        ("Corporate VPN gateway",),
        ("AC.010",),
        -150,
        -143,
        -144,
        "Signal handler race in sshd allowing unauthenticated remote code execution.",
    ),
    (
        "VUL.002",
        "Assembly cell PLCs accept a shared engineering password",
        4,
        "mitigated",
        ("Assembly cell PLCs", "Production line control"),
        ("AC.017", "AC.007"),
        -40,
        20,
        35,
        (
            "Cell PLCs also keep a vendor maintenance account that cannot be "
            "disabled; reachable from the plant office LAN."
        ),
    ),
    (
        "VUL.003",
        "Unsupported operating system on the plant SCADA server",
        3,
        "mitigated",
        ("Plant SCADA server",),
        ("AC.007",),
        -90,
        30,
        60,
        (
            "The SCADA server runs an OS out of vendor support; isolated in its own "
            "VLAN until the line 4 retrofit."
        ),
    ),
    (
        "VUL.004",
        "PostgreSQL minor version behind security release",
        2,
        "potential",
        ("PostgreSQL primary",),
        ("AC.010",),
        -10,
        50,
        21,
        "The device cloud primary runs a minor release missing two security fixes.",
    ),
    (
        "VUL.005",
        "Kubernetes API server reachable from the corporate network",
        3,
        "exploitable",
        ("Device cloud Kubernetes cluster",),
        ("AC.007",),
        -28,
        2,
        5,
        "The device cloud control plane is not restricted to the admin subnet.",
    ),
    (
        "VUL.006",
        "Framework debug mode leaks stack traces on the device cloud API",
        2,
        "fixed",
        ("Device cloud Kubernetes cluster",),
        (),
        -25,
        5,
        -2,
        "Raised by the penetration test; production now runs with debug off.",
    ),
    (
        "VUL.007",
        "Outdated WebView helper in the companion app analytics SDK",
        1,
        "potential",
        ("Companion mobile app",),
        (),
        -25,
        90,
        None,
        "Only reachable through the SDK's in-app messages, which are disabled.",
    ),
    (
        "VUL.008",
        "Firmware CI plugin with arbitrary file read",
        3,
        "mitigated",
        ("Firmware CI build farm",),
        ("AC.010", "AC.013"),
        -60,
        -30,
        -31,
        (
            "Plugin upgrade blocked by a pipeline dependency; access restricted to "
            "the build VPN and signing requests need a custodian approval."
        ),
    ),
    (
        "VUL.009",
        "Self-signed certificate on Brno warehouse label printers",
        0,
        "not_exploitable",
        (),
        (),
        -70,
        None,
        None,
        "Printers are on an isolated segment with no management exposure.",
    ),
    (
        "VUL.010",
        "Public listing flagged on the S3 evidence bucket",
        2,
        "unaffected",
        ("S3 evidence bucket",),
        (),
        -15,
        None,
        None,
        (
            "Scanner flagged the evidence bucket by name; it is object-locked and "
            "private, the public one belongs to a marketing account."
        ),
    ),
    (
        "VUL.011",
        "Lookout clip links predictable and not authorised",
        4,
        "fixed",
        ("Customer and device accounts", "Device cloud Kubernetes cluster"),
        ("AC.010",),
        -31,
        -29,
        -29,
        (
            "Sequential clip ids and a CDN rule without session check let anyone "
            "download clips; actively exploited before the fix (INC.2026.006)."
        ),
    ),
    (
        "VUL.012",
        "Debug UART root shell on Keystone hub production units",
        2,
        "mitigated",
        ("Device firmware and signing keys",),
        ("AC.018",),
        -18,
        30,
        20,
        (
            "Needs physical access to test pads. Disabled in firmware 2.8.1; units "
            "built from now on have the console fused at end-of-line test."
        ),
    ),
    (
        "VUL.013",
        "Outdated BusyBox DHCP client in Keystone hub firmware",
        3,
        "exploitable",
        ("Device firmware and signing keys",),
        ("AC.015", "AC.010"),
        -12,
        25,
        18,
        (
            "Found by matching the 2.8.x SBOM: a malformed DHCP option from the "
            "home LAN can crash or take over the hub. Fix ships in 2.9.0."
        ),
    ),
    (
        "VUL.014",
        "Shared commissioning code on one Keystone hub production batch",
        3,
        "mitigated",
        ("Device firmware and signing keys",),
        ("AC.018",),
        -45,
        -10,
        -14,
        (
            "A provisioning script error gave one batch of 1,800 hubs the same "
            "Matter setup code; an OTA update rotated it on every online unit."
        ),
    ),
]

# ref, name, severity, status, expiration, assets, controls, lead-audit
# requirements, vulnerabilities, risk scenarios, description, observation.
EXCEPTIONS = [
    (
        "EXC.001",
        "Legacy SCADA server OS kept until the line 4 retrofit",
        3,
        "approved",
        120,
        ("Plant SCADA server",),
        ("AC.007",),
        ("A.8.8",),
        ("VUL.003",),
        ("RS.01",),
        "The SCADA vendor certifies a newer OS only with the retrofit in Q3.",
        (
            "Compensating controls: dedicated VLAN, application allow-listing, no "
            "internet egress, offline backups."
        ),
    ),
    (
        "EXC.002",
        "PLC vendor maintenance account cannot be disabled",
        4,
        "in_review",
        180,
        ("Assembly cell PLCs",),
        ("AC.007", "AC.017"),
        ("A.8.5",),
        ("VUL.002",),
        ("RS.08",),
        "The PLC vendor confirms no firmware fix before next year.",
        "Proposed: vendor access broker with MFA as the only path to the cells.",
    ),
    (
        "EXC.003",
        "Firmware CI plugin upgrade deferred",
        2,
        "approved",
        30,
        ("Firmware CI build farm",),
        ("AC.010",),
        (),
        ("VUL.008",),
        ("RS.04",),
        "A pipeline dependency blocks the upgrade until the build migration.",
        None,
    ),
    (
        "EXC.004",
        "Session recording retention below policy",
        2,
        "draft",
        90,
        ("Device cloud Kubernetes cluster",),
        ("AC.002",),
        ("A.8.15",),
        (),
        ("RS.05",),
        "The PAM licence caps recordings at 7 days; the upgrade is budgeted next year.",
        None,
    ),
    (
        "EXC.005",
        "HTTP firmware mirror for Kelvin v1 thermostats",
        1,
        "resolved",
        -20,
        ("Device firmware and signing keys",),
        ("AC.013", "AC.014"),
        (),
        (),
        ("RS.07",),
        (
            "Kept an HTTP-only mirror (images still signed) for v1 thermostats until "
            "they moved to OTA."
        ),
        "Closed when the mirror was decommissioned.",
    ),
    (
        "EXC.006",
        "Shared engineering account on the Brno SCADA HMI",
        3,
        "expired",
        -10,
        ("Production line control",),
        ("AC.001", "AC.017"),
        ("A.5.16",),
        (),
        ("RS.01",),
        "Temporary shared account during the HMI migration.",
        "Expired; the owner was asked to confirm the account is gone.",
    ),
    (
        "EXC.007",
        "TLS 1.1 on checkout for a retail partner's payment terminal",
        2,
        "rejected",
        None,
        ("Store checkout and payments",),
        ("AC.016",),
        (),
        (),
        ("RS.09",),
        "Request to keep TLS 1.1 enabled for one partner terminal model.",
        "Rejected: PCI DSS forbids it; the partner must upgrade.",
    ),
    (
        "EXC.008",
        "Linterra Automation remote access pending MFA",
        3,
        "approved",
        45,
        ("Plant SCADA server", "Assembly cell PLCs"),
        ("AC.007",),
        ("A.8.5", "A.5.19"),
        (),
        ("RS.08",),
        "The vendor access broker is being rolled out; MFA enforcement follows.",
        (
            "Meanwhile the VPN account is enabled on request only, time-boxed and "
            "supervised by plant engineering."
        ),
    ),
    (
        "EXC.009",
        "Lookout v1 cameras past their security support period",
        2,
        "in_review",
        365,
        ("Device firmware and signing keys",),
        ("AC.010",),
        ("A.8.8",),
        (),
        (),
        "Lookout v1 (sold until 2021) no longer receives firmware updates.",
        (
            "Customers notified with a trade-in offer; the cloud refuses streams from "
            "firmware older than 1.9."
        ),
    ),
]

# name, risk scenario refs, expiry, justification, description. Kept in the
# "created" state: submitting or accepting one needs an approver account.
ACCEPTANCES = [
    (
        "Residual DDoS exposure on the store edge during launches",
        ("RS.06",),
        180,
        (
            "Kestrava Cloud scrubbing absorbs volumetric attacks up to contract "
            "limits; short slowdowns during launches are within appetite."
        ),
        "Proposed acceptance for the volumetric attack scenario.",
    ),
    (
        "Telemetry storage misconfiguration, pending CSPM rollout",
        ("RS.05",),
        90,
        (
            "Object lock and bucket policies in place; cloud posture monitoring "
            "arrives next quarter."
        ),
        "Time-boxed acceptance until continuous cloud posture monitoring is live.",
    ),
    (
        "Integrator access to assembly PLCs until the MFA broker is live",
        ("RS.08",),
        60,
        (
            "Access is enabled on request and supervised; the line cannot run "
            "without Linterra Automation support during the retrofit."
        ),
        "Time-boxed acceptance tied to security exception EXC.008.",
    ),
]


@register
class FindingsBuilder(DemoBuilder):
    """Follow-ups with findings, vulnerabilities, exceptions, risk acceptances."""

    name = "findings"
    depends = ("core", "compliance", "risk")
    covers: ClassVar[dict] = {
        FindingsAssessment: "folder",
        Finding: "folder",
        Vulnerability: "folder",
        SecurityException: "folder",
        RiskAcceptance: "folder",
    }

    def stamps(self, ctx):
        scope = {"folder__in": ctx.folders()}
        return [
            (FindingsAssessment, scope, ("ref_id",)),
            (Finding, scope, ("findings_assessment__ref_id", "ref_id")),
            (Vulnerability, scope, ("ref_id",)),
            (SecurityException, scope, ("ref_id",)),
            (RiskAcceptance, scope, ("name",)),
        ]

    def build(self, ctx):
        vulnerabilities = self.build_vulnerabilities(ctx)
        self.build_findings(ctx, vulnerabilities)
        self.build_exceptions(ctx, vulnerabilities)
        self.build_acceptances(ctx)
        ctx.out(f"{len(FINDINGS)} findings, {len(vulnerabilities)} vulnerabilities")

    def build_vulnerabilities(self, ctx):
        result = {}
        for (
            ref_id,
            name,
            severity,
            status,
            assets,
            controls,
            detected,
            due,
            eta,
            description,
        ) in VULNERABILITIES:
            # due_date is set explicitly, so save() never applies the SLA from
            # the instance's (non-demo) settings.
            vulnerability, created = Vulnerability.objects.get_or_create(
                ref_id=ref_id,
                folder=ctx.domain,
                defaults={
                    "name": name,
                    "description": description,
                    "severity": severity,
                    "status": status,
                    "detected_at": ctx.day(detected),
                    "due_date": ctx.day(due) if due is not None else None,
                    "eta": ctx.day(eta) if eta is not None else None,
                },
            )
            if created:
                vulnerability.assets.set(_assets(ctx, assets))
                vulnerability.applied_controls.set(_controls(ctx, controls))
            result[ref_id] = vulnerability
        return result

    def build_findings(self, ctx, vulnerabilities):
        requirements = _lead_requirements(ctx)
        audits = _audits(ctx)
        perimeters = {
            p.ref_id: p
            for p in Perimeter.objects.filter(folder=ctx.domain).order_by("ref_id")
        }
        follow_ups = {}
        for (
            ref_id,
            name,
            category,
            status,
            perimeter,
            start,
            reported,
            due,
            budget,
            expenses,
            audit_ref,
            description,
            objectives,
        ) in FOLLOW_UPS:
            follow_up, _ = FindingsAssessment.objects.get_or_create(
                ref_id=ref_id,
                folder=ctx.domain,
                defaults={
                    "name": name,
                    "description": description,
                    "category": category,
                    "status": status,
                    "perimeter": perimeters.get(perimeter),
                    "start_date": ctx.day(start),
                    "reported_at": ctx.day(reported) if reported is not None else None,
                    "due_date": ctx.day(due) if due is not None else None,
                    "budget": Decimal(budget) if budget else None,
                    "expenses": Decimal(expenses) if expenses else None,
                    "objectives": objectives,
                    "compliance_assessment": audits.get(audit_ref),
                },
            )
            follow_ups[ref_id] = follow_up

        for (
            follow_up_ref,
            ref_id,
            name,
            severity,
            status,
            priority,
            controls,
            asset,
            requirement,
            eta,
            due,
            observation,
            recommendation,
            linked_vulnerabilities,
        ) in FINDINGS:
            follow_up = follow_ups[follow_up_ref]
            assessment = requirements.get(requirement) if requirement else None
            assets = _assets(ctx, [asset]) if asset else []
            finding, created = Finding.objects.get_or_create(
                ref_id=ref_id,
                findings_assessment=follow_up,
                defaults={
                    "name": name,
                    "folder": follow_up.folder,
                    "severity": severity,
                    "status": status,
                    "priority": priority,
                    "asset": assets[0] if assets else None,
                    "requirement_assessment": assessment,
                    "requirement_node": assessment.requirement if assessment else None,
                    "eta": ctx.day(eta) if eta is not None else None,
                    "due_date": ctx.day(due) if due is not None else None,
                    "observation": observation,
                    "recommendation": recommendation,
                },
            )
            if created:
                finding.applied_controls.set(_controls(ctx, controls))
                finding.vulnerabilities.set(
                    [vulnerabilities[v] for v in linked_vulnerabilities]
                )

    def build_exceptions(self, ctx, vulnerabilities):
        requirements = _lead_requirements(ctx)
        scenarios = {s.ref_id: s for s in ctx.refs.get("risk_scenarios", [])}
        for (
            ref_id,
            name,
            severity,
            status,
            expiration,
            assets,
            controls,
            requirement_refs,
            linked_vulnerabilities,
            scenario_refs,
            description,
            observation,
        ) in EXCEPTIONS:
            exception, created = SecurityException.objects.get_or_create(
                ref_id=ref_id,
                folder=ctx.domain,
                defaults={
                    "name": name,
                    "description": description,
                    "severity": severity,
                    "status": status,
                    "expiration_date": ctx.day(expiration)
                    if expiration is not None
                    else None,
                    "observation": observation,
                },
            )
            if not created:
                continue
            for asset in _assets(ctx, assets):
                asset.security_exceptions.add(exception)
            for control in _controls(ctx, controls):
                control.security_exceptions.add(exception)
            for ref in requirement_refs:
                if ref in requirements:
                    requirements[ref].security_exceptions.add(exception)
            for ref in linked_vulnerabilities:
                vulnerabilities[ref].security_exceptions.add(exception)
            for ref in scenario_refs:
                if ref in scenarios:
                    scenarios[ref].security_exceptions.add(exception)

    def build_acceptances(self, ctx):
        scenarios = {s.ref_id: s for s in ctx.refs.get("risk_scenarios", [])}
        for name, scenario_refs, expiry, justification, description in ACCEPTANCES:
            acceptance, created = RiskAcceptance.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "description": description,
                    "justification": justification,
                    "expiry_date": ctx.day(expiry),
                },
            )
            if created:
                acceptance.risk_scenarios.set(
                    [scenarios[r] for r in scenario_refs if r in scenarios]
                )


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

# ref, name, description, status, severity, detection, occurred and
# resolved as (day offset, hour, minute), threats, assets, controls,
# qualifications, BCP activated, resolution, timeline. Timeline entries:
# (day offset, hour, minute, type, entry, observation). The status/severity
# changes mirror what the incident view records on update; regulatory
# notifications (CRA, NIS2, GDPR, DORA) are logged as observations.
INCIDENTS = [
    (
        "INC.2026.001",
        "Phishing of a firmware engineer",
        (
            "A look-alike 'chipset SDK update' email from a fake Orbisil "
            "Semiconductors domain harvested a firmware engineer's credentials."
        ),
        "resolved",
        3,
        "internally_detected",
        (-41, 8, 10),
        (-38, 17, 0),
        ("Supply chain compromise",),
        ("Workforce identity provider", "Firmware CI build farm"),
        ("AC.001", "AC.006", "AC.013"),
        ("confidentiality", "integrity"),
        False,
        (
            "Credentials reset, look-alike domain blocked, CI and HSM logs clean. "
            "Number-matching MFA held; targeted phishing simulation scheduled."
        ),
        [
            (
                -41,
                8,
                40,
                "detection",
                "Engineer reports a suspicious SDK update email after signing in",
                "The link led to a fake Brightline Identity sign-in page.",
            ),
            (-41, 8, 55, "status_changed", "New->Ongoing", None),
            (
                -41,
                9,
                10,
                "mitigation",
                "Password reset, sessions and tokens revoked for the engineer",
                None,
            ),
            (
                -41,
                10,
                30,
                "observation",
                "Attacker sign-ins blocked by the MFA number-matching prompt",
                "Three attempts from a hosting provider, none successful.",
            ),
            (
                -41,
                14,
                0,
                "observation",
                "Firmware CI and signing HSM logs reviewed",
                "No signing request and no code change from the account.",
            ),
            (
                -40,
                9,
                0,
                "mitigation",
                "Look-alike domain blocked at the mail gateway and proxy",
                "Nine other firmware engineers received the email; none clicked.",
            ),
            (-38, 17, 0, "status_changed", "Ongoing->Resolved", None),
        ],
    ),
    (
        "INC.2026.002",
        "USB malware on a Brno plant engineering workstation",
        (
            "EDR blocked a worm launched from a contractor's USB stick on the "
            "engineering workstation that loads recipes to cell 3."
        ),
        "closed",
        2,
        "internally_detected",
        (-75, 2, 55),
        (-72, 16, 0),
        ("Ransomware deployment", "OT intrusion through remote maintenance"),
        ("Production line control", "Assembly cell PLCs"),
        ("AC.005", "AC.007", "AC.017"),
        ("availability", "integrity", "safety"),
        True,
        (
            "Workstation reimaged, PLC programs verified against the backup, USB "
            "ports locked with a scanning kiosk. NIS2 reporting completed."
        ),
        [
            (
                -75,
                3,
                12,
                "detection",
                "EDR blocks a USB-launched worm on engineering workstation BRN-ENG-04",
                "The stick was used to load a Keystone recipe on cell 3.",
            ),
            (-75, 3, 30, "status_changed", "New->Ongoing", None),
            (-75, 3, 45, "severity_changed", "Moderate->Major", None),
            (
                -75,
                4,
                10,
                "mitigation",
                "Cell 3 isolated from the plant LAN; recipes loaded manually",
                "Business continuity plan activated; Keystone output down 40%.",
            ),
            (
                -75,
                11,
                0,
                "observation",
                "NIS2 early warning sent to the national CSIRT",
                "Within 24 hours: suspected malicious act affecting production.",
            ),
            (
                -74,
                10,
                0,
                "observation",
                "Forensics confirm no spread to SCADA or PLCs",
                "PLC program hashes match the verified backup.",
            ),
            (
                -73,
                15,
                0,
                "mitigation",
                "USB ports locked on engineering workstations; kiosk installed",
                None,
            ),
            (-72, 16, 0, "status_changed", "Ongoing->Resolved", None),
            (
                -72,
                17,
                0,
                "observation",
                "NIS2 incident notification submitted",
                "72-hour notification with impact, indicators and mitigations.",
            ),
            (
                -45,
                10,
                0,
                "observation",
                "NIS2 final report submitted",
                "Root cause: contractor media not scanned before use on OT.",
            ),
            (-44, 9, 30, "status_changed", "Resolved->Closed", None),
        ],
    ),
    (
        "INC.2026.003",
        "Lost laptop — Eindhoven hardware design office",
        "A hardware engineer reported a laptop left on a train.",
        "new",
        4,
        "internally_detected",
        (-2, 17, 45),
        None,
        (),
        ("Product designs and source code",),
        ("AC.005",),
        ("confidentiality",),
        None,
        None,
        [
            (
                -2,
                18,
                30,
                "detection",
                "Loss reported to the service desk",
                "Device is encrypted (MDM compliant); remote wipe requested.",
            ),
            (
                -1,
                9,
                15,
                "observation",
                "Laptop has not checked in since the loss",
                "Local PLM cache held Keystone hub v3 schematics.",
            ),
        ],
    ),
    (
        "INC.2026.004",
        "Suspicious VPN logins from an unusual country",
        "Impossible-travel alert on a sales director's account.",
        "dismissed",
        5,
        "internally_detected",
        (-20, 7, 30),
        (-19, 9, 20),
        (),
        ("Corporate VPN gateway", "Workforce identity provider"),
        (),
        (),
        False,
        (
            "False positive: user at a consumer electronics trade show, confirmed by "
            "the manager."
        ),
        [
            (
                -20,
                7,
                50,
                "detection",
                "SIEM raises an impossible-travel alert",
                None,
            ),
            (
                -19,
                9,
                10,
                "observation",
                "User confirms the business trip; MFA prompts were genuine",
                None,
            ),
            (-19, 9, 20, "status_changed", "New->Dismissed", None),
        ],
    ),
    (
        "INC.2026.005",
        "Kelvin assembly line stopped by a PLC misconfiguration",
        "An unreviewed recipe change halted cell 2 for three hours.",
        "resolved",
        3,
        "internally_detected",
        (-33, 5, 50),
        (-32, 11, 0),
        (),
        ("Production line control", "Assembly cell PLCs"),
        ("AC.017", "AC.007"),
        ("availability", "safety"),
        False,
        "Program restored from the verified backup; PLC changes now need approval.",
        [
            (
                -33,
                6,
                5,
                "detection",
                "Cell 2 PLCs enter fault state; Kelvin assembly stops",
                None,
            ),
            (-33, 6, 20, "status_changed", "New->Ongoing", None),
            (
                -33,
                7,
                0,
                "observation",
                "Recipe change pushed the night before without review",
                "The change bypassed the PLC change management procedure.",
            ),
            (
                -33,
                8,
                45,
                "mitigation",
                "Previous PLC program restored from the verified backup",
                "Line back in production at 09:10; 1,150 thermostats delayed.",
            ),
            (-32, 11, 0, "status_changed", "Ongoing->Resolved", None),
        ],
    ),
    (
        "INC.2026.006",
        "Lookout camera clips exposed through enumerable links",
        (
            "A researcher reported through the disclosure programme that Lookout "
            "clip links could be guessed; logs showed active exploitation."
        ),
        "resolved",
        2,
        "externally_detected",
        (-33, 2, 0),
        (-26, 17, 0),
        ("Cloud misconfiguration",),
        ("Customer and device accounts", "Device cloud Kubernetes cluster"),
        ("AC.010",),
        ("confidentiality", "privacy", "reputation"),
        False,
        (
            "Signed, expiring clip links bound to the account; CDN authorisation. "
            "CRA, GDPR and customer notifications completed."
        ),
        [
            (
                -31,
                14,
                20,
                "detection",
                "Disclosure report: Lookout clip links can be enumerated",
                "Received through security.txt; PSIRT acknowledged within 2 hours.",
            ),
            (-31, 16, 5, "status_changed", "New->Ongoing", None),
            (
                -31,
                18,
                30,
                "mitigation",
                "CDN now requires a valid session on clip downloads",
                "Stops anonymous downloads; links are still predictable.",
            ),
            (
                -30,
                9,
                15,
                "observation",
                "CDN logs show a scraper fetched clips from 143 accounts",
                "It started two days before the report: actively exploited.",
            ),
            (-30, 9, 40, "severity_changed", "Moderate->Major", None),
            (
                -30,
                11,
                0,
                "observation",
                "CRA early warning sent to the CSIRT and ENISA reporting platform",
                "Within 24 hours of becoming aware of active exploitation.",
            ),
            (
                -29,
                10,
                0,
                "mitigation",
                "Signed, expiring clip links deployed in every region",
                None,
            ),
            (
                -28,
                15,
                0,
                "observation",
                "Personal data breach notified to the supervisory authority",
                "Within 72 hours, led by the DPO; the 143 households were informed.",
            ),
            (
                -28,
                16,
                30,
                "observation",
                "CRA vulnerability notification submitted",
                "72-hour report: affected products, fix status, mitigations.",
            ),
            (-26, 17, 0, "status_changed", "Ongoing->Resolved", None),
            (
                -15,
                11,
                0,
                "observation",
                "CRA final report submitted",
                "Within 14 days of the fix: root cause, impact and lessons learned.",
            ),
        ],
    ),
    (
        "INC.2026.007",
        "DDoS on the online store during the Keystone hub launch",
        "A botnet flooded the store front minutes after the launch went live.",
        "resolved",
        3,
        "internally_detected",
        (-55, 10, 4),
        (-54, 10, 0),
        ("Denial of service",),
        ("Online store web front", "Store checkout and payments"),
        ("AC.008",),
        ("availability", "reputation"),
        False,
        (
            "Scrubbing and a checkout waiting room absorbed the attack; launch "
            "playbook now enables both ahead of time."
        ),
        [
            (
                -55,
                10,
                7,
                "detection",
                "Store latency alert: traffic 40 times the launch forecast",
                "Requests come from a botnet, not buyers.",
            ),
            (-55, 10, 12, "status_changed", "New->Ongoing", None),
            (
                -55,
                10,
                20,
                "mitigation",
                "Kestrava Cloud scrubbing enabled for the store front",
                None,
            ),
            (
                -55,
                10,
                45,
                "mitigation",
                "Waiting room enabled for checkout",
                None,
            ),
            (
                -55,
                11,
                30,
                "observation",
                "Checkout recovered; card payments were down for 38 minutes",
                (
                    "Payments Risk Officer: not major under DORA (duration and clients "
                    "below thresholds)."
                ),
            ),
            (-54, 10, 0, "status_changed", "Ongoing->Resolved", None),
        ],
    ),
]


@register
class IncidentsBuilder(DemoBuilder):
    """Incidents across the domains, each with a timeline."""

    name = "incidents"
    depends = ("core", "risk")
    covers: ClassVar[dict] = {
        Incident: "folder",
        TimelineEntry: "folder",
    }

    def stamps(self, ctx):
        scope = {"folder__in": ctx.folders()}
        return [
            (Incident, scope, ("ref_id",)),
            (TimelineEntry, scope, ("incident__ref_id", "timestamp")),
        ]

    def build(self, ctx):
        threats = {t.name: t for t in ctx.refs.get("threats", [])}
        qualifications = {
            t.name: t
            for t in Terminology.objects.filter(
                field_path=Terminology.FieldPath.QUALIFICATIONS, is_visible=True
            )
        }
        for (
            ref_id,
            name,
            description,
            status,
            severity,
            detection,
            occurred,
            resolved,
            threat_names,
            assets,
            controls,
            qualification_names,
            bcp,
            resolution,
            timeline,
        ) in INCIDENTS:
            incident, created = Incident.objects.get_or_create(
                ref_id=ref_id,
                folder=ctx.domain,
                defaults={
                    "name": name,
                    "description": description,
                    "status": status,
                    "severity": severity,
                    "detection": detection,
                    "occurred_at": _ts(ctx, *occurred),
                    "reported_at": _ts(ctx, *timeline[0][:3]),
                    "resolved_at": _ts(ctx, *resolved) if resolved else None,
                    "is_bcp_activated": bcp,
                    "resolution": resolution,
                },
            )
            if not created:
                continue
            incident.threats.set([threats[t] for t in threat_names if t in threats])
            incident.assets.set(_assets(ctx, assets))
            incident.applied_controls.set(_controls(ctx, controls))
            incident.qualifications.set(
                [qualifications[q] for q in qualification_names if q in qualifications]
            )
            for offset, hour, minute, entry_type, entry, observation in timeline:
                TimelineEntry.objects.create(
                    incident=incident,
                    entry=entry,
                    entry_type=entry_type,
                    timestamp=_ts(ctx, offset, hour, minute),
                    observation=observation,
                )
        ctx.out(f"{len(INCIDENTS)} incidents seeded")
