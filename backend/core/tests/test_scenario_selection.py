"""Scenario selection: `scenario__*` params narrow every view of a risk assessment."""

import csv
import io
from uuid import uuid4

import pymupdf
import pytest
from knox.models import AuthToken
from openpyxl import load_workbook
from rest_framework.test import APIClient

from core.models import AppliedControl, RiskAssessment, RiskMatrix, RiskScenario, Threat
from core.startup import startup
from iam.models import Folder, Role, RoleAssignment, RoleCodename, User, UserGroup
from test_fixtures import RISK_MATRIX_JSON_DEFINITION

# Test matrix: levels Low(0) / Medium(1) / High(2), grid[proba][impact].
LOW, MEDIUM, HIGH = (0, 0), (1, 1), (2, 2)


@pytest.fixture
def app_config():
    startup(sender=None, **{})


@pytest.fixture
def domain(app_config):
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="selection domain",
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser("admin@scenario-selection-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    return _client(admin)


def _client(user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


def _scenario(ra, ref_id, level, treatment="mitigate", **kwargs):
    proba, impact = level
    return RiskScenario.objects.create(
        risk_assessment=ra,
        ref_id=ref_id,
        name=f"Scenario {ref_id}",
        current_proba=proba,
        current_impact=impact,
        treatment=treatment,
        **kwargs,
    )


def _control(domain, name):
    return AppliedControl.objects.create(name=name, folder=domain)


@pytest.fixture
def setup(domain):
    """Tolerance is Medium: R1 and R2 are not tolerable, R3 is."""
    matrix = RiskMatrix.objects.create(
        name="selection matrix",
        folder=Folder.get_root_folder(),
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    ra = RiskAssessment.objects.create(
        name="selection ra", folder=domain, risk_matrix=matrix, risk_tolerance=1
    )
    r1 = _scenario(ra, "R1", HIGH)
    r2 = _scenario(ra, "R2", HIGH, treatment="accept")
    r3 = _scenario(ra, "R3", LOW)
    only_r1 = _control(domain, "only R1")
    only_r3 = _control(domain, "only R3")
    shared = _control(domain, "R1 and R3")
    existing_r2 = _control(domain, "existing on R2")
    r1.applied_controls.add(only_r1, shared)
    r3.applied_controls.add(only_r3, shared)
    r2.existing_applied_controls.add(existing_r2)
    return {
        "ra": ra,
        "scenarios": {"R1": r1, "R2": r2, "R3": r3},
        "controls": {
            "only_r1": only_r1,
            "only_r3": only_r3,
            "shared": shared,
            "existing_r2": existing_r2,
        },
    }


def _plan(client, ra, query=""):
    res = client.get(f"/api/risk-assessments/{ra.id}/action-plan/?{query}")
    assert res.status_code == 200, res.content
    return {row["name"]: row for row in res.json()["results"]}


@pytest.mark.django_db
def test_without_a_selection_the_action_plan_is_unchanged(admin_client, setup):
    rows = _plan(admin_client, setup["ra"])

    assert set(rows) == {"only R1", "only R3", "R1 and R3", "existing on R2"}
    assert {s["str"] for s in rows["R1 and R3"]["risk_scenarios"]} == {
        "R1 - Scenario R1",
        "R3 - Scenario R3",
    }
    assert "risk_scenarios_outside_selection" not in rows["R1 and R3"]


@pytest.mark.django_db
def test_selection_keeps_controls_of_selected_scenarios(admin_client, setup):
    rows = _plan(admin_client, setup["ra"], "scenario__within_tolerance=NO")

    # R1 and R2 are not tolerable; the control shared with tolerable R3 stays.
    assert set(rows) == {"only R1", "R1 and R3", "existing on R2"}
    shared = rows["R1 and R3"]
    assert [s["str"] for s in shared["risk_scenarios"]] == ["R1 - Scenario R1"]
    assert [s["str"] for s in shared["risk_scenarios_outside_selection"]] == [
        "R3 - Scenario R3"
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "link_type, expected",
    [
        ("additional", {"only R1", "R1 and R3"}),
        ("existing", {"existing on R2"}),
        ("all", {"only R1", "R1 and R3", "existing on R2"}),
    ],
)
def test_link_type_picks_the_relation(admin_client, setup, link_type, expected):
    rows = _plan(
        admin_client,
        setup["ra"],
        f"scenario__within_tolerance=NO&link_type={link_type}",
    )
    assert set(rows) == expected


@pytest.mark.django_db
def test_selection_and_control_filters_combine(admin_client, setup):
    controls = setup["controls"]
    controls["only_r1"].status = "active"
    controls["only_r1"].save()

    rows = _plan(
        admin_client, setup["ra"], "scenario__within_tolerance=NO&status=active"
    )

    assert set(rows) == {"only R1"}


@pytest.mark.django_db
def test_unprefixed_scenario_params_are_not_the_selection(admin_client, setup):
    rows = _plan(admin_client, setup["ra"], "treatment=accept")
    assert len(rows) == 4


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query",
    [
        "scenario__nope=1",
        # Fixed by the assessment, so not part of the selection.
        f"scenario__risk_assessment={uuid4()}",
        "scenario__folder=x",
        "link_type=everything",
    ],
)
def test_bad_selection_params_are_rejected(admin_client, setup, query):
    res = admin_client.get(
        f"/api/risk-assessments/{setup['ra'].id}/action-plan/?{query}"
    )
    assert res.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query",
    [
        "within_tolerance=NO",
        "within_tolerance=YES",
        "treatment=mitigate",
        "treatment=accept&within_tolerance=NO",
        "current_level=2",
        "current_level=0&current_level=2",
    ],
)
def test_selection_matches_the_scenario_list(admin_client, setup, query):
    """The selection is RiskScenarioFilter: same params, same scenarios."""
    ra = setup["ra"]
    listed = admin_client.get(f"/api/risk-scenarios/?risk_assessment={ra.id}&{query}")
    prefixed = "&".join(f"scenario__{part}" for part in query.split("&"))
    selected = admin_client.get(
        f"/api/risk-assessments/{ra.id}/scenario-selection/?{prefixed}"
    )

    assert selected.status_code == 200, selected.content
    assert set(selected.json()["ids"]) == {r["id"] for r in listed.json()["results"]}


@pytest.mark.django_db
def test_stale_values_are_reported_not_fatal(admin_client, setup):
    ra = setup["ra"]
    threat = Threat.objects.create(name="Ransomware", folder=Folder.get_root_folder())
    setup["scenarios"]["R1"].threats.add(threat)
    gone = uuid4()

    res = admin_client.get(
        f"/api/risk-assessments/{ra.id}/scenario-selection/"
        f"?scenario__threats={threat.id}&scenario__threats={gone}"
    )

    assert res.status_code == 200, res.content
    body = res.json()
    assert body["ids"] == [str(setup["scenarios"]["R1"].id)]
    assert body["ignored"] == [{"filter": "threats", "value": str(gone)}]


@pytest.mark.django_db
def test_facets_count_each_value_against_the_other_filters(admin_client, setup):
    ra = setup["ra"]
    res = admin_client.get(
        f"/api/risk-assessments/{ra.id}/scenario-selection/"
        "?scenario__within_tolerance=NO&scenario__treatment=mitigate"
    )
    body = res.json()

    assert body["count"] == 1 and body["total"] == 3
    treatment = {f["value"]: f["count"] for f in body["facets"]["treatment"]}
    # Counted against within_tolerance=NO only: R1 mitigates, R2 accepts.
    assert treatment["mitigate"] == 1 and treatment["accept"] == 1
    tolerance = {f["value"]: f["count"] for f in body["facets"]["within_tolerance"]}
    # Counted against treatment=mitigate only: R1 is not tolerable, R3 is.
    assert tolerance == {"NO": 1, "YES": 1}


@pytest.mark.django_db
def test_no_tolerance_means_no_tolerance_facet(admin_client, setup):
    ra = setup["ra"]
    ra.risk_tolerance = -1
    ra.save()
    body = admin_client.get(f"/api/risk-assessments/{ra.id}/scenario-selection/").json()
    assert body["facets"]["within_tolerance"] == []


@pytest.mark.django_db
def test_selection_never_reveals_controls_the_user_cannot_view(setup, domain):
    other = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="hidden domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    hidden = _control(other, "hidden control")
    setup["scenarios"]["R1"].applied_controls.add(hidden)

    reader = User.objects.create_user("reader@scenario-selection-tests.com")
    group = UserGroup.objects.create(name="selection-readers", folder=domain)
    group.user_set.add(reader)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=RoleCodename.READER.value),
        folder=domain,
        is_recursive=True,
    ).perimeter_folders.add(domain)

    rows = _plan(_client(reader), setup["ra"], "scenario__within_tolerance=NO")

    assert "hidden control" not in rows
    assert "only R1" in rows


