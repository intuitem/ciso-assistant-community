import csv
import io
import json
import zipfile

import pytest
from rest_framework.test import APIClient

from core.models import Asset
from iam.models import Folder
from tprm.models import Contract, Entity, Solution

DORA_EXPORT_URL = "/api/entities/generate_dora_roi/"


@pytest.fixture
def dora_data(app_config):
    """Create a complete DORA data set for API testing."""
    root_folder = Folder.get_root_folder()

    # startup() creates a builtin "Main" entity — update it with DORA fields
    main_entity = Entity.get_main_entity()
    main_entity.name = "API Test Entity"
    main_entity.legal_identifiers = {"LEI": "APITESTLEI0000000000"}
    main_entity.country = "BE"
    main_entity.currency = "EUR"
    main_entity.dora_entity_type = "eba_CT:x12"
    main_entity.dora_competent_authority = "FSMA"
    main_entity.save()

    provider = Entity.objects.create(
        name="Cloud Provider Inc",
        legal_identifiers={"LEI": "PROV0000000000000000"},
        country="US",
        dora_provider_person_type="eba_CT:x212",
    )

    subsidiary = Entity.objects.create(
        name="Sub Entity",
        legal_identifiers={"LEI": "SUB00000000000000001"},
        country="FR",
        currency="EUR",
        parent_entity=main_entity,
        dora_provider_person_type="eba_CT:x212",
    )

    branch = Entity.objects.create(
        name="Branch Office",
        legal_identifiers={"VAT": "BE0111111111"},
        country="BE",
        parent_entity=main_entity,
    )

    business_function = Asset.objects.create(
        name="Core Banking",
        is_business_function=True,
        disaster_recovery_objectives={
            "objectives": {"rto": {"value": 4}, "rpo": {"value": 2}}
        },
        dora_criticality_assessment="eba_BT:x28",
    )

    solution = Solution.objects.create(
        name="Cloud Hosting",
        provider_entity=provider,
        dora_ict_service_type="cloud",
        storage_of_data=True,
        data_location_storage="US",
        data_location_processing="IE",
    )
    solution.assets.add(business_function)

    active_contract = Contract.objects.create(
        name="Main Contract",
        ref_id="API-CA-001",
        provider_entity=provider,
        beneficiary_entity=main_entity,
        annual_expense=200000,
        currency="EUR",
        is_intragroup=False,
        status=Contract.Status.ACTIVE,
    )
    active_contract.solutions.add(solution)

    second_contract = Contract.objects.create(
        name="Second Contract",
        ref_id="API-CA-002",
        provider_entity=provider,
        beneficiary_entity=main_entity,
        annual_expense=50000,
        currency="EUR",
        is_intragroup=False,
        status=Contract.Status.ACTIVE,
    )
    second_contract.solutions.add(solution)

    return {
        "main_entity": main_entity,
        "provider": provider,
        "subsidiary": subsidiary,
        "branch": branch,
        "business_function": business_function,
        "solution": solution,
        "active_contract": active_contract,
        "second_contract": second_contract,
    }


def _read_csv_from_zip(content, filename):
    """Read a CSV file from zip bytes, searching with or without folder prefix."""
    buf = io.BytesIO(content)
    with zipfile.ZipFile(buf, "r") as z:
        # Find the file — may be nested in a folder prefix
        matches = [n for n in z.namelist() if n.endswith(filename)]
        assert matches, f"{filename} not found in zip. Files: {z.namelist()}"
        with z.open(matches[0]) as f:
            return list(csv.reader(io.StringIO(f.read().decode("utf-8"))))


def _read_json_from_zip(content, filename):
    buf = io.BytesIO(content)
    with zipfile.ZipFile(buf, "r") as z:
        matches = [n for n in z.namelist() if n.endswith(filename)]
        assert matches, f"{filename} not found in zip. Files: {z.namelist()}"
        with z.open(matches[0]) as f:
            return json.loads(f.read().decode("utf-8"))


# ===========================================================================
# Unauthenticated access
# ===========================================================================


@pytest.mark.django_db
class TestDoraExportUnauthenticated:
    def test_returns_401(self):
        client = APIClient()
        response = client.get(DORA_EXPORT_URL)
        assert response.status_code == 401


# ===========================================================================
# No data / invalid data
# ===========================================================================


@pytest.mark.django_db
class TestDoraExportNoData:
    def test_no_main_entity_returns_400(self, authenticated_client, app_config):
        response = authenticated_client.get(DORA_EXPORT_URL)
        assert response.status_code == 400

    def test_main_entity_without_any_identifier_returns_400(
        self, authenticated_client, app_config
    ):
        # startup() creates a builtin Main entity — update it to have no identifiers
        main_entity = Entity.get_main_entity()
        main_entity.legal_identifiers = {}
        main_entity.save()
        response = authenticated_client.get(DORA_EXPORT_URL)
        assert response.status_code == 400


# ===========================================================================
# Basic endpoint behavior
# ===========================================================================


