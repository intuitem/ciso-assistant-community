"""Realistic, messy spreadsheets for trying the data import page."""

import csv
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
BOLD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="1F4E78")


def sheet(wb, title, header, rows, banner=None, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    if banner:
        for line in banner:
            ws.append([line])
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(header))
        ws["A1"].font = Font(bold=True, size=14)
        ws.append([])
    ws.append(header)
    for cell in ws[ws.max_row]:
        cell.font, cell.fill = BOLD, FILL
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        ws.column_dimensions[col[-1].column_letter].width = 22
    return ws


def text_sheet(wb, title, lines):
    ws = wb.create_sheet(title)
    for line in lines:
        ws.append([line])


# 1. French asset register: banner, two asset tabs, a lookup tab, a readme.
wb = Workbook()
sheet(
    wb,
    "Processus métier",
    ["Réf.", "Nom", "Description", "Type", "Domaine", "Propriétaire"],
    [
        [
            "PM-01",
            "Facturation clients",
            "Émission et suivi des factures",
            "Primaire",
            "DEMO",
            "Direction financière",
        ],
        ["PM-02", "Paie", "Calcul et versement des salaires", "Primaire", "DEMO", "RH"],
        [
            "PM-03",
            "Vente en ligne",
            "Boutique e-commerce",
            "Primaire",
            "DEMO",
            "Direction commerciale",
        ],
        [
            "PM-04",
            "Support client",
            "Traitement des demandes clients",
            "Primaire",
            "DSI Lyon",
            "Service client",
        ],
    ],
    banner=[
        "Cartographie du SI – Processus métier",
        "Version 3.2 – validée en COPIL le 12/09/2026",
    ],
    first=True,
)
sheet(
    wb,
    "Inventaire applicatif",
    ["Réf.", "Nom", "Description", "Type", "Domaine", "Hébergement", "Criticité"],
    [
        [
            "APP-001",
            "SAP S/4HANA",
            "ERP finance et achats",
            "Support",
            "DEMO",
            "Datacenter Paris",
            "Haute",
        ],
        ["APP-002", "Salesforce", "CRM commercial", "Support", "DEMO", "SaaS", "Haute"],
        ["APP-003", "Workday", "SIRH et paie", "Support", "DEMO", "SaaS", "Moyenne"],
        [
            "APP-004",
            "Magento",
            "Plateforme e-commerce",
            "Support",
            "DEMO",
            "AWS eu-west-3",
            "Haute",
        ],
        [
            "APP-005",
            "Zendesk",
            "Outil de ticketing support",
            "Support",
            "DSI Lyon",
            "SaaS",
            "Moyenne",
        ],
        [
            "APP-006",
            "Active Directory",
            "Annuaire et authentification",
            "Support",
            "DEMO",
            "Datacenter Paris",
            "Critique",
        ],
        [
            "APP-007",
            "Veeam",
            "Sauvegardes",
            "Support",
            "DEMO",
            "Datacenter Paris",
            "Haute",
        ],
        [
            "APP-008",
            "Microsoft 365",
            "Messagerie et bureautique",
            "Support",
            "DEMO",
            "SaaS",
            "Haute",
        ],
        [None, None, None, None, None, None, None],
    ],
    banner=["Inventaire applicatif 2026", "Source : CMDB extraite le 01/10/2026"],
)
sheet(
    wb,
    "Listes",
    ["Criticité", "Hébergement"],
    [
        ["Critique", "SaaS"],
        ["Haute", "Datacenter Paris"],
        ["Moyenne", "AWS eu-west-3"],
        ["Basse", ""],
    ],
)
text_sheet(
    wb,
    "Lisez-moi",
    [
        "Ce classeur est maintenu par la DSI.",
        "Ne pas modifier l'onglet Listes.",
        "Contact : dsi@acme.fr",
    ],
)
wb.save(OUT / "01_cartographie_SI_FR.xlsx")