@pytest.mark.django_db
def test_csv_export_holds_only_the_selection(admin_client, setup):
    ra = setup["ra"]
    res = admin_client.get(
        f"/api/risk-assessments/{ra.id}/risk_assessment_csv/?scenario__within_tolerance=NO"
    )
    rows = list(csv.reader(io.StringIO(res.content.decode("utf-8-sig")), delimiter=";"))
    assert [r[0] for r in rows[1:]] == ["R1", "R2"]


@pytest.mark.django_db
def test_xlsx_exports_state_their_selection(admin_client, setup):
    ra = setup["ra"]
    for path in ("risk_assessment_xlsx", "action_plan_excel"):
        filtered = admin_client.get(
            f"/api/risk-assessments/{ra.id}/{path}/?scenario__within_tolerance=NO"
        )
        book = load_workbook(io.BytesIO(filtered.content))
        assert "Selection" in book.sheetnames, path
        assert book["Selection"]["B1"].value == "2 / 3"

        unfiltered = admin_client.get(f"/api/risk-assessments/{ra.id}/{path}/")
        assert (
            "Selection" not in load_workbook(io.BytesIO(unfiltered.content)).sheetnames
        )


@pytest.mark.django_db
def test_action_plan_excel_follows_the_action_plan(admin_client, setup):
    ra = setup["ra"]
    res = admin_client.get(
        f"/api/risk-assessments/{ra.id}/action_plan_excel/"
        "?scenario__within_tolerance=NO&link_type=additional"
    )
    sheet = load_workbook(io.BytesIO(res.content))["Action Plan"]
    assert {row[0].value for row in sheet.iter_rows(min_row=2)} == {
        "only R1",
        "R1 and R3",
    }


