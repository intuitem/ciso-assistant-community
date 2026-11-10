"""Scenario selection: `scenario__*` params narrow every view of a risk assessment."""

import csv
import io
from uuid import uuid4

import pymupdf
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from knox.models import AuthToken
from openpyxl import load_workbook
from rest_framework.test import APIClient

from core.models import (
    AppliedControl,
    Asset,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    Threat,
)
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
        # Takes one value: the second would be dropped without a word.
        "scenario__within_tolerance=YES&scenario__within_tolerance=NO",
        "scenario__current_impact=1&scenario__current_impact=2",
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


def _options(client, ra, name, query=""):
    res = client.get(
        f"/api/risk-assessments/{ra.id}/scenario-selection/options/"
        f"?filter={name}&{query}"
    )
    assert res.status_code == 200, res.content
    return res.json()


def _threats(setup, links):
    """Create one threat per name, linked to the scenarios listed for it."""
    threats = {}
    for name, ref_ids in links.items():
        threat = Threat.objects.create(name=name, folder=Folder.get_root_folder())
        for ref_id in ref_ids:
            setup["scenarios"][ref_id].threats.add(threat)
        threats[name] = threat
    return threats


def _hidden_domain():
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="hidden domain",
        content_type=Folder.ContentType.DOMAIN,
    )


def _reader(domain):
    reader = User.objects.create_user("reader@scenario-selection-tests.com")
    group = UserGroup.objects.create(name="selection-readers", folder=domain)
    group.user_set.add(reader)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=RoleCodename.READER.value),
        folder=domain,
        is_recursive=True,
    ).perimeter_folders.add(domain)
    return reader


@pytest.mark.django_db
def test_selection_carries_related_labels_not_related_options(admin_client, setup):
    ra = setup["ra"]
    threats = _threats(setup, {"Ransomware": ["R1"], "Phishing": ["R2"]})

    res = admin_client.get(
        f"/api/risk-assessments/{ra.id}/scenario-selection/"
        f"?scenario__threats={threats['Ransomware'].id}"
    )
    body = res.json()

    assert set(body["facets"]) == {
        "within_tolerance",
        "treatment",
        "current_level",
        "residual_level",
    }
    assert body["related_filters"]["threats"] == {
        "has_options": True,
        "selected": [{"value": str(threats["Ransomware"].id), "label": "Ransomware"}],
    }
    assert body["related_filters"]["assets"] == {"has_options": False, "selected": []}


@pytest.mark.django_db
def test_related_options_are_paged_in_a_stable_order(admin_client, setup):
    ra = setup["ra"]
    threats = _threats(
        setup,
        {
            "delta": ["R1"],
            "Bravo": ["R2"],
            "alpha": ["R1", "R2", "R3"],
            "Charlie": ["R3"],
            "echo": ["R1", "R2"],
        },
    )
    elsewhere = Threat.objects.create(name="elsewhere", folder=Folder.get_root_folder())
    other_ra = RiskAssessment.objects.create(
        name="other ra", folder=ra.folder, risk_matrix=ra.risk_matrix
    )
    _scenario(other_ra, "X1", HIGH).threats.add(elsewhere, threats["delta"])

    first = _options(admin_client, ra, "threats", "limit=2")
    rest = _options(admin_client, ra, "threats", "limit=10&offset=2")

    # Most scenarios first, then by label whatever its case. Links to other
    # assessments neither add options nor count.
    assert first["count"] == rest["count"] == 5
    assert first["next"] is not None and rest["next"] is None
    assert [(o["label"], o["count"]) for o in first["results"] + rest["results"]] == [
        ("alpha", 3),
        ("echo", 2),
        ("Bravo", 1),
        ("Charlie", 1),
        ("delta", 1),
    ]
    assert first["results"][0]["value"] == str(threats["alpha"].id)


@pytest.mark.django_db
def test_related_option_counts_follow_the_other_filters(admin_client, setup):
    ra = setup["ra"]
    threats = _threats(
        setup, {"Ransomware": ["R1", "R3"], "Phishing": ["R1", "R2"], "Flood": ["R3"]}
    )

    body = _options(
        admin_client,
        ra,
        "threats",
        f"scenario__within_tolerance=NO&scenario__threats={threats['Flood'].id}",
    )

    # Counted against within_tolerance=NO only (R1, R2): the filter's own values
    # do not narrow its options, they only come first.
    assert [(o["label"], o["count"]) for o in body["results"]] == [
        ("Flood", 0),
        ("Phishing", 2),
        ("Ransomware", 1),
    ]