# 2. English ISMS controls tracker: header on row 2 under a note, free-form statuses.
wb = Workbook()
ws = wb.active
ws.title = "Controls"
ws.append(["Last reviewed by the ISMS committee on 2026-09-30. Do not sort."])
header = [
    "Control ID",
    "Control",
    "Details",
    "Category",
    "CSF Function",
    "Status",
    "Priority",
    "Effort",
    "Owner",
    "Due date",
    "Evidence link",
]
ws.append(header)
for cell in ws[2]:
    cell.font, cell.fill = BOLD, FILL
rows = [
    [
        "ISMS-01",
        "Information security policy",
        "Approve and publish the top-level policy",
        "Policy",
        "Govern",
        "Done",
        "High",
        "S",
        "ciso@acme.com",
        date(2026, 3, 31),
        "https://intranet.acme.com/isms/policy",
    ],
    [
        "ISMS-02",
        "MFA for remote access",
        "Enforce MFA on VPN and webmail",
        "Technical",
        "Protect",
        "In Progress",
        "High",
        "M",
        "it.ops@acme.com",
        date(2026, 12, 15),
        "",
    ],
    [
        "ISMS-03",
        "Quarterly access review",
        "Review privileged accounts every quarter",
        "Process",
        "Identify",
        "Planned",
        "Medium",
        "M",
        "iam@acme.com",
        "Q1 2027",
        "",
    ],
    [
        "ISMS-04",
        "EDR on all endpoints",
        "Roll out the EDR agent fleet-wide",
        "Technical",
        "Detect",
        "In Progress",
        "P1",
        "Large",
        "soc@acme.com",
        date(2026, 11, 30),
        "",
    ],
    [
        "ISMS-05",
        "Backup restore tests",
        "Restore a sample every month",
        "Procedure",
        "Recover",
        "On hold",
        "Medium",
        "S",
        "it.ops@acme.com",
        date(2026, 10, 31),
        "",
    ],
    [
        "ISMS-06",
        "Security awareness training",
        "Annual training and phishing drills",
        "Process",
        "Protect",
        "Done",
        "Low",
        "M",
        "hr@acme.com",
        date(2026, 6, 30),
        "https://lms.acme.com/sec101",
    ],
    [
        "ISMS-07",
        "Incident response plan",
        "Write and test the IR playbooks",
        "Policy",
        "Respond",
        "Not started",
        "High",
        "L",
        "soc@acme.com",
        date(2027, 1, 31),
        "",
    ],
    [
        "ISMS-08",
        "Badge access to server rooms",
        "Restrict and log physical access",
        "Physical",
        "Protect",
        "Done",
        "Medium",
        "XS",
        "facilities@acme.com",
        date(2026, 2, 28),
        "",
    ],
    [
        "ISMS-09",
        "Vulnerability scanning",
        "Weekly authenticated scans",
        "Technical",
        "Identify",
        "Deprecated",
        "Low",
        "S",
        "soc@acme.com",
        "",
        "",
    ],
    [
        "ISMS-10",
        "Supplier security clauses",
        "Add security annex to contracts",
        "Process",
        "Govern",
        "In progress",
        "Medium",
        "M",
        "legal@acme.com",
        date(2026, 12, 31),
        "",
    ],
]
for row in rows:
    ws.append(row)
wb.save(OUT / "02_isms_controls_tracker_EN.xlsx")

