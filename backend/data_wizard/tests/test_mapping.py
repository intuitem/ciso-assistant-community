"""Mapped import: analyse any spreadsheet, map it onto a template, import or dry run."""

import io
import json
from unittest.mock import patch

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core import mailer
from core.models import AppliedControl, Asset
from data_wizard import mapping
from data_wizard.views import ModelType
from iam.models import User

ANALYZE_URL = "/api/data-wizard/mapping/analyze/"
IMPORT_URL = "/api/data-wizard/mapping/import/"
SCHEMA_URL = "/api/data-wizard/mapping/schema/"


def _workbook(sheets: dict[str, list[list]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# A real-world shape: a title banner above the table, French headers and values,
# a second sheet that belongs to another object type, and a free-text sheet.
SOURCE = {
    "Mesures": [
        ["Plan de traitement 2026"],
        [],
        ["ID", "Mesure", "Description", "Statut", "Priorité", "Commentaire"],
        ["M-001", "MFA on VPN", "Enable MFA", "En cours", 1, "x"],
        ["M-002", "EDR rollout", "Deploy EDR", "Fait", 2, ""],
        ["M-003", "Access review", "Quarterly", "A faire", 2, ""],
    ],
    "Inventaire": [
        ["Nom", "Description", "Type"],
        ["CRM", "Customer data", "Primaire"],
    ],
    "Readme": [["Free text, no table here"]],
}


def _file(sheets=SOURCE, name="source.xlsx"):
    return SimpleUploadedFile(name, _workbook(sheets))


def _controls_step(**options):
    return {
        "model_type": "AppliedControl",
        "options": options,
        "sheets": [
            {
                "source": "Mesures",
                "target": "Sheet1",
                "header_row": 3,
                "columns": {
                    "ID": "ref_id",
                    "Mesure": "name",
                    "Description": "description",
                    "Statut": "status",
                },
                "values": {
                    "Statut": {
                        "En cours": "in_progress",
                        "Fait": "active",
                        "A faire": "to_do",
                    }
                },
            }
        ],
    }


def _import(client, steps, folder, dry_run=False, sheets=SOURCE):
    return client.post(
        IMPORT_URL,
        {
            "file": _file(sheets),
            "mapping": json.dumps({"steps": steps}),
            "options": json.dumps({"folder_id": str(folder.id)}),
            "dry_run": "true" if dry_run else "false",
        },
        format="multipart",
    )


class TestDetection:
    def test_header_row_skips_title_banner(self):
        sources = mapping.read_source(io.BytesIO(_workbook(SOURCE)))
        mesures = next(s for s in sources if s.name == "Mesures")
        assert mapping.detect_header_row(mesures.raw) == 2

    def test_csv_is_one_sheet(self):
        sources = mapping.read_source(io.BytesIO(b"name;ref_id\nA;1\n"))
        assert [s.name for s in sources] == ["CSV"]
        assert sources[0].headers == ["name", "ref_id"]

    def test_value_suggestion_uses_translated_labels(self):
        targets = mapping._target_columns(ModelType.APPLIED_CONTROL, "Sheet1")
        status = next(t for t in targets if t.key == "status")
        assert mapping.suggest_value("En cours", status.choices)["value"] == (
            "in_progress"
        )
        assert mapping.suggest_value("in progres", status.choices)["reason"] == (
            "close"
        )
        assert mapping.suggest_value("Nope", status.choices) is None


@pytest.mark.django_db
class TestSchemaEndpoint:
    def test_lists_mappable_model_types(self, api_client):
        body = api_client.get(SCHEMA_URL).json()
        assert "AppliedControl" in body["model_types"]
        assert "TaskTemplate" in body["model_types"]
        assert "CyFunAssessment" not in body["model_types"]

    def test_describes_columns_and_choices(self, api_client):
        body = api_client.get(f"{SCHEMA_URL}AppliedControl/").json()
        columns = {c["key"]: c for c in body["sheets"][0]["columns"]}
        assert "name" in columns
        values = {c["value"] for c in columns["status"]["choices"]}
        assert {"to_do", "in_progress", "active"} <= values

    def test_multi_sheet_template(self, api_client):
        body = api_client.get(f"{SCHEMA_URL}TPRM/").json()
        assert [s["name"] for s in body["sheets"]][:2] == ["Entities", "Solutions"]

    def test_unmappable_type_is_404(self, api_client):
        assert api_client.get(f"{SCHEMA_URL}CyFunAssessment/").status_code == 404


@pytest.mark.django_db
class TestAnalyzeEndpoint:
    def test_describes_sheets_and_suggests_mapping(self, api_client, domain_folder):
        resp = api_client.post(ANALYZE_URL, {"file": _file()}, format="multipart")
        assert resp.status_code == 200
        sheets = {s["name"]: s for s in resp.json()["sheets"]}

        mesures = sheets["Mesures"]
        assert mesures["header_row"] == 3
        assert mesures["row_count"] == 3
        headers = [c["header"] for c in mesures["columns"]]
        assert headers[:4] == ["ID", "Mesure", "Description", "Statut"]

        assert mesures["target"]["model_type"] == "AppliedControl"
        columns = mesures["mapping"]["columns"]
        assert columns["Statut"] == {"key": "status", "reason": "name"}
        assert columns["Description"]["key"] == "description"
        assert mesures["mapping"]["values"]["Statut"]["En cours"]["value"] == (
            "in_progress"
        )

    def test_override_target_and_header_row(self, api_client):
        overrides = {"Inventaire": {"model_type": "Asset", "sheet": "Sheet1"}}
        resp = api_client.post(
            ANALYZE_URL,
            {"file": _file(), "overrides": json.dumps(overrides)},
            format="multipart",
        )
        inventaire = next(s for s in resp.json()["sheets"] if s["name"] == "Inventaire")
        assert inventaire["target"] == {"model_type": "Asset", "sheet": "Sheet1"}
        assert inventaire["mapping"]["columns"]["Type"]["key"] == "type"

    def test_rejects_bad_override(self, api_client):
        overrides = {"Mesures": {"model_type": "Asset", "sheet": "Nope"}}
        resp = api_client.post(
            ANALYZE_URL,
            {"file": _file(), "overrides": json.dumps(overrides)},
            format="multipart",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestMappedImport:
    def test_imports_with_mapped_columns_and_values(
        self, api_client, domain_folder, all_accessible
    ):
        resp = _import(api_client, [_controls_step()], domain_folder)
        assert resp.status_code == 200, resp.json()
        step = resp.json()["steps"][0]
        assert step["results"]["created"] == 3
        control = AppliedControl.objects.get(ref_id="M-001")
        assert control.name == "MFA on VPN"
        assert control.status == "in_progress"
        assert control.folder == domain_folder

    def test_dry_run_reports_without_writing(
        self, api_client, domain_folder, all_accessible
    ):
        resp = _import(api_client, [_controls_step()], domain_folder, dry_run=True)
        body = resp.json()
        assert body["dry_run"] is True
        assert body["steps"][0]["results"]["created"] == 3
        assert not AppliedControl.objects.filter(ref_id__startswith="M-").exists()

    def test_dry_run_reports_conflicts(self, api_client, domain_folder, all_accessible):
        AppliedControl.objects.create(
            name="MFA on VPN", ref_id="M-001", folder=domain_folder
        )
        resp = _import(
            api_client,
            [_controls_step(on_conflict="skip")],
            domain_folder,
            dry_run=True,
        )
        results = resp.json()["steps"][0]["results"]
        assert (results["created"], results["skipped"]) == (2, 1)
        assert AppliedControl.objects.filter(ref_id__startswith="M-").count() == 1

    def test_steps_run_in_order_and_dry_run_rolls_back_all(
        self, api_client, domain_folder, all_accessible
    ):
        assets = {
            "model_type": "Asset",
            "sheets": [
                {
                    "source": "Inventaire",
                    "target": "Sheet1",
                    "columns": {"Nom": "name", "Description": "description"},
                }
            ],
        }
        resp = _import(
            api_client, [assets, _controls_step()], domain_folder, dry_run=True
        )
        steps = resp.json()["steps"]
        assert [s["model_type"] for s in steps] == ["Asset", "AppliedControl"]
        assert steps[0]["results"]["created"] == 1
        assert not Asset.objects.filter(name="CRM").exists()

    def test_dry_run_sends_no_mail(self, api_client, domain_folder, all_accessible):
        users = {
            "model_type": "User",
            "sheets": [
                {"source": "People", "target": "Sheet1", "columns": {"Mail": "email"}}
            ],
        }
        sheets = {"People": [["Mail"], ["new.person@example.com"]]}
        with (
            patch.object(mailer, "mailing_enabled", return_value=True),
            patch.object(mailer, "active_mailers") as active_mailers,
        ):
            resp = _import(api_client, [users], domain_folder, True, sheets)
        assert resp.json()["steps"][0]["results"]["created"] == 1
        active_mailers.assert_not_called()
        assert not User.objects.filter(email="new.person@example.com").exists()

    @pytest.mark.parametrize(
        "change, error",
        [
            ({"columns": {"Mesure": "nope"}}, "UnknownColumns"),
            ({"columns": {"Mesure": "name", "ID": "name"}}, "DuplicateTargetColumns"),
            ({"target": "Nope"}, "UnknownTargetSheet"),
            ({"source": "Nope"}, "UnknownSourceSheet"),
            ({"columns": {"Missing": "name"}}, "MissingSourceColumns"),
            ({"header_row": 0}, "InvalidHeaderRow"),
        ],
    )
    def test_invalid_mapping_is_rejected_before_any_write(
        self, api_client, domain_folder, all_accessible, change, error
    ):
        step = _controls_step()
        step["sheets"][0].update(change)
        resp = _import(api_client, [step], domain_folder)
        assert resp.status_code == 400
        assert resp.json()["detail"].startswith(error)
        assert not AppliedControl.objects.exists()


def test_mailer_suppressed_yields_a_silent_backend():
    with mailer.suppressed():
        mailer.send("subject", "body", "someone@example.com")
    with (
        pytest.raises(mailer.NoMailerAvailable),
        patch.object(mailer, "active_mailers", return_value=[]),
    ):
        mailer.send("subject", "body", "someone@example.com")


class TestReadableError:
    def test_flattens_serializer_errors(self):
        from rest_framework import serializers

        from data_wizard.views import readable_error

        class S(serializers.Serializer):
            eta = serializers.DateField()
            name = serializers.CharField()

        s = S(data={"eta": "Q1 2027"})
        s.is_valid()
        text = readable_error(s.errors)
        assert "ErrorDetail" not in text
        assert text.startswith("eta: Date has wrong format.")
        assert text.endswith("; name: This field is required")
        assert ".;" not in text

    def test_raised_validation_error_and_plain_text(self):
        from rest_framework.exceptions import ValidationError

        from data_wizard.views import readable_error

        error = ValidationError(
            {"non_field_errors": ["Duplicate name"], "country": ["Bad"]}
        )
        assert readable_error(error) == "Duplicate name; country: Bad"
        assert readable_error("already readable") == "already readable"


@pytest.mark.django_db
def test_row_errors_are_readable(api_client, domain_folder, all_accessible):
    step = _controls_step(on_conflict="skip")
    step["sheets"][0]["columns"]["Priorité"] = "start_date"
    resp = _import(api_client, [step], domain_folder, dry_run=True)
    errors = resp.json()["steps"][0]["results"]["errors"]
    assert errors
    assert all("ErrorDetail" not in e["error"] for e in errors)
    assert errors[0]["error"].startswith("start_date: Date has wrong format.")


@pytest.mark.django_db
class TestOwners:
    """Owners are mapped by user email or team name; the ones nobody matches are
    reported as warnings and the row is still imported."""

    def _owner_file(self):
        return {
            "Mesures": [
                ["ID", "Mesure", "Responsable"],
                ["M-001", "MFA on VPN", "admin@datawizard.test"],
                ["M-002", "EDR rollout", "Network team"],
                ["M-003", "Access review", "admin@datawizard.test; ghost@nowhere.test"],
            ]
        }

    def _step(self, model_type):
        return {
            "model_type": model_type,
            "options": {"on_conflict": "skip"},
            "sheets": [
                {
                    "source": "Mesures",
                    "target": "Sheet1",
                    "columns": {
                        "ID": "ref_id",
                        "Mesure": "name",
                        "Responsable": "owner",
                    },
                }
            ],
        }

    @pytest.fixture
    def team(self, domain_folder):
        from core.models import Team

        return Team.objects.create(name="Network team", folder=domain_folder)

    def test_owner_is_mappable_where_the_template_omits_it(self, api_client):
        for model_type in ("AppliedControl", "Policy"):
            body = api_client.get(f"{SCHEMA_URL}{model_type}/").json()
            keys = [c["key"] for c in body["sheets"][0]["columns"]]
            assert "owner" in keys

    @pytest.mark.parametrize("model_type", ["AppliedControl", "Policy"])
    def test_owners_by_email_and_team(
        self, api_client, domain_folder, admin_user, team, all_accessible, model_type
    ):
        resp = _import(
            api_client,
            [self._step(model_type)],
            domain_folder,
            sheets=self._owner_file(),
        )
        results = resp.json()["steps"][0]["results"]
        assert results["created"] == 3
        from core.models import Actor

        person = Actor.objects.get(user=admin_user).id
        squad = Actor.objects.get(team=team).id
        owners = {
            c.ref_id: {a.id for a in c.owner.all()}
            for c in AppliedControl.objects.filter(ref_id__startswith="M-")
        }
        assert owners == {"M-001": {person}, "M-002": {squad}, "M-003": {person}}
        warnings = [w["error"] for w in results["warnings"]]
        assert warnings == ["owner: no user or team found for ghost@nowhere.test"]


@pytest.mark.django_db
@pytest.mark.parametrize("separator", [";", ",", "|", "\n"])
def test_owner_separators_are_the_same_everywhere(admin_user, domain_folder, separator):
    from core.models import Actor, Team
    from data_wizard.views import _resolve_actors, _resolve_owners

    team = Team.objects.create(name="Network team", folder=domain_folder)
    value = f"{admin_user.email}{separator} Network team{separator}{admin_user.email}"
    expected = [Actor.objects.get(user=admin_user).id, Actor.objects.get(team=team).id]
    assert _resolve_owners(value) == expected
    assert _resolve_actors(value)[:2] == expected