@pytest.mark.django_db
class TestDoraExportEndpoint:
    def test_returns_200(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        assert response.status_code == 200

    def test_content_type_is_zip(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        assert response["Content-Type"] == "application/zip"

    def test_content_disposition_has_filename(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        assert "attachment; filename=" in response["Content-Disposition"]

    def test_filename_matches_lei_pattern(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        disposition = response["Content-Disposition"]
        assert "LEI_APITESTLEI0000000000" in disposition
        assert "IND_FSMA" in disposition
        assert disposition.endswith('.zip"')

    def test_zip_is_valid(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        buf = io.BytesIO(response.content)
        assert zipfile.is_zipfile(buf)

    def test_zip_contains_all_19_files(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        buf = io.BytesIO(response.content)
        with zipfile.ZipFile(buf, "r") as z:
            names = z.namelist()
            expected_suffixes = [
                "b_01.01.csv",
                "b_01.02.csv",
                "b_01.03.csv",
                "b_02.01.csv",
                "b_02.02.csv",
                "b_02.03.csv",
                "b_03.01.csv",
                "b_03.02.csv",
                "b_03.03.csv",
                "b_04.01.csv",
                "b_05.01.csv",
                "b_05.02.csv",
                "b_06.01.csv",
                "b_07.01.csv",
                "b_99.01.csv",
                "FilingIndicators.csv",
                "parameters.csv",
                "reportPackage.json",
                "report.json",
            ]
            for suffix in expected_suffixes:
                matches = [n for n in names if n.endswith(suffix)]
                assert matches, (
                    f"Missing file ending with {suffix}. Zip contains: {names}"
                )

    def test_draft_contracts_excluded(self, authenticated_client, dora_data):
        draft = Contract.objects.create(
            name="Draft Contract",
            ref_id="DRAFT-001",
            provider_entity=dora_data["provider"],
            beneficiary_entity=dora_data["main_entity"],
            status=Contract.Status.DRAFT,
        )
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_02.01.csv")
        refs = [r[0] for r in rows[1:]]
        assert "DRAFT-001" not in refs
        draft.delete()

    def test_each_csv_has_header_row(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        buf = io.BytesIO(response.content)
        with zipfile.ZipFile(buf, "r") as z:
            csv_files = [n for n in z.namelist() if n.endswith(".csv")]
            for csv_file in csv_files:
                with z.open(csv_file) as f:
                    rows = list(csv.reader(io.StringIO(f.read().decode("utf-8"))))
                    assert len(rows) >= 1, f"{csv_file} has no header row"

    def test_parameters_csv_has_correct_values(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "parameters.csv")
        params = dict(rows[1:])
        assert "rs:APITESTLEI0000000000.IND" == params["entityID"]
        assert params["baseCurrency"] == "iso4217:EUR"

    def test_filing_indicators_all_true(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "FilingIndicators.csv")
        for row in rows[1:]:
            assert row[1] == "true"


# ===========================================================================
# End-to-end content validation
# ===========================================================================


@pytest.mark.django_db
class TestDoraExportEndToEnd:
    def test_b0101_has_correct_entity_data(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_01.01.csv")
        assert len(rows) == 2
        assert rows[1][0] == "APITESTLEI0000000000"
        assert rows[1][1] == "API Test Entity"
        assert rows[1][2] == "eba_GA:BE"

    def test_b0102_includes_main_and_subsidiaries_not_branches(
        self, authenticated_client, dora_data
    ):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_01.02.csv")
        leis = [r[0] for r in rows[1:]]
        assert "APITESTLEI0000000000" in leis
        assert "SUB00000000000000001" in leis
        # Branch VAT should NOT appear in b_01.02
        assert "BE0111111111" not in leis

    def test_b0103_includes_only_branches(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_01.03.csv")
        codes = [r[0] for r in rows[1:]]
        assert "BE0111111111" in codes

    def test_b0201_includes_all_active_contracts(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_02.01.csv")
        refs = [r[0] for r in rows[1:]]
        assert "API-CA-001" in refs
        assert "API-CA-002" in refs

    def test_b0202_has_correct_contract_function_rows(
        self, authenticated_client, dora_data
    ):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_02.02.csv")
        # At least one data row for API-CA-001 with the business function
        data = rows[1:]
        assert len(data) >= 1
        main_rows = [r for r in data if r[0] == "API-CA-001"]
        assert len(main_rows) >= 1
        assert main_rows[0][1] == "APITESTLEI0000000000"  # beneficiary

    def test_b0301_has_row_per_active_contract(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_03.01.csv")
        data = rows[1:]
        # All active contracts get a row
        assert len(data) >= 2
        for row in data:
            assert row[1] == "APITESTLEI0000000000"

    def test_b0501_aggregates_expenses_per_provider(
        self, authenticated_client, dora_data
    ):
        response = authenticated_client.get(DORA_EXPORT_URL)
        rows = _read_csv_from_zip(response.content, "b_05.01.csv")
        data = rows[1:]
        prov_row = next((r for r in data if r[0] == "PROV0000000000000000"), None)
        assert prov_row is not None
        # 200000 + 50000 = 250000
        assert float(prov_row[9]) == 250000.0

    def test_report_json_extends_dora_taxonomy(self, authenticated_client, dora_data):
        response = authenticated_client.get(DORA_EXPORT_URL)
        data = _read_json_from_zip(response.content, "report.json")
        assert (
            "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/dora/4.0/mod/dora.json"
            in data["documentInfo"]["extends"]
        )