# 3. Vendor register: four tabs that map onto the third-party template's sheets.
wb = Workbook()
sheet(
    wb,
    "Suppliers",
    ["Vendor ID", "Vendor", "What they do", "Country", "Currency", "Domain"],
    [
        ["V-001", "Contoso Cloud", "IaaS provider", "France", "EUR", "DEMO"],
        ["V-002", "Northwind Payroll", "Payroll outsourcing", "Germany", "EUR", "DEMO"],
        ["V-003", "Fabrikam Security", "Managed SOC", "United States", "USD", "DEMO"],
        ["V-004", "Tailspin Logistics", "Warehousing", "Belgium", "EUR", "DEMO"],
    ],
    first=True,
)
sheet(
    wb,
    "Services",
    ["Service ref", "Service", "Description", "Vendor ID", "Vendor"],
    [
        ["S-01", "Compute hosting", "VMs and storage", "V-001", "Contoso Cloud"],
        [
            "S-02",
            "Payroll processing",
            "Monthly payroll run",
            "V-002",
            "Northwind Payroll",
        ],
        [
            "S-03",
            "24/7 SOC monitoring",
            "Alert triage and response",
            "V-003",
            "Fabrikam Security",
        ],
    ],
)
sheet(
    wb,
    "Contracts",
    [
        "Contract #",
        "Title",
        "Vendor ID",
        "Service ref",
        "Status",
        "Start",
        "End",
        "Annual cost",
        "Currency",
        "Domain",
    ],
    [
        [
            "C-2024-17",
            "Hosting framework agreement",
            "V-001",
            "S-01",
            "Active",
            date(2024, 1, 1),
            date(2027, 12, 31),
            180000,
            "EUR",
            "DEMO",
        ],
        [
            "C-2025-03",
            "Payroll services",
            "V-002",
            "S-02",
            "Signed",
            date(2025, 4, 1),
            date(2028, 3, 31),
            42000,
            "EUR",
            "DEMO",
        ],
        [
            "C-2023-41",
            "SOC retainer",
            "V-003",
            "S-03",
            "Expired",
            date(2023, 6, 1),
            date(2026, 5, 31),
            96000,
            "USD",
            "DEMO",
        ],
        [
            "C-2026-08",
            "Warehouse lease",
            "V-004",
            "",
            "Draft",
            date(2026, 11, 1),
            date(2029, 10, 31),
            60000,
            "EUR",
            "DEMO",
        ],
    ],
)
sheet(
    wb,
    "Contacts",
    ["Email", "First name", "Last name", "Role", "Phone", "Vendor ID"],
    [
        [
            "j.martin@contoso.example",
            "Julie",
            "Martin",
            "Account manager",
            "+33 1 23 45 67 89",
            "V-001",
        ],
        [
            "k.weber@northwind.example",
            "Klaus",
            "Weber",
            "Service delivery lead",
            "+49 30 1234567",
            "V-002",
        ],
        [
            "d.brown@fabrikam.example",
            "Dana",
            "Brown",
            "SOC manager",
            "+1 415 555 0101",
            "V-003",
        ],
    ],
)
wb.save(OUT / "03_vendor_register.xlsx")

# 4. Risk register: matrix-dependent levels as words, threats and assets as lists.
wb = Workbook()
sheet(
    wb,
    "Risk register",
    [
        "Risk ID",
        "Risk",
        "Scenario",
        "Threat",
        "Affected assets",
        "Likelihood",
        "Impact",
        "Existing controls",
        "Treatment",
        "Residual likelihood",
        "Residual impact",
        "Planned controls",
    ],
    [
        [
            "R-01",
            "Ransomware on file servers",
            "Encryption of shared drives after phishing",
            "Ransomware",
            "File servers, Active Directory",
            "High",
            "Very high",
            "Backups, EDR",
            "Mitigate",
            "Low",
            "High",
            "Immutable backups",
        ],
        [
            "R-02",
            "Payroll data leak",
            "Exfiltration of payroll data by a supplier",
            "Data leak",
            "Workday",
            "Medium",
            "High",
            "NDA",
            "Transfer",
            "Low",
            "High",
            "Contract security annex",
        ],
        [
            "R-03",
            "E-commerce outage",
            "DDoS on the web shop during sales",
            "Denial of service",
            "Magento",
            "Medium",
            "Medium",
            "CDN",
            "Mitigate",
            "Low",
            "Medium",
            "Anti-DDoS service",
        ],
        [
            "R-04",
            "Account takeover",
            "Credential stuffing on webmail",
            "Credential theft",
            "Microsoft 365",
            "High",
            "High",
            "Password policy",
            "Mitigate",
            "Low",
            "Medium",
            "MFA everywhere",
        ],
        [
            "R-05",
            "Legacy ERP end of support",
            "No security patches after 2027",
            "Unpatched software",
            "SAP S/4HANA",
            "Low",
            "High",
            "",
            "Accept",
            "Low",
            "High",
            "",
        ],
    ],
    banner=["Risk register FY2026", "Owner: CISO office"],
    first=True,
)
wb.save(OUT / "04_risk_register_FY2026.xlsx")

