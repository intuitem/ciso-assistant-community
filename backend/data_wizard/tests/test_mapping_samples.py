"""What detection makes of the realistic files in samples/: target per sheet and
the columns that must be recognised. A change in detection that loses one of
these shows up here."""

import io
from pathlib import Path

import pytest

from data_wizard import mapping

SAMPLES = Path(__file__).parent / "samples"
FOLDERS = {mapping.normalize(n) for n in ("DEMO", "Global")}

# file -> sheet -> (model type, template sheet) or None, and columns that must map.
EXPECTED = {
    "01_cartographie_SI_FR.xlsx": {
        "Processus métier": (
            ("Asset", "Sheet1"),
            {"Réf.": "ref_id", "Nom": "name", "Type": "type", "Domaine": "domain"},
        ),
        "Inventaire applicatif": (("Asset", "Sheet1"), {"Nom": "name"}),
        "Listes": (None, {}),
        "Lisez-moi": (None, {}),
    },
    "02_isms_controls_tracker_EN.xlsx": {
        "Controls": (
            ("AppliedControl", "Sheet1"),
            {
                "Control ID": "ref_id",
                "Control": "name",
                "Details": "description",
                "Status": "status",
                "Category": "category",
                "CSF Function": "csf_function",
                "Evidence link": "link",
            },
        ),
    },
    "03_vendor_register.xlsx": {
        "Suppliers": (
            ("TPRM", "Entities"),
            {"Vendor ID": "ref_id", "Vendor": "name", "Country": "country"},
        ),
        "Contracts": (
            ("TPRM", "Contracts"),
            {"Contract #": "ref_id", "Status": "status", "Start": "start_date"},
        ),
        "Contacts": (("TPRM", "Representatives"), {"Email": "email"}),
    },
    "04_risk_register_FY2026.xlsx": {
        "Risk register": (
            ("RiskAssessment", "Sheet1"),
            {"Risk ID": "ref_id", "Threat": "threats", "Treatment": "treatment"},
        ),
    },
    "05_pentest_findings_Q3.csv": {
        "CSV": (
            ("FindingsAssessment", "Sheet1"),
            {"Finding ID": "ref_id", "Title": "name", "Severity": "severity"},
        ),
    },
    "06_journal_incidents_FR.csv": {
        "CSV": (
            ("Incident", "Sheet1"),
            {"Réf": "ref_id", "Statut": "status", "Détection": "detection"},
        ),
    },
    "07_new_joiners.csv": {
        "CSV": (("User", "Sheet1"), {"E-mail address": "email"}),
    },
    "09_iso27001_internal_audit.xlsx": {
        "SoA review": (
            ("ComplianceAssessment", "Requirements"),
            {
                "Control": "ref_id",
                "Assessment": "compliance_result",
                "Progress": "requirement_progress",
                "Score": "score",
            },
        ),
    },
    "10_vendor_due_diligence.xlsx": {
        "Vendor": (("TPRM", "Entities"), {"Vendor ID": "ref_id", "Vendor": "name"}),
        "Assessment": (
            ("TPRM", "EntityAssessments"),
            {"Audit name": "audit_name", "Due date": "due_date"},
        ),
        "Answers": (
            ("ComplianceAssessment", "Requirements"),
            {"Requirement": "ref_id", "Answer": "compliance_result"},
        ),
    },
    "11_kpi_monthly_pack.xlsx": {
        "KPIs": (
            ("MetricInstance", "Metric instances"),
            {
                "Target": "target_value",
                "Frequency": "collection_frequency",
                "Owner": "owner",
            },
        ),
        "Monthly values": (
            ("CustomMetricSample", "Samples"),
            {"Month": "timestamp", "Value": "value"},
        ),
    },
    "12_security_calendar.xlsx": {
        "Calendar": (
            ("TaskTemplate", "Summary"),
            {
                "Frequency": "schedule_frequency",
                "Start": "task_date",
                "Owner": "assigned_to",
            },
        ),
    },
    "08_cmdb_assets_noisy.xlsx": {
        "Assets": (
            ("Asset", "Sheet1"),
            {"Asset tag": "ref_id", "Name": "name", "Description": "description"},
        ),
    },
}


def _analyze(filename):
    data = (SAMPLES / filename).read_bytes()
    result = mapping.analyze(io.BytesIO(data), FOLDERS, filename=filename)
    return {s["name"]: s for s in result["sheets"]}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "filename, sheet, target, columns",
    [
        (filename, sheet, target, columns)
        for filename, sheets in EXPECTED.items()
        for sheet, (target, columns) in sheets.items()
    ],
)
def test_sample_detection(filename, sheet, target, columns):
    analysed = _analyze(filename)[sheet]
    got = analysed.get("target")
    assert ((got["model_type"], got["sheet"]) if got else None) == target
    mapped = {
        header: s["key"]
        for header, s in (analysed.get("mapping") or {}).get("columns", {}).items()
    }
    assert {h: mapped.get(h) for h in columns} == columns


@pytest.mark.django_db
def test_title_banner_is_skipped():
    assert _analyze("01_cartographie_SI_FR.xlsx")["Processus métier"]["header_row"] == 4
    assert _analyze("02_isms_controls_tracker_EN.xlsx")["Controls"]["header_row"] == 2


@pytest.mark.django_db
def test_choice_values_in_french_are_matched():
    values = _analyze("01_cartographie_SI_FR.xlsx")["Processus métier"]["mapping"][
        "values"
    ]
    assert values["Type"]["Primaire"]["value"] == "PR"


@pytest.mark.django_db
def test_noisy_side_columns_are_left_unmapped():
    """Status, Impact, Link, Label and Owner match other objects' fields by name;
    on an asset list they must neither win the target nor be mapped."""
    sheet = _analyze("08_cmdb_assets_noisy.xlsx")["Assets"]
    mapped = set(sheet["mapping"]["columns"])
    assert not mapped & {"Status", "Impact", "Link", "Label", "Owner", "Comments"}
    assert "Name (2)" not in mapped


@pytest.mark.django_db
def test_relational_fields_are_not_guessed_from_loose_names():
    """Linked records are only mapped on an exact column name: "Affected assets"
    could just as well be a free-text note."""
    risk = _analyze("04_risk_register_FY2026.xlsx")["Risk register"]
    assert "Affected assets" not in risk["mapping"]["columns"]
    pentest = _analyze("05_pentest_findings_Q3.csv")["CSV"]
    assert "Affected asset" not in pentest["mapping"]["columns"]