def _pdf_text(content):
    return "".join(
        page.get_text() for page in pymupdf.open(stream=content, filetype="pdf")
    )


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["risk_assessment_pdf", "action_plan_pdf"])
@pytest.mark.parametrize(
    "lang, statement",
    [("en", "Tolerable: No"), ("fr", "Tolérable : Non")],
)
def test_pdf_exports_state_their_selection(admin_client, setup, path, lang, statement):
    ra = setup["ra"]
    admin = User.objects.get(email="admin@scenario-selection-tests.com")
    admin.preferences = {**(admin.preferences or {}), "lang": lang}
    admin.save()

    filtered = admin_client.get(
        f"/api/risk-assessments/{ra.id}/{path}/?scenario__within_tolerance=NO"
    )
    assert filtered.status_code == 200
    text = _pdf_text(filtered.content)
    assert statement in text
    assert "2/3" in text, "every page footer carries the count"

    unfiltered = admin_client.get(f"/api/risk-assessments/{ra.id}/{path}/")
    assert statement not in _pdf_text(unfiltered.content)


@pytest.mark.django_db
def test_flash_mode_filter_carries_the_selection(admin_client, setup):
    ra = setup["ra"]

    def names(query):
        res = admin_client.get(
            f"/api/applied-controls/?risk_assessments={ra.id}&{query}"
        )
        return {row["name"] for row in res.json()["results"]}

    # Historical meaning without selection params: additional measures only.
    assert names("") == {"only R1", "only R3", "R1 and R3"}
    assert names("scenario__within_tolerance=NO") == {"only R1", "R1 and R3"}
    assert names("scenario__within_tolerance=NO&link_type=all") == {
        "only R1",
        "R1 and R3",
        "existing on R2",
    }