# 5. Pentest findings: semicolon CSV, as exported by a reporting tool.
with open(
    OUT / "05_pentest_findings_Q3.csv", "w", newline="", encoding="utf-8-sig"
) as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(
        [
            "Finding ID",
            "Title",
            "Description",
            "Severity",
            "Status",
            "Affected asset",
            "Recommendation",
        ]
    )
    w.writerows(
        [
            [
                "PT-2026-01",
                "SQL injection in search",
                "Unsanitised parameter q",
                "Critical",
                "Open",
                "Magento",
                "Use prepared statements",
            ],
            [
                "PT-2026-02",
                "Outdated TLS configuration",
                "TLS 1.0 still accepted",
                "Medium",
                "Fixed",
                "Magento",
                "Disable TLS < 1.2",
            ],
            [
                "PT-2026-03",
                "Default admin credentials",
                "Admin console with vendor password",
                "High",
                "Open",
                "Veeam",
                "Rotate credentials",
            ],
            [
                "PT-2026-04",
                "Verbose error messages",
                "Stack traces shown to users",
                "Low",
                "Accepted risk",
                "Salesforce",
                "Generic error pages",
            ],
            [
                "PT-2026-05",
                "Missing security headers",
                "No CSP or HSTS",
                "Informational",
                "Open",
                "Magento",
                "Add headers at the CDN",
            ],
            [
                "PT-2026-06",
                "Kerberoastable service accounts",
                "SPNs on accounts with weak passwords",
                "High",
                "In remediation",
                "Active Directory",
                "Long random passwords",
            ],
        ]
    )

# 6. Incident log: French comma CSV with French statuses and severities.
with open(OUT / "06_journal_incidents_FR.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(
        ["Réf", "Incident", "Description", "Gravité", "Statut", "Détection", "Domaine"]
    )
    w.writerows(
        [
            [
                "INC-0142",
                "Phishing ciblé",
                "Campagne visant la comptabilité",
                "Majeure",
                "Résolu",
                "Interne",
                "DEMO",
            ],
            [
                "INC-0143",
                "Perte d'un ordinateur portable",
                "PC non chiffré oublié dans un train",
                "Modérée",
                "Clos",
                "Interne",
                "DEMO",
            ],
            [
                "INC-0144",
                "Fuite de données client",
                "Fichier exposé sur un partage public",
                "Critique",
                "En cours",
                "Externe",
                "DEMO",
            ],
            [
                "INC-0145",
                "Indisponibilité du site",
                "Saturation lors des soldes",
                "Mineure",
                "Nouveau",
                "Interne",
                "DEMO",
            ],
            [
                "INC-0146",
                "Compte compromis",
                "Connexion depuis un pays inhabituel",
                "Majeure",
                "En cours",
                "Interne",
                "DSI Lyon",
            ],
        ]
    )