@pytest.mark.django_db
def test_related_options_search_their_label(admin_client, setup):
    ra = setup["ra"]
    _threats(setup, {"Ransomware": ["R1"], "Phishing": ["R2"]})
    ada = User.objects.create_user(
        "ada@scenario-selection-tests.com", first_name="Ada", last_name="Lovelace"
    )
    alan = User.objects.create_user("alan@scenario-selection-tests.com")
    setup["scenarios"]["R1"].owner.add(ada.actor, alan.actor)

    def labels(name, q):
        return [
            o["label"] for o in _options(admin_client, ra, name, f"q={q}")["results"]
        ]

    # The risk assessment itself is searched with `search`, not `q`.
    assert labels("threats", "RANSOM") == ["Ransomware"]
    assert labels("threats", "nothing") == []
    assert labels("owner", "ada love") == ["Ada Lovelace"]
    assert labels("owner", "alan@") == ["alan@scenario-selection-tests.com"]


@pytest.mark.django_db
def test_related_options_cost_the_same_whatever_their_number(admin_client, setup):
    ra = setup["ra"]

    def queries():
        with CaptureQueriesContext(connection) as captured:
            _options(admin_client, ra, "owner")
        return len(captured)

    def add_owners(count, start):
        for i in range(start, start + count):
            user = User.objects.create_user(f"owner{i}@scenario-selection-tests.com")
            setup["scenarios"]["R1"].owner.add(user.actor)

    queries()  # the first request also fills the per-process caches
    add_owners(2, 0)
    few = queries()
    add_owners(10, 2)

    assert queries() == few


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["", "treatment", "applied_controls"])
def test_related_options_reject_other_filters(admin_client, setup, name):
    res = admin_client.get(
        f"/api/risk-assessments/{setup['ra'].id}/scenario-selection/options/"
        f"?filter={name}"
    )
    assert res.status_code == 400, res.content


@pytest.mark.django_db
def test_related_options_never_name_what_the_user_cannot_view(setup, domain):
    ra = setup["ra"]
    r1 = setup["scenarios"]["R1"]
    hidden = Asset.objects.create(name="hidden asset", folder=_hidden_domain())
    visible = Asset.objects.create(name="visible asset", folder=domain)
    r1.assets.add(hidden, visible)
    client = _client(_reader(domain))

    body = _options(client, ra, "assets")
    assert [o["label"] for o in body["results"]] == ["visible asset"]
    assert body["count"] == 1

    # Applying a hidden value still filters, but its label is not given away.
    res = client.get(
        f"/api/risk-assessments/{ra.id}/scenario-selection/"
        f"?scenario__assets={hidden.id}"
    )
    assert res.json()["related_filters"]["assets"] == {
        "has_options": True,
        "selected": [],
    }

    r1.assets.remove(visible)
    res = client.get(f"/api/risk-assessments/{ra.id}/scenario-selection/")
    assert res.json()["related_filters"]["assets"]["has_options"] is False


@pytest.mark.django_db
def test_selection_never_reveals_controls_the_user_cannot_view(setup, domain):
    hidden = _control(_hidden_domain(), "hidden control")
    setup["scenarios"]["R1"].applied_controls.add(hidden)

    rows = _plan(_client(_reader(domain)), setup["ra"], "scenario__within_tolerance=NO")

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
def test_exports_never_name_what_the_user_cannot_view(setup, domain):
    ra = setup["ra"]
    r1 = setup["scenarios"]["R1"]
    hidden = Asset.objects.create(name="hidden asset", folder=_hidden_domain())
    visible = Asset.objects.create(name="visible asset", folder=domain)
    r1.assets.add(hidden, visible)
    client = _client(_reader(domain))
    query = f"scenario__assets={hidden.id}&scenario__assets={visible.id}"

    for path in ("risk_assessment_xlsx", "action_plan_excel"):
        res = client.get(f"/api/risk-assessments/{ra.id}/{path}/?{query}")
        sheet = load_workbook(io.BytesIO(res.content))["Selection"]
        # The hidden value still filters: it is stated by its id, not its name.
        assert sheet["A2"].value == "assets", path
        assert sheet["B2"].value == f"visible asset, {hidden.id}", path

    for path in ("risk_assessment_pdf", "action_plan_pdf"):
        res = client.get(f"/api/risk-assessments/{ra.id}/{path}/?{query}")
        assert res.status_code == 200, path
        # A line break can fall inside the id.
        assert str(hidden.id) in "".join(_pdf_text(res.content).split()), path


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