# 7. Users: email only for some rows, names in one column for others.
with open(OUT / "07_new_joiners.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["E-mail address", "Given name", "Surname", "Department"])
    w.writerows(
        [
            ["alice.dupont@acme.example", "Alice", "Dupont", "Finance"],
            ["bruno.leroy@acme.example", "Bruno", "Leroy", "IT"],
            ["chloe.nguyen@acme.example", "", "", "Legal"],
            ["david.okafor@acme.example", "David", "Okafor", "SOC"],
        ]
    )

# 8. CMDB export: an asset list drowned in side columns whose names happen to
# match other objects' fields (Status, Impact, Link, Label), plus a duplicated
# header and owners as emails.
wb = Workbook()
sheet(
    wb,
    "Assets",
    [
        "Asset tag",
        "Name",
        "Description",
        "Class",
        "Label",
        "Impact",
        "Status",
        "Link",
        "Internal ID",
        "Owner",
        "Comments",
        "Name",
    ],
    [
        [
            "AST-001",
            "CRM",
            "Customer relationship management",
            "Confidential",
            "PCI scope",
            "High",
            "Prod",
            "https://cmdb.acme.example/ci/1",
            1001,
            "it.ops@acme.com",
            "migrated 2024",
            "crm-prod",
        ],
        [
            "AST-002",
            "ERP",
            "Finance and purchasing",
            "Restricted",
            "",
            "High",
            "Prod",
            "https://cmdb.acme.example/ci/2",
            1002,
            "finance@acme.com",
            "",
            "erp-prod",
        ],
        [
            "AST-003",
            "Intranet",
            "Employee portal",
            "Internal",
            "",
            "Low",
            "Test",
            "https://cmdb.acme.example/ci/3",
            1003,
            "it.ops@acme.com",
            "to decommission",
            "intranet-test",
        ],
        [
            "AST-004",
            "Backup vault",
            "Offsite backups",
            "Confidential",
            "DR",
            "High",
            "Prod",
            "https://cmdb.acme.example/ci/4",
            1004,
            "it.ops@acme.com",
            "",
            "vault",
        ],
        [
            "AST-005",
            "Legacy FTP",
            "Partner file exchange",
            "Internal",
            "",
            "Medium",
            "Decommissioned",
            "https://cmdb.acme.example/ci/5",
            1005,
            "",
            "",
            "ftp-old",
        ],
    ],
    first=True,
)
wb.save(OUT / "08_cmdb_assets_noisy.xlsx")

# 9. Internal audit worksheet against ISO/IEC 27001:2022 Annex A, in the
# auditor's own words. "Existing measures" become applied controls in passing;
# A.99.9 is not a requirement and must be reported.
wb = Workbook()
sheet(
    wb,
    "SoA review",
    [
        "Control",
        "Title",
        "Assessment",
        "Progress",
        "Score",
        "Auditor notes",
        "Existing measures",
    ],
    [
        [
            "A.5.1",
            "Policies for information security",
            "Compliant",
            "Done",
            4,
            "Policy approved 2026-03",
            "Information security policy",
        ],
        [
            "A.5.2",
            "Roles and responsibilities",
            "Partially compliant",
            "In review",
            2,
            "RACI incomplete",
            "",
        ],
        [
            "A.5.3",
            "Segregation of duties",
            "Non compliant",
            "To do",
            1,
            "Admins approve their own changes",
            "",
        ],
        [
            "A.5.7",
            "Threat intelligence",
            "Not applicable",
            "Done",
            "",
            "Out of scope this year",
            "",
        ],
        [
            "A.5.15",
            "Access control",
            "Partially compliant",
            "In progress",
            3,
            "MFA not on all apps",
            "MFA for remote access; Quarterly access review",
        ],
        [
            "A.99.9",
            "Made-up control",
            "Compliant",
            "Done",
            4,
            "Typo in the reference",
            "",
        ],
    ],
    banner=[
        "ISMS internal audit 2026 – Annex A sample",
        "Auditor: internal audit team",
    ],
    first=True,
)
wb.save(OUT / "09_iso27001_internal_audit.xlsx")

# 10. Vendor due diligence: the third party, its assessment, and its answers to
# an ISO 27001 based questionnaire. The answers become the audit the
# assessment links to by name, in the same import.
wb = Workbook()
sheet(
    wb,
    "Vendor",
    ["Vendor ID", "Vendor", "What they do", "Country", "Domain"],
    [
        [
            "V-101",
            "Northwind Analytics",
            "Data processing for marketing",
            "Netherlands",
            "DEMO",
        ]
    ],
    first=True,
)
sheet(
    wb,
    "Assessment",
    [
        "Vendor ID",
        "Assessment",
        "Description",
        "Criticality",
        "Due date",
        "Domain",
        "Audit name",
    ],
    [
        [
            "V-101",
            "Northwind onboarding review",
            "Before contract signature",
            3,
            date(2026, 12, 1),
            "DEMO",
            "Northwind questionnaire 2026",
        ]
    ],
)
sheet(
    wb,
    "Answers",
    ["Requirement", "Answer", "Comment"],
    [
        ["A.5.1", "Compliant", "Policy shared under NDA"],
        ["A.5.15", "Partially compliant", "MFA on admin accounts only"],
        ["A.8.24", "Compliant", "AES-256 at rest"],
        ["A.5.30", "Non compliant", "No tested BCP"],
    ],
)
wb.save(OUT / "10_vendor_due_diligence.xlsx")

# 11. Monthly KPI pack: the KPIs (metric instances of library definitions)
# and their monthly values. GOV-02 is a maturity level, given by name; one
# level is misspelt and one row names a KPI that does not exist.
wb = Workbook()
sheet(
    wb,
    "KPIs",
    ["KPI code", "KPI", "What it measures", "Metric", "Target", "Frequency", "Owner"],
    [
        [
            "KPI-VULN",
            "Open critical vulnerabilities",
            "Critical and high findings still open",
            "VULN-01",
            0,
            "Monthly",
            "soc@acme.com",
        ],
        [
            "KPI-MAT",
            "Security programme maturity",
            "Self-assessed maturity level",
            "GOV-02",
            "",
            "Quarterly",
            "",
        ],
    ],
    first=True,
)
sheet(
    wb,
    "Monthly values",
    ["KPI code", "Month", "Value", "Comment"],
    [
        ["KPI-VULN", date(2026, 6, 30), 18, "Backlog after pentest"],
        ["KPI-VULN", date(2026, 7, 31), 11, ""],
        ["KPI-VULN", date(2026, 8, 31), 7, "Patch sprint"],
        ["KPI-MAT", date(2026, 6, 30), "Developing", ""],
        ["KPI-MAT", date(2026, 9, 30), "Defined", "After ISMS audit"],
        ["KPI-MAT", date(2026, 8, 31), "Excelent", "Typo in the level"],
        ["KPI-LOST", date(2026, 8, 31), 3, "Code nobody defined"],
    ],
)
wb.save(OUT / "11_kpi_monthly_pack.xlsx")

# 12. Security calendar kept by the ISMS team: recurring activities with a
# frequency and an "every N" column, owners by email or team, and the control
# each activity maintains. One row has a frequency without its interval.
wb = Workbook()
sheet(
    wb,
    "Calendar",
    [
        "Ref",
        "Activity",
        "What to do",
        "Recurring",
        "Start",
        "Frequency",
        "Every",
        "Owner",
        "Control maintained",
        "Notes",
    ],
    [
        [
            "CAL-01",
            "Quarterly access review",
            "Review privileged accounts with each manager",
            "Yes",
            date(2026, 1, 15),
            "Monthly",
            3,
            "it-ops@acme.com",
            "Quarterly access review",
            "Export from the IAM tool",
        ],
        [
            "CAL-02",
            "Backup restore test",
            "Restore one production database to staging",
            "Yes",
            date(2026, 2, 1),
            "Monthly",
            1,
            "Infra team",
            "",
            "",
        ],
        [
            "CAL-03",
            "Annual ISMS management review",
            "Top management reviews objectives and incidents",
            "Yes",
            date(2026, 11, 30),
            "Yearly",
            1,
            "ciso@acme.com",
            "",
            "",
        ],
        [
            "CAL-04",
            "Phishing simulation",
            "",
            "Yes",
            date(2026, 3, 1),
            "Weekly",
            "",
            "soc@acme.com",
            "",
            "Interval forgotten",
        ],
        [
            "CAL-05",
            "Renew TLS certificates",
            "Public endpoints",
            "No",
            date(2026, 12, 1),
            "",
            "",
            "it-ops@acme.com",
            "",
            "",
        ],
    ],
    banner=["ISMS security calendar 2026"],
    first=True,
)
wb.save(OUT / "12_security_calendar.xlsx")

print("\n".join(sorted(p.name for p in OUT.iterdir())))
