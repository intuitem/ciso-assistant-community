import csv
import io
import json
import re
import unittest
import zipfile
from datetime import date
from unittest.mock import patch

from django.test import TestCase

from core.models import Asset
from tprm.models import Entity, Contract, Solution
from tprm import dora_export


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------


class DoraExportTestMixin:
    """Helpers shared by all report-level tests."""

    def _generate(self, func, *args, **kwargs):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            func(z, *args, **kwargs)
        return buf

    def _read_csv(self, buf, filename):
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as z:
            with z.open(filename) as f:
                return list(csv.reader(io.StringIO(f.read().decode("utf-8"))))

    def _read_json(self, buf, filename):
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as z:
            with z.open(filename) as f:
                return json.loads(f.read().decode("utf-8"))

    def _assert_headers(self, rows, expected):
        self.assertEqual(rows[0], expected)

    def _assert_col_count(self, rows, n):
        for i, row in enumerate(rows):
            self.assertEqual(len(row), n, f"Row {i} has {len(row)} cols, expected {n}")

    def _data_rows(self, rows):
        return rows[1:]


class DoraDataFactory:
    """Creates a rich object graph for report tests (called from setUp)."""

    def setUp(self):
        super().setUp()

        # --- Entities (9) ---
        self.main_entity = Entity.objects.create(
            name="Main Financial Entity",
            legal_identifiers={"LEI": "MAIN1234567890123456"},
            country="BE",
            currency="EUR",
            dora_entity_type="eba_CT:x12",
            dora_competent_authority="FSMA",
            dora_entity_hierarchy="eba_RP:x53",
        )

        self.subsidiary = Entity.objects.create(
            name="Subsidiary Entity",
            legal_identifiers={"LEI": "SUB00000000000000000"},
            country="FR",
            currency="EUR",
            parent_entity=self.main_entity,
            dora_provider_person_type="eba_CT:x212",
            dora_assets_value=50000,
        )

        self.branch_be = Entity.objects.create(
            name="Branch Belgium",
            legal_identifiers={"VAT": "BE0999999999"},
            country="BE",
            parent_entity=self.main_entity,
            # No dora_provider_person_type → branch
        )

        self.branch_nl = Entity.objects.create(
            name="Branch Netherlands",
            legal_identifiers={"EUID": "NL0888888888"},
            country="NL",
            parent_entity=self.main_entity,
            # person_type is None → branch
        )

        self.provider_external = Entity.objects.create(
            name="External Cloud Provider",
            legal_identifiers={"LEI": "PROV1234567890123456"},
            country="US",
            dora_provider_person_type="eba_CT:x212",
        )

        self.provider_external_2 = Entity.objects.create(
            name="German IT Provider",
            legal_identifiers={"VAT": "DE123456789"},
            country="DE",
            dora_provider_person_type="eba_CT:x212",
        )

        self.provider_intragroup = Entity.objects.create(
            name="Intragroup IT Services",
            legal_identifiers={"LEI": "INTRA000000000000000"},
            parent_entity=self.main_entity,
        )

        self.provider_with_parent = Entity.objects.create(
            name="UK Provider Subsidiary",
            legal_identifiers={"LEI": "UKPR1234567890123456"},
            country="GB",
            parent_entity=self.provider_external,
            dora_provider_person_type="eba_CT:x212",
        )

        self.entity_minimal = Entity.objects.create(
            name="Minimal Entity",
        )

        # --- Assets (4) ---
        self.biz_fn_critical = Asset.objects.create(
            name="Critical Payment Service",
            is_business_function=True,
            disaster_recovery_objectives={
                "objectives": {"rto": {"value": 2}, "rpo": {"value": 1}}
            },
            dora_criticality_assessment="eba_BT:x28",
            dora_criticality_justification="Supports core payments",
            dora_licenced_activity="eba_TA:x185",
            dora_discontinuing_impact="eba_ZZ:x793",
        )

        self.biz_fn_empty_objectives = Asset.objects.create(
            name="Function Empty Objectives",
            is_business_function=True,
            disaster_recovery_objectives={},
        )

        self.biz_fn_partial_objectives = Asset.objects.create(
            name="Function Partial Objectives",
            is_business_function=True,
            disaster_recovery_objectives={"objectives": {"rto": {"value": 4}}},
        )

        self.non_business_asset = Asset.objects.create(
            name="Laptop Fleet",
            is_business_function=False,
        )

        # --- Solutions (4) ---
        self.solution_cloud = Solution.objects.create(
            name="Cloud Hosting",
            provider_entity=self.provider_external,
            dora_ict_service_type="eba_TA:S09",
            storage_of_data=True,
            data_location_storage="US",
            data_location_processing="IE",
            dora_data_sensitiveness="eba_ZZ:x793",
            dora_reliance_level="eba_ZZ:x796",
            dora_substitutability="eba_ZZ:x960",
            dora_non_substitutability_reason="eba_ZZ:x963",
            dora_has_exit_plan="eba_BT:x28",
            dora_reintegration_possibility="eba_ZZ:x966",
            dora_discontinuing_impact="eba_ZZ:x793",
            dora_alternative_providers_identified="eba_BT:x28",
            dora_alternative_providers="Azure, GCP",
        )
        self.solution_cloud.assets.add(self.biz_fn_critical)

        self.solution_no_storage = Solution.objects.create(
            name="Managed Network",
            provider_entity=self.provider_external_2,
            dora_ict_service_type="eba_TA:S10",
            storage_of_data=False,
            data_location_storage="",
            data_location_processing="",
        )
        self.solution_no_storage.assets.add(self.biz_fn_critical)

        self.solution_no_assets = Solution.objects.create(
            name="Consulting Services",
            provider_entity=self.provider_external,
            dora_ict_service_type="eba_TA:S01",
        )

        self.solution_minimal = Solution.objects.create(
            name="Internal Tools",
            provider_entity=self.provider_intragroup,
        )
        self.solution_minimal.assets.add(self.biz_fn_empty_objectives)

        # --- Contracts (7) ---
        self.contract_main = Contract.objects.create(
            name="Main Cloud Contract",
            ref_id="CA-001",
            provider_entity=self.provider_external,
            beneficiary_entity=self.main_entity,
            annual_expense=100000,
            currency="EUR",
            is_intragroup=False,
            start_date=date(2024, 1, 1),
            end_date=date(2026, 12, 31),
            notice_period_entity=90,
            notice_period_provider=60,
            governing_law_country="BE",
            status=Contract.Status.ACTIVE,
        )
        self.contract_main.solutions.add(self.solution_cloud)

        self.contract_second = Contract.objects.create(
            name="Network Contract",
            ref_id="CA-002",
            provider_entity=self.provider_external_2,
            beneficiary_entity=self.main_entity,
            annual_expense=50000,
            currency="EUR",
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        self.contract_second.solutions.add(self.solution_no_storage)

        self.contract_no_expense = Contract.objects.create(
            name="Free Tier Contract",
            provider_entity=self.provider_external,
            beneficiary_entity=self.main_entity,
            annual_expense=None,
            currency="",
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        self.contract_no_expense.solutions.add(self.solution_cloud)

        self.overarching = Contract.objects.create(
            name="Group Framework Agreement",
            ref_id="CA-OVR",
            provider_entity=self.provider_intragroup,
            beneficiary_entity=self.main_entity,
            is_intragroup=True,
            status=Contract.Status.ACTIVE,
        )

        self.sub_contract = Contract.objects.create(
            name="Local IT Support",
            ref_id="CA-SUB",
            provider_entity=self.provider_intragroup,
            beneficiary_entity=self.subsidiary,
            is_intragroup=True,
            overarching_contract=self.overarching,
            status=Contract.Status.ACTIVE,
        )
        self.sub_contract.solutions.add(self.solution_minimal)

        self.contract_no_provider = Contract.objects.create(
            name="Legacy Contract",
            provider_entity=None,
            beneficiary_entity=self.main_entity,
            status=Contract.Status.ACTIVE,
        )

        self.contract_no_solutions = Contract.objects.create(
            name="Pending Contract",
            provider_entity=self.provider_external,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )


# ===========================================================================
# Helper function tests
# ===========================================================================


class TestGetEntityIdentifier(TestCase):
    def test_empty_entity(self):
        entity = Entity()
        self.assertEqual(dora_export.get_entity_identifier(entity), ("", ""))

    def test_none_entity(self):
        self.assertEqual(dora_export.get_entity_identifier(None), ("", ""))

    def test_null_legal_identifiers(self):
        entity = Entity(legal_identifiers=None)
        self.assertEqual(dora_export.get_entity_identifier(entity), ("", ""))

    def test_empty_legal_identifiers(self):
        entity = Entity(legal_identifiers={})
        self.assertEqual(dora_export.get_entity_identifier(entity), ("", ""))

    def test_lei_maps_to_qx2000(self):
        entity = Entity(legal_identifiers={"LEI": "ABCDEFGHIJ0123456789"})
        code, code_type = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "ABCDEFGHIJ0123456789")
        self.assertEqual(code_type, "eba_qCO:qx2000")

    def test_euid_maps_to_qx2002(self):
        entity = Entity(legal_identifiers={"EUID": "NL0888888888"})
        code, code_type = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "NL0888888888")
        self.assertEqual(code_type, "eba_qCO:qx2002")

    def test_vat_maps_to_qx2004(self):
        entity = Entity(legal_identifiers={"VAT": "BE0999999999"})
        code, code_type = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "BE0999999999")
        self.assertEqual(code_type, "eba_qCO:qx2004")

    def test_duns_maps_to_qx2003(self):
        entity = Entity(legal_identifiers={"DUNS": "123456789"})
        code, code_type = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "123456789")
        self.assertEqual(code_type, "eba_qCO:qx2003")

    def test_unknown_key_falls_back_to_qx2003(self):
        entity = Entity(legal_identifiers={"CUSTOM_ID": "XYZ"})
        code, code_type = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "XYZ")
        self.assertEqual(code_type, "eba_qCO:qx2003")

    def test_priority_lei_over_vat(self):
        entity = Entity(legal_identifiers={"VAT": "V1", "LEI": "L1"})
        code, _ = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "L1")

    def test_priority_euid_over_vat(self):
        entity = Entity(legal_identifiers={"VAT": "V1", "EUID": "E1"})
        code, _ = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "E1")

    def test_custom_priority_order(self):
        entity = Entity(legal_identifiers={"LEI": "L1", "VAT": "V1"})
        code, code_type = dora_export.get_entity_identifier(entity, priority=["VAT"])
        self.assertEqual(code, "V1")
        self.assertEqual(code_type, "eba_qCO:qx2004")

    def test_empty_string_values_skipped(self):
        entity = Entity(legal_identifiers={"LEI": "", "VAT": "V1"})
        code, code_type = dora_export.get_entity_identifier(entity)
        self.assertEqual(code, "V1")
        self.assertEqual(code_type, "eba_qCO:qx2004")


class TestFormatDate(TestCase):
    def test_normal_date(self):
        self.assertEqual(dora_export.format_date(date(2023, 5, 17)), "2023-05-17")

    def test_none_returns_empty(self):
        self.assertEqual(dora_export.format_date(None), "")

    def test_jan_first_zero_padding(self):
        self.assertEqual(dora_export.format_date(date(2024, 1, 1)), "2024-01-01")

    def test_dec_31_zero_padding(self):
        self.assertEqual(dora_export.format_date(date(2024, 12, 31)), "2024-12-31")


class TestComputeRefPeriod(TestCase):
    @patch("tprm.dora_export.date")
    def test_year_2025(self, mock_date):
        mock_date.today.return_value = date(2025, 6, 15)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        self.assertEqual(dora_export._compute_ref_period(), "2025-03-31")

    @patch("tprm.dora_export.date")
    def test_year_2026(self, mock_date):
        mock_date.today.return_value = date(2026, 3, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        self.assertEqual(dora_export._compute_ref_period(), "2025-12-31")

    @patch("tprm.dora_export.date")
    def test_year_2030(self, mock_date):
        mock_date.today.return_value = date(2030, 7, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        self.assertEqual(dora_export._compute_ref_period(), "2029-12-31")

    @patch("tprm.dora_export.date")
    def test_year_2024_returns_2025_period(self, mock_date):
        mock_date.today.return_value = date(2024, 12, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        self.assertEqual(dora_export._compute_ref_period(), "2025-03-31")


class TestGetDoraExportMetadata(TestCase):
    def setUp(self):
        self.entity_with_auth = Entity.objects.create(
            name="Entity With Auth",
            legal_identifiers={"LEI": "123456789ABCDEFGHI00"},
            dora_competent_authority="FSMA",
        )
        self.entity_without_auth = Entity.objects.create(
            name="Entity Without Auth",
            legal_identifiers={"LEI": "00IHGFEDCBA987654321"},
        )
        self.entity_no_lei = Entity.objects.create(
            name="Entity No LEI",
            legal_identifiers={"VAT": "BE0123456789"},
        )
        self.entity_empty_lei = Entity.objects.create(
            name="Entity Empty LEI",
            legal_identifiers={"LEI": ""},
        )

    def test_with_authority(self):
        meta = dora_export.get_dora_export_metadata(self.entity_with_auth)
        self.assertEqual(
            meta["folder_prefix"], "LEI_123456789ABCDEFGHI00.CON_FSMA_DOR_DORA_ROI"
        )
        self.assertEqual(
            meta["filename"], "LEI_123456789ABCDEFGHI00.CON_FSMA_DOR_DORA_ROI.zip"
        )
        self.assertEqual(meta["competent_authority"], "FSMA")

    def test_without_authority_defaults_unknown(self):
        meta = dora_export.get_dora_export_metadata(self.entity_without_auth)
        self.assertEqual(meta["competent_authority"], "UNKNOWN")
        self.assertIn("UNKNOWN", meta["folder_prefix"])

    def test_no_lei_raises_value_error(self):
        with self.assertRaises(ValueError):
            dora_export.get_dora_export_metadata(self.entity_no_lei)

    def test_empty_lei_raises_value_error(self):
        with self.assertRaises(ValueError):
            dora_export.get_dora_export_metadata(self.entity_empty_lei)

    def test_entity_id_format(self):
        meta = dora_export.get_dora_export_metadata(self.entity_with_auth)
        self.assertEqual(meta["entity_id"], "rs:123456789ABCDEFGHI00.CON")


# ===========================================================================
# Report generator tests
# ===========================================================================


class TestGenerateB0101(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_01.01.csv"
    HEADERS = ["c0010", "c0020", "c0030", "c0040", "c0050", "c0060"]

    def test_correct_headers(self):
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 6)

    def test_exactly_one_data_row(self):
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(self._data_rows(rows)), 1)

    def test_lei_column(self):
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][0], "MAIN1234567890123456")

    def test_name_column(self):
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][1], "Main Financial Entity")

    def test_country_column(self):
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][2], "eba_GA:BE")

    def test_entity_type_column(self):
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][3], "eba_CT:x12")

    def test_missing_country_returns_empty(self):
        self.main_entity.country = ""
        self.main_entity.save()
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][2], "")

    def test_missing_entity_type_returns_empty(self):
        self.main_entity.dora_entity_type = ""
        self.main_entity.save()
        buf = self._generate(dora_export.generate_b_01_01_main_entity, self.main_entity)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][3], "")

    def test_folder_prefix_path_routing(self):
        buf = self._generate(
            dora_export.generate_b_01_01_main_entity,
            self.main_entity,
            folder_prefix="MY_PREFIX",
        )
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as z:
            self.assertIn("MY_PREFIX/reports/b_01.01.csv", z.namelist())


class TestGenerateB0102(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_01.02.csv"
    HEADERS = [
        "c0010",
        "c0020",
        "c0030",
        "c0040",
        "c0050",
        "c0060",
        "c0070",
        "c0080",
        "c0090",
        "c0100",
        "c0110",
    ]

    def _entities(self):
        return [self.main_entity, self.subsidiary]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, self._entities()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, self._entities()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 11)

    def test_correct_row_count(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, self._entities()
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(self._data_rows(rows)), 2)

    def test_parent_lei_self_reference_when_no_parent(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, self._entities()
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "MAIN1234567890123456")
        # No parent → self-reference
        self.assertEqual(main_row[5], "MAIN1234567890123456")

    def test_subsidiary_parent_lei(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, self._entities()
        )
        rows = self._read_csv(buf, self.CSV)
        sub_row = next(r for r in rows[1:] if r[0] == "SUB00000000000000000")
        self.assertEqual(sub_row[5], "MAIN1234567890123456")

    def test_currency_prefix(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, self._entities()
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "MAIN1234567890123456")
        self.assertEqual(main_row[9], "eba_CU:EUR")

    def test_missing_currency(self):
        entity_no_cur = Entity.objects.create(
            name="No Currency",
            legal_identifiers={"LEI": "NOCUR000000000000000"},
        )
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, [entity_no_cur]
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][9], "")

    def test_assets_value_present(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, [self.subsidiary]
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][10], "50000")

    def test_assets_value_null(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, [self.main_entity]
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][10], "")

    def test_date_defaults(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, [self.main_entity]
        )
        rows = self._read_csv(buf, self.CSV)
        # deletion_date col 8 should be 9999-12-31
        self.assertEqual(rows[1][8], "9999-12-31")

    def test_empty_entity_list(self):
        buf = self._generate(
            dora_export.generate_b_01_02_entities, self.main_entity, []
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)  # header only


class TestGenerateB0103(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_01.03.csv"
    HEADERS = ["c0010", "c0020", "c0030", "c0040"]

    def test_correct_headers(self):
        buf = self._generate(dora_export.generate_b_01_03_branches, [self.branch_be])
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(dora_export.generate_b_01_03_branches, [self.branch_be])
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 4)

    def test_branch_code_from_vat(self):
        buf = self._generate(dora_export.generate_b_01_03_branches, [self.branch_be])
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][0], "BE0999999999")

    def test_branch_code_from_euid(self):
        buf = self._generate(dora_export.generate_b_01_03_branches, [self.branch_nl])
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][0], "NL0888888888")

    def test_head_office_lei(self):
        buf = self._generate(dora_export.generate_b_01_03_branches, [self.branch_be])
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][1], "MAIN1234567890123456")

    def test_missing_parent_returns_empty(self):
        orphan_branch = Entity.objects.create(
            name="Orphan Branch",
            legal_identifiers={"VAT": "XX111111111"},
        )
        buf = self._generate(dora_export.generate_b_01_03_branches, [orphan_branch])
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][1], "")

    def test_country_prefix(self):
        buf = self._generate(dora_export.generate_b_01_03_branches, [self.branch_be])
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][3], "eba_GA:BE")

    def test_empty_list(self):
        buf = self._generate(dora_export.generate_b_01_03_branches, [])
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)

    def test_multiple_branches(self):
        buf = self._generate(
            dora_export.generate_b_01_03_branches,
            [self.branch_be, self.branch_nl],
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(self._data_rows(rows)), 2)


class TestGenerateB0201(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_02.01.csv"
    HEADERS = ["c0010", "c0020", "c0030", "c0040", "c0050"]

    def _all_contracts(self):
        return Contract.objects.all()

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 5)

    def test_contract_ref_uses_ref_id(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        self.assertIn("CA-001", refs)

    def test_contract_ref_falls_back_to_id(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        # contract_no_expense has no ref_id → uses str(id)
        self.assertIn(str(self.contract_no_expense.id), refs)

    def test_overarching_reference_present(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        sub_row = next(r for r in rows[1:] if r[0] == "CA-SUB")
        self.assertEqual(sub_row[2], "CA-OVR")

    def test_overarching_reference_missing(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[2], "")

    def test_currency_prefix(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[3], "eba_CU:EUR")

    def test_missing_currency(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        no_expense_row = next(
            r for r in rows[1:] if r[0] == str(self.contract_no_expense.id)
        )
        self.assertEqual(no_expense_row[3], "")

    def test_annual_expense_present(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(float(main_row[4]), 100000.0)

    def test_annual_expense_null(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, self._all_contracts()
        )
        rows = self._read_csv(buf, self.CSV)
        no_expense_row = next(
            r for r in rows[1:] if r[0] == str(self.contract_no_expense.id)
        )
        self.assertEqual(no_expense_row[4], "")

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_02_01_contracts, Contract.objects.none()
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)


class TestGenerateB0202(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_02.02.csv"
    HEADERS = [
        "c0010",
        "c0020",
        "c0030",
        "c0040",
        "c0050",
        "c0060",
        "c0070",
        "c0080",
        "c0090",
        "c0100",
        "c0110",
        "c0120",
        "c0130",
        "c0140",
        "c0150",
        "c0160",
        "c0170",
        "c0180",
    ]

    def _contracts(self):
        return Contract.objects.all()

    def _biz_fn_ids(self):
        return set(
            Asset.objects.filter(is_business_function=True).values_list("id", flat=True)
        )

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 18)

    def test_contract_ref(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        self.assertIn("CA-001", refs)

    def test_beneficiary_lei(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[1], "MAIN1234567890123456")

    def test_provider_code_and_type_lei(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[2], "PROV1234567890123456")
        self.assertEqual(main_row[3], "eba_qCO:qx2000")

    def test_provider_with_non_lei_identifier(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        second_row = next(r for r in rows[1:] if r[0] == "CA-002")
        self.assertEqual(second_row[2], "DE123456789")
        self.assertEqual(second_row[3], "eba_qCO:qx2004")

    def test_function_id(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[4], str(self.biz_fn_critical.id))

    def test_ict_service_type(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[5], "eba_TA:S09")

    def test_start_date(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[6], "2024-01-01")

    def test_end_date(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[7], "2026-12-31")

    def test_end_date_missing_defaults_to_9999(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        second_row = next(r for r in rows[1:] if r[0] == "CA-002")
        self.assertEqual(second_row[7], "9999-12-31")

    def test_notice_periods_present(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[9], "90")
        self.assertEqual(main_row[10], "60")

    def test_notice_periods_null(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        second_row = next(r for r in rows[1:] if r[0] == "CA-002")
        self.assertEqual(second_row[9], "")
        self.assertEqual(second_row[10], "")

    def test_governing_law_country(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[11], "eba_GA:BE")

    def test_provider_country_present(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[12], "eba_GA:US")

    def test_provider_country_missing_defaults_qx2007(self):
        self.provider_external.country = ""
        self.provider_external.save()
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[12], "eba_GA:qx2007")

    def test_storage_of_data_true(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[13], "eba_BT:x28")

    def test_storage_of_data_false(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        second_row = next(r for r in rows[1:] if r[0] == "CA-002")
        self.assertEqual(second_row[13], "eba_BT:x29")

    def test_data_location_storage_present(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[14], "eba_GA:US")

    def test_data_location_storage_missing_defaults_qx2007(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        second_row = next(r for r in rows[1:] if r[0] == "CA-002")
        self.assertEqual(second_row[14], "eba_GA:qx2007")

    def test_data_location_processing_present(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[15], "eba_GA:IE")

    def test_data_location_processing_missing_defaults_qx2007(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        second_row = next(r for r in rows[1:] if r[0] == "CA-002")
        self.assertEqual(second_row[15], "eba_GA:qx2007")

    def test_data_sensitiveness(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[16], "eba_ZZ:x793")

    def test_reliance_level(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[17], "eba_ZZ:x796")

    def test_multiple_solutions_per_contract_multiple_rows(self):
        # contract_no_expense also has solution_cloud → should produce rows
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=self._biz_fn_ids(),
        )
        rows = self._read_csv(buf, self.CSV)
        # contract_main and contract_no_expense both have solution_cloud → biz_fn_critical
        # contract_second has solution_no_storage → biz_fn_critical
        # sub_contract has solution_minimal → biz_fn_empty_objectives
        self.assertGreater(len(self._data_rows(rows)), 2)

    def test_empty_business_function_asset_ids_uses_fallback(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
            business_function_asset_ids=set(),
        )
        rows = self._read_csv(buf, self.CSV)
        # Empty set is falsy → falls through to is_business_function=True filter
        self.assertGreater(len(self._data_rows(rows)), 0)

    def test_fallback_when_param_is_none(self):
        buf = self._generate(
            dora_export.generate_b_02_02_ict_services,
            self._contracts(),
        )
        rows = self._read_csv(buf, self.CSV)
        # Fallback uses is_business_function filter
        self.assertGreater(len(self._data_rows(rows)), 0)


class TestGenerateB0203(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_02.03.csv"
    HEADERS = ["c0010", "c0020", "c0030"]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_02_03_intragroup_contracts, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_02_03_intragroup_contracts, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 3)

    def test_only_intragroup_with_overarching(self):
        buf = self._generate(
            dora_export.generate_b_02_03_intragroup_contracts, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        # Only sub_contract has is_intragroup=True AND overarching_contract
        self.assertEqual(len(self._data_rows(rows)), 1)
        self.assertEqual(rows[1][0], "CA-SUB")
        self.assertEqual(rows[1][1], "CA-OVR")

    def test_intragroup_without_overarching_excluded(self):
        buf = self._generate(
            dora_export.generate_b_02_03_intragroup_contracts, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        # overarching itself is intragroup but has no overarching_contract
        self.assertNotIn("CA-OVR", refs)

    def test_link_always_true(self):
        buf = self._generate(
            dora_export.generate_b_02_03_intragroup_contracts, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[2], "true")

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_02_03_intragroup_contracts, Contract.objects.none()
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)


class TestGenerateB0301(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_03.01.csv"
    HEADERS = ["c0010", "c0020", "c0030"]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_03_01_signing_entities,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_all_contracts_listed(self):
        contracts = Contract.objects.all()
        buf = self._generate(
            dora_export.generate_b_03_01_signing_entities,
            self.main_entity,
            contracts,
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(self._data_rows(rows)), contracts.count())

    def test_signing_entity_always_main(self):
        buf = self._generate(
            dora_export.generate_b_03_01_signing_entities,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[1], "MAIN1234567890123456")

    def test_link_always_true(self):
        buf = self._generate(
            dora_export.generate_b_03_01_signing_entities,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[2], "true")

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_03_01_signing_entities,
            self.main_entity,
            Contract.objects.none(),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)


class TestGenerateB0302(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_03.02.csv"
    HEADERS = ["c0010", "c0020", "c0030"]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_03_02_ict_providers, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_only_third_party_contracts(self):
        buf = self._generate(
            dora_export.generate_b_03_02_ict_providers, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        # Intragroup contracts should not appear
        self.assertNotIn("CA-OVR", refs)
        self.assertNotIn("CA-SUB", refs)

    def test_provider_code_and_type(self):
        buf = self._generate(
            dora_export.generate_b_03_02_ict_providers, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[1], "PROV1234567890123456")
        self.assertEqual(main_row[2], "eba_qCO:qx2000")

    def test_provider_vat_type(self):
        buf = self._generate(
            dora_export.generate_b_03_02_ict_providers, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        second_row = next(r for r in rows[1:] if r[0] == "CA-002")
        self.assertEqual(second_row[1], "DE123456789")
        self.assertEqual(second_row[2], "eba_qCO:qx2004")

    def test_contract_without_provider_excluded(self):
        buf = self._generate(
            dora_export.generate_b_03_02_ict_providers, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        self.assertNotIn(str(self.contract_no_provider.id), refs)

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_03_02_ict_providers, Contract.objects.none()
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)


class TestGenerateB0303(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_03.03.csv"
    HEADERS = ["c0010", "c0020", "c0031"]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_03_03_intragroup_providers,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_only_intragroup(self):
        buf = self._generate(
            dora_export.generate_b_03_03_intragroup_providers,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        # overarching + sub_contract are intragroup
        self.assertEqual(len(self._data_rows(rows)), 2)

    def test_provider_lei(self):
        buf = self._generate(
            dora_export.generate_b_03_03_intragroup_providers,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[1], "INTRA000000000000000")

    def test_link_always_true(self):
        buf = self._generate(
            dora_export.generate_b_03_03_intragroup_providers,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[2], "true")

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_03_03_intragroup_providers,
            self.main_entity,
            Contract.objects.none(),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)


class TestGenerateB0401(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_04.01.csv"
    HEADERS = ["c0010", "c0020", "c0030", "c0040"]

    def _branches(self):
        return [self.branch_be, self.branch_nl]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_04_01_service_users,
            self._branches(),
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_beneficiary_row_nature(self):
        buf = self._generate(
            dora_export.generate_b_04_01_service_users,
            self._branches(),
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        main_rows = [r for r in rows[1:] if r[0] == "CA-001" and r[2] == "eba_ZZ:x839"]
        self.assertEqual(len(main_rows), 1)
        self.assertEqual(main_rows[0][3], "")  # branch_code empty

    def test_branch_row_nature(self):
        buf = self._generate(
            dora_export.generate_b_04_01_service_users,
            self._branches(),
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        branch_rows = [
            r for r in rows[1:] if r[0] == "CA-001" and r[2] == "eba_ZZ:x838"
        ]
        # main_entity has 2 branches → 2 branch rows for CA-001
        self.assertEqual(len(branch_rows), 2)

    def test_branch_code_present(self):
        buf = self._generate(
            dora_export.generate_b_04_01_service_users,
            self._branches(),
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        branch_rows = [
            r for r in rows[1:] if r[0] == "CA-001" and r[2] == "eba_ZZ:x838"
        ]
        branch_codes = {r[3] for r in branch_rows}
        self.assertIn("BE0999999999", branch_codes)
        self.assertIn("NL0888888888", branch_codes)

    def test_deduplication(self):
        buf = self._generate(
            dora_export.generate_b_04_01_service_users,
            self._branches(),
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        # Check no duplicate (contract_ref, beneficiary_lei, branch_code) combos
        combos = [(r[0], r[1], r[3]) for r in self._data_rows(rows)]
        self.assertEqual(len(combos), len(set(combos)))

    def test_empty_branches_still_has_beneficiary_rows(self):
        buf = self._generate(
            dora_export.generate_b_04_01_service_users,
            [],
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        # All contracts still get beneficiary rows
        self.assertGreater(len(self._data_rows(rows)), 0)
        for row in self._data_rows(rows):
            self.assertEqual(row[2], "eba_ZZ:x839")

    def test_subsidiary_contract_no_branches(self):
        # sub_contract beneficiary is subsidiary, not main → no branches for it
        buf = self._generate(
            dora_export.generate_b_04_01_service_users,
            self._branches(),
            Contract.objects.filter(id=self.sub_contract.id),
        )
        rows = self._read_csv(buf, self.CSV)
        # Only 1 beneficiary row, no branch rows (branches belong to main, not subsidiary)
        self.assertEqual(len(self._data_rows(rows)), 1)
        self.assertEqual(rows[1][2], "eba_ZZ:x839")


class TestGenerateB0501(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_05.01.csv"
    HEADERS = [
        "c0010",
        "c0020",
        "c0030",
        "c0040",
        "c0050",
        "c0060",
        "c0070",
        "c0080",
        "c0090",
        "c0100",
        "c0110",
        "c0120",
    ]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 12)

    def test_only_third_party_providers(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        provider_codes = [r[0] for r in self._data_rows(rows)]
        self.assertNotIn("INTRA000000000000000", provider_codes)

    def test_provider_deduplication(self):
        # provider_external has 2 contracts (contract_main, contract_no_expense) → 1 row
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        lei_rows = [r for r in self._data_rows(rows) if r[0] == "PROV1234567890123456"]
        self.assertEqual(len(lei_rows), 1)

    def test_expense_aggregation(self):
        # provider_external: contract_main (100000) + contract_no_expense (None) + contract_no_solutions (None)
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        prov_row = next(r for r in rows[1:] if r[0] == "PROV1234567890123456")
        self.assertEqual(float(prov_row[9]), 100000.0)

    def test_expense_aggregation_multiple_providers(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        de_row = next(r for r in rows[1:] if r[0] == "DE123456789")
        self.assertEqual(float(de_row[9]), 50000.0)

    def test_null_expense_excluded_from_aggregation(self):
        # contract_no_expense has annual_expense=None → should not add anything
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        prov_row = next(r for r in rows[1:] if r[0] == "PROV1234567890123456")
        # Total should be 100000 (from contract_main only), not crash
        self.assertEqual(float(prov_row[9]), 100000.0)

    def test_currency_from_contract(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        prov_row = next(r for r in rows[1:] if r[0] == "PROV1234567890123456")
        self.assertEqual(prov_row[8], "eba_CU:EUR")

    def test_parent_entity_codes_populated(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.filter(provider_entity=self.provider_with_parent),
        )
        # Need a contract with provider_with_parent
        c = Contract.objects.create(
            name="UK Contract",
            provider_entity=self.provider_with_parent,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        uk_row = next((r for r in rows[1:] if r[0] == "UKPR1234567890123456"), None)
        if uk_row:
            self.assertEqual(uk_row[10], "PROV1234567890123456")
            self.assertEqual(uk_row[11], "eba_qCO:qx2000")
        c.delete()

    def test_parent_entity_empty_when_no_parent(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        prov_row = next(r for r in rows[1:] if r[0] == "PROV1234567890123456")
        self.assertEqual(prov_row[10], "")
        self.assertEqual(prov_row[11], "")

    def test_ultimate_parent_multi_level_hierarchy(self):
        """c0110/c0120 should resolve to the ultimate parent, not the immediate parent."""
        grandparent = Entity.objects.create(
            name="Grand Parent Corp",
            legal_identifiers={"LEI": "GRAND123456789012345"},
            country="US",
        )
        intermediate = Entity.objects.create(
            name="Intermediate Holdings",
            legal_identifiers={"LEI": "INTER123456789012345"},
            country="GB",
            parent_entity=grandparent,
        )
        subsidiary = Entity.objects.create(
            name="Subsidiary Provider",
            legal_identifiers={"LEI": "SUBSI123456789012345"},
            country="DE",
            parent_entity=intermediate,
            dora_provider_person_type="eba_CT:x212",
        )
        contract = Contract.objects.create(
            name="Subsidiary Contract",
            provider_entity=subsidiary,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.filter(pk=contract.pk),
        )
        rows = self._read_csv(buf, self.CSV)
        sub_row = next(r for r in rows[1:] if r[0] == "SUBSI123456789012345")
        # c0110 should be the grandparent's LEI, not intermediate's
        self.assertEqual(sub_row[10], "GRAND123456789012345")
        self.assertEqual(sub_row[11], "eba_qCO:qx2000")
        # Cleanup
        contract.delete()
        subsidiary.delete()
        intermediate.delete()
        grandparent.delete()

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_05_01_provider_details,
            self.main_entity,
            Contract.objects.none(),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)


class TestGenerateB0502(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_05.02.csv"
    HEADERS = ["c0010", "c0020", "c0030", "c0040", "c0050", "c0060", "c0070"]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 7)

    def test_only_third_party_with_solutions(self):
        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        self.assertNotIn("CA-OVR", refs)
        self.assertNotIn("CA-SUB", refs)

    def test_rank_1_for_direct_providers(self):
        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[4], "1")

    def test_recipient_empty_for_rank_1(self):
        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[5], "")
            self.assertEqual(row[6], "")

    def test_multiple_solutions_multiple_rows(self):
        # contract_main has 1 solution, contract_second has 1 → at least 2 rows
        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertGreaterEqual(len(self._data_rows(rows)), 2)

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains, Contract.objects.none()
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)

    def test_rank_from_provider_chain(self):
        """Provider with parent chain produces multiple rows with increasing rank."""
        grandparent = Entity.objects.create(
            name="Root Provider",
            legal_identifiers={"LEI": "ROOT1234567890123456"},
        )
        intermediate = Entity.objects.create(
            name="Intermediate Sub",
            legal_identifiers={"LEI": "INTM1234567890123456"},
            parent_entity=grandparent,
        )
        leaf = Entity.objects.create(
            name="Leaf Sub-sub",
            legal_identifiers={"LEI": "LEAF1234567890123456"},
            parent_entity=intermediate,
        )
        solution = Solution.objects.create(
            name="Subcontracted Service",
            provider_entity=leaf,
            dora_ict_service_type="eba_ZZ:x755",
        )
        contract = Contract.objects.create(
            name="Chain Contract",
            ref_id="CA-CHAIN",
            provider_entity=grandparent,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        contract.solutions.add(solution)

        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains,
            Contract.objects.filter(pk=contract.pk),
        )
        rows = self._read_csv(buf, self.CSV)
        chain_rows = [r for r in self._data_rows(rows) if r[0] == "CA-CHAIN"]

        # 3 ranks
        self.assertEqual(len(chain_rows), 3)

        # Rank 1: root provider, no recipient
        self.assertEqual(chain_rows[0][2], "ROOT1234567890123456")  # c0030
        self.assertEqual(chain_rows[0][4], "1")  # c0050
        self.assertEqual(chain_rows[0][5], "")  # c0060

        # Rank 2: intermediate, recipient = root
        self.assertEqual(chain_rows[1][2], "INTM1234567890123456")
        self.assertEqual(chain_rows[1][4], "2")
        self.assertEqual(chain_rows[1][5], "ROOT1234567890123456")

        # Rank 3: leaf, recipient = intermediate
        self.assertEqual(chain_rows[2][2], "LEAF1234567890123456")
        self.assertEqual(chain_rows[2][4], "3")
        self.assertEqual(chain_rows[2][5], "INTM1234567890123456")

        # Cleanup
        contract.solutions.clear()
        contract.delete()
        solution.delete()
        leaf.delete()
        intermediate.delete()
        grandparent.delete()

    def test_rank_1_no_parent(self):
        """Provider with no parent produces a single rank-1 row (regression guard)."""
        standalone = Entity.objects.create(
            name="Standalone Provider",
            legal_identifiers={"LEI": "SOLO1234567890123456"},
        )
        solution = Solution.objects.create(
            name="Solo Service",
            provider_entity=standalone,
            dora_ict_service_type="eba_ZZ:x755",
        )
        contract = Contract.objects.create(
            name="Solo Contract",
            ref_id="CA-SOLO",
            provider_entity=standalone,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        contract.solutions.add(solution)

        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains,
            Contract.objects.filter(pk=contract.pk),
        )
        rows = self._read_csv(buf, self.CSV)
        solo_rows = [r for r in self._data_rows(rows) if r[0] == "CA-SOLO"]

        self.assertEqual(len(solo_rows), 1)
        self.assertEqual(solo_rows[0][4], "1")
        self.assertEqual(solo_rows[0][5], "")
        self.assertEqual(solo_rows[0][6], "")

        # Cleanup
        contract.solutions.clear()
        contract.delete()
        solution.delete()
        standalone.delete()


class TestGenerateB0601(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_06.01.csv"
    HEADERS = [
        "c0010",
        "c0020",
        "c0030",
        "c0040",
        "c0050",
        "c0060",
        "c0070",
        "c0080",
        "c0090",
        "c0100",
    ]

    def _biz_fns(self):
        return Asset.objects.filter(is_business_function=True)

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            self._biz_fns(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            self._biz_fns(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 10)

    def test_function_id_uses_ref_id(self):
        self.biz_fn_critical.ref_id = "FN-001"
        self.biz_fn_critical.save()
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_critical.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][0], "FN-001")

    def test_function_id_falls_back_to_uuid(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_critical.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][0], str(self.biz_fn_critical.id))

    def test_licensed_activity(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_critical.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][1], "eba_TA:x185")

    def test_function_name(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_critical.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][2], "Critical Payment Service")

    def test_entity_lei_is_main(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            self._biz_fns(),
        )
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[3], "MAIN1234567890123456")

    def test_criticality_assessment(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_critical.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][4], "eba_BT:x28")

    def test_rto_rpo_full_objectives(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_critical.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][7], "2")
        self.assertEqual(rows[1][8], "1")

    def test_rto_rpo_empty_dict(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_empty_objectives.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][7], "")
        self.assertEqual(rows[1][8], "")

    def test_rto_rpo_partial_only_rto(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_partial_objectives.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][7], "4")
        self.assertEqual(rows[1][8], "")

    def test_discontinuing_impact(self):
        buf = self._generate(
            dora_export.generate_b_06_01_functions,
            self.main_entity,
            Asset.objects.filter(id=self.biz_fn_critical.id),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(rows[1][9], "eba_ZZ:x793")


class TestGenerateB0701(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_07.01.csv"
    HEADERS = [
        "c0010",
        "c0020",
        "c0030",
        "c0040",
        "c0050",
        "c0060",
        "c0070",
        "c0080",
        "c0090",
        "c0100",
        "c0110",
        "c0120",
    ]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_07_01_assessment, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_07_01_assessment, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 12)

    def test_only_third_party_with_solutions(self):
        buf = self._generate(
            dora_export.generate_b_07_01_assessment, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        self.assertNotIn("CA-OVR", refs)
        self.assertNotIn("CA-SUB", refs)

    def test_solution_dora_fields(self):
        buf = self._generate(
            dora_export.generate_b_07_01_assessment, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        # Find the row for contract_main with solution_cloud
        main_row = next(r for r in rows[1:] if r[0] == "CA-001")
        self.assertEqual(main_row[3], "eba_TA:S09")
        self.assertEqual(main_row[4], "eba_ZZ:x960")
        self.assertEqual(main_row[5], "eba_ZZ:x963")
        self.assertEqual(main_row[7], "eba_BT:x28")
        self.assertEqual(main_row[8], "eba_ZZ:x966")
        self.assertEqual(main_row[9], "eba_ZZ:x793")
        self.assertEqual(main_row[10], "eba_BT:x28")
        self.assertEqual(main_row[11], "Azure, GCP")

    def test_missing_optional_fields(self):
        buf = self._generate(
            dora_export.generate_b_07_01_assessment,
            Contract.objects.filter(id=self.contract_second.id),
        )
        rows = self._read_csv(buf, self.CSV)
        if len(rows) > 1:
            row = rows[1]
            self.assertEqual(row[4], "")  # substitutability
            self.assertEqual(row[5], "")  # non_sub reason

    def test_empty_queryset(self):
        buf = self._generate(
            dora_export.generate_b_07_01_assessment, Contract.objects.none()
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)

    def test_contract_no_solutions_excluded(self):
        buf = self._generate(
            dora_export.generate_b_07_01_assessment, Contract.objects.all()
        )
        rows = self._read_csv(buf, self.CSV)
        refs = [r[0] for r in self._data_rows(rows)]
        self.assertNotIn(str(self.contract_no_solutions.id), refs)


class TestGenerateB9901(DoraExportTestMixin, DoraDataFactory, TestCase):
    CSV = "reports/b_99.01.csv"
    EXPECTED_HEADERS = [
        "c0010",
        "c0020",
        "c0030",
        "c0040",
        "c0050",
        "c0060",
        "c0070",
        "c0080",
        "c0090",
        "c0100",
        "c0110",
        "c0120",
        "c0130",
        "c0140",
        "c0150",
        "c0160",
        "c0170",
        "c0180",
        "c0190",
    ]

    def test_correct_headers(self):
        buf = self._generate(
            dora_export.generate_b_99_01_aggregation,
            Contract.objects.all(),
            Asset.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, self.EXPECTED_HEADERS)

    def test_col_count(self):
        buf = self._generate(
            dora_export.generate_b_99_01_aggregation,
            Contract.objects.all(),
            Asset.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self._assert_col_count(rows, 19)

    def test_header_only_no_data_rows(self):
        buf = self._generate(
            dora_export.generate_b_99_01_aggregation,
            Contract.objects.all(),
            Asset.objects.all(),
        )
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(rows), 1)


class TestFilingIndicators(DoraExportTestMixin, TestCase):
    CSV = "reports/FilingIndicators.csv"

    def test_correct_headers(self):
        buf = self._generate(dora_export.generate_filing_indicators)
        rows = self._read_csv(buf, self.CSV)
        self._assert_headers(rows, ["templateID", "reported"])

    def test_exactly_15_templates(self):
        buf = self._generate(dora_export.generate_filing_indicators)
        rows = self._read_csv(buf, self.CSV)
        self.assertEqual(len(self._data_rows(rows)), 15)

    def test_all_reported_true(self):
        buf = self._generate(dora_export.generate_filing_indicators)
        rows = self._read_csv(buf, self.CSV)
        for row in self._data_rows(rows):
            self.assertEqual(row[1], "true")

    def test_complete_template_set(self):
        expected_ids = {
            "B_01.01",
            "B_01.02",
            "B_01.03",
            "B_02.01",
            "B_02.02",
            "B_02.03",
            "B_03.01",
            "B_03.02",
            "B_03.03",
            "B_04.01",
            "B_05.01",
            "B_05.02",
            "B_06.01",
            "B_07.01",
            "B_99.01",
        }
        buf = self._generate(dora_export.generate_filing_indicators)
        rows = self._read_csv(buf, self.CSV)
        actual_ids = {r[0] for r in self._data_rows(rows)}
        self.assertEqual(actual_ids, expected_ids)


class TestParameters(DoraExportTestMixin, TestCase):
    def setUp(self):
        self.entity = Entity.objects.create(
            name="Param Entity",
            legal_identifiers={"LEI": "PARAM000000000000000"},
            currency="EUR",
        )

    def _params_dict(self, buf):
        rows = self._read_csv(buf, "reports/parameters.csv")
        return dict(self._data_rows(rows))

    def test_entity_id_passed_through(self):
        buf = self._generate(
            dora_export.generate_parameters,
            self.entity,
            entity_id="rs:CUSTOM.CON",
        )
        params = self._params_dict(buf)
        self.assertEqual(params["entityID"], "rs:CUSTOM.CON")

    def test_entity_id_computed_from_lei(self):
        buf = self._generate(dora_export.generate_parameters, self.entity)
        params = self._params_dict(buf)
        self.assertEqual(params["entityID"], "rs:PARAM000000000000000.CON")

    def test_base_currency(self):
        buf = self._generate(dora_export.generate_parameters, self.entity)
        params = self._params_dict(buf)
        self.assertEqual(params["baseCurrency"], "iso4217:EUR")

    def test_base_currency_other(self):
        self.entity.currency = "USD"
        self.entity.save()
        buf = self._generate(dora_export.generate_parameters, self.entity)
        params = self._params_dict(buf)
        self.assertEqual(params["baseCurrency"], "iso4217:USD")

    def test_ref_period_present(self):
        buf = self._generate(dora_export.generate_parameters, self.entity)
        params = self._params_dict(buf)
        self.assertIn("refPeriod", params)
        self.assertTrue(len(params["refPeriod"]) > 0)

    def test_decimals(self):
        buf = self._generate(dora_export.generate_parameters, self.entity)
        params = self._params_dict(buf)
        self.assertEqual(params["decimalsInteger"], "0")
        self.assertEqual(params["decimalsMonetary"], "-3")

    def test_five_parameter_rows(self):
        buf = self._generate(dora_export.generate_parameters, self.entity)
        rows = self._read_csv(buf, "reports/parameters.csv")
        self.assertEqual(len(self._data_rows(rows)), 5)


class TestReportPackageJson(DoraExportTestMixin, TestCase):
    def test_document_type(self):
        buf = self._generate(dora_export.generate_report_package_json)
        data = self._read_json(buf, "META-INF/reportPackage.json")
        self.assertEqual(
            data["documentInfo"]["documentType"],
            "https://xbrl.org/report-package/2023",
        )

    def test_json_structure(self):
        buf = self._generate(dora_export.generate_report_package_json)
        data = self._read_json(buf, "META-INF/reportPackage.json")
        self.assertIn("documentInfo", data)

    def test_path(self):
        buf = self._generate(dora_export.generate_report_package_json)
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as z:
            self.assertIn("META-INF/reportPackage.json", z.namelist())


class TestReportJson(DoraExportTestMixin, TestCase):
    def test_document_type(self):
        buf = self._generate(dora_export.generate_report_json)
        data = self._read_json(buf, "reports/report.json")
        self.assertEqual(
            data["documentInfo"]["documentType"],
            "https://xbrl.org/2021/xbrl-csv",
        )

    def test_extends_taxonomy(self):
        buf = self._generate(dora_export.generate_report_json)
        data = self._read_json(buf, "reports/report.json")
        self.assertIn(
            "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/dora/4.0/mod/dora.json",
            data["documentInfo"]["extends"],
        )

    def test_path(self):
        buf = self._generate(dora_export.generate_report_json)
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as z:
            self.assertIn("reports/report.json", z.namelist())


# ===========================================================================
# Cross-table referential integrity
# ===========================================================================


class TestCrossTableReferentialIntegrity(
    DoraExportTestMixin, DoraDataFactory, TestCase
):
    """Verify FK consistency across all report tables."""

    def setUp(self):
        super().setUp()
        self.all_contracts = Contract.objects.all()
        self.biz_fn_ids = set(
            Asset.objects.filter(is_business_function=True).values_list("id", flat=True)
        )
        self.branches = [self.branch_be, self.branch_nl]
        self.biz_fns = Asset.objects.filter(is_business_function=True)

        # Generate all reports into one zip
        self.buf = io.BytesIO()
        with zipfile.ZipFile(self.buf, "w") as z:
            dora_export.generate_b_01_01_main_entity(z, self.main_entity)
            dora_export.generate_b_01_02_entities(
                z, self.main_entity, [self.main_entity, self.subsidiary]
            )
            dora_export.generate_b_01_03_branches(z, self.branches)
            dora_export.generate_b_02_01_contracts(z, self.all_contracts)
            dora_export.generate_b_02_02_ict_services(
                z, self.all_contracts, business_function_asset_ids=self.biz_fn_ids
            )
            dora_export.generate_b_02_03_intragroup_contracts(z, self.all_contracts)
            dora_export.generate_b_03_01_signing_entities(
                z, self.main_entity, self.all_contracts
            )
            dora_export.generate_b_03_02_ict_providers(z, self.all_contracts)
            dora_export.generate_b_03_03_intragroup_providers(
                z, self.main_entity, self.all_contracts
            )
            dora_export.generate_b_04_01_service_users(
                z, self.branches, self.all_contracts
            )
            dora_export.generate_b_05_01_provider_details(
                z, self.main_entity, self.all_contracts
            )
            dora_export.generate_b_05_02_supply_chains(z, self.all_contracts)
            dora_export.generate_b_06_01_functions(z, self.main_entity, self.biz_fns)
            dora_export.generate_b_07_01_assessment(z, self.all_contracts)
            dora_export.generate_b_99_01_aggregation(
                z, self.all_contracts, self.biz_fns
            )

    def _get_refs(self, csv_name, col=0):
        rows = self._read_csv(self.buf, csv_name)
        return {r[col] for r in self._data_rows(rows)}

    def test_b0202_refs_subset_of_b0201(self):
        b0201_refs = self._get_refs("reports/b_02.01.csv")
        b0202_refs = self._get_refs("reports/b_02.02.csv")
        self.assertTrue(b0202_refs.issubset(b0201_refs))

    def test_b0203_refs_subset_of_b0201(self):
        b0201_refs = self._get_refs("reports/b_02.01.csv")
        b0203_refs = self._get_refs("reports/b_02.03.csv")
        self.assertTrue(b0203_refs.issubset(b0201_refs))

    def test_b0301_refs_subset_of_b0201(self):
        b0201_refs = self._get_refs("reports/b_02.01.csv")
        b0301_refs = self._get_refs("reports/b_03.01.csv")
        self.assertTrue(b0301_refs.issubset(b0201_refs))

    def test_b0302_refs_subset_of_b0201(self):
        b0201_refs = self._get_refs("reports/b_02.01.csv")
        b0302_refs = self._get_refs("reports/b_03.02.csv")
        self.assertTrue(b0302_refs.issubset(b0201_refs))

    def test_b0401_refs_subset_of_b0201(self):
        b0201_refs = self._get_refs("reports/b_02.01.csv")
        b0401_refs = self._get_refs("reports/b_04.01.csv")
        self.assertTrue(b0401_refs.issubset(b0201_refs))

    def test_b0502_refs_subset_of_b0201(self):
        b0201_refs = self._get_refs("reports/b_02.01.csv")
        b0502_refs = self._get_refs("reports/b_05.02.csv")
        self.assertTrue(b0502_refs.issubset(b0201_refs))

    def test_b0701_refs_subset_of_b0201(self):
        b0201_refs = self._get_refs("reports/b_02.01.csv")
        b0701_refs = self._get_refs("reports/b_07.01.csv")
        self.assertTrue(b0701_refs.issubset(b0201_refs))

    def test_b0202_function_ids_subset_of_b0601(self):
        b0601_rows = self._read_csv(self.buf, "reports/b_06.01.csv")
        b0601_fn_ids = {r[0] for r in self._data_rows(b0601_rows)}
        b0202_rows = self._read_csv(self.buf, "reports/b_02.02.csv")
        b0202_fn_ids = {r[4] for r in self._data_rows(b0202_rows)}
        self.assertTrue(b0202_fn_ids.issubset(b0601_fn_ids))


# ===========================================================================
# EBA validation rules compliance
# ===========================================================================

LEI_REGEX = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


class TestEBAValidationRules(DoraExportTestMixin, DoraDataFactory, TestCase):
    """
    Verify generated CSV output conforms to EBA validation rules v4.2.1.
    Rules from: EBA_validation_rules_4.2.1_2026-02-18.xlsx (49 active DORA rules).
    """

    def setUp(self):
        super().setUp()
        self.all_contracts = Contract.objects.all()
        self.biz_fn_ids = set(
            Asset.objects.filter(is_business_function=True).values_list("id", flat=True)
        )
        self.branches = [self.branch_be, self.branch_nl]
        self.biz_fns = Asset.objects.filter(is_business_function=True)

        # Generate all reports into one zip
        self.buf = io.BytesIO()
        with zipfile.ZipFile(self.buf, "w") as z:
            dora_export.generate_b_01_01_main_entity(z, self.main_entity)
            dora_export.generate_b_01_02_entities(
                z, self.main_entity, [self.main_entity, self.subsidiary]
            )
            dora_export.generate_b_01_03_branches(z, self.branches)
            dora_export.generate_b_02_01_contracts(z, self.all_contracts)
            dora_export.generate_b_02_02_ict_services(
                z, self.all_contracts, business_function_asset_ids=self.biz_fn_ids
            )
            dora_export.generate_b_05_01_provider_details(
                z, self.main_entity, self.all_contracts
            )
            dora_export.generate_b_06_01_functions(z, self.main_entity, self.biz_fns)
            dora_export.generate_b_07_01_assessment(z, self.all_contracts)

        # Parse all CSVs into data rows (excluding header)
        self.b0101 = self._data_rows(self._read_csv(self.buf, "reports/b_01.01.csv"))
        self.b0102 = self._data_rows(self._read_csv(self.buf, "reports/b_01.02.csv"))
        self.b0103 = self._data_rows(self._read_csv(self.buf, "reports/b_01.03.csv"))
        self.b0201 = self._data_rows(self._read_csv(self.buf, "reports/b_02.01.csv"))
        self.b0202 = self._data_rows(self._read_csv(self.buf, "reports/b_02.02.csv"))
        self.b0501 = self._data_rows(self._read_csv(self.buf, "reports/b_05.01.csv"))
        self.b0601 = self._data_rows(self._read_csv(self.buf, "reports/b_06.01.csv"))
        self.b0701 = self._data_rows(self._read_csv(self.buf, "reports/b_07.01.csv"))

    # --- Category 1: LEI Format (4 tests) ---

    def test_v8890_b0101_lei_format(self):
        """v8890_m: B_01.01 c0010 LEI must match ^[A-Z0-9]{18}[0-9]{2}$."""
        for row in self.b0101:
            lei = row[0]  # c0010
            if lei:
                self.assertRegex(lei, LEI_REGEX)

    def test_v8891_b0102_lei_format(self):
        """v8891_m: B_01.02 c0010 LEI must match ^[A-Z0-9]{18}[0-9]{2}$."""
        for row in self.b0102:
            lei = row[0]  # c0010
            if lei:
                self.assertRegex(lei, LEI_REGEX)

    def test_v8826_b0102_parent_lei_format(self):
        """v8826_m: B_01.02 c0060 parent LEI must match ^[A-Z0-9]{18}[0-9]{2}$."""
        for row in self.b0102:
            lei = row[5]  # c0060
            if lei:
                self.assertRegex(lei, LEI_REGEX)

    def test_v8892_b0103_head_office_lei_format(self):
        """v8892_m: B_01.03 c0020 head office LEI must match ^[A-Z0-9]{18}[0-9]{2}$."""
        for row in self.b0103:
            lei = row[1]  # c0020
            if lei:
                self.assertRegex(lei, LEI_REGEX)

    # --- Category 2: Non-negative constraints (2 tests) ---

    def test_v22913_b0102_assets_non_negative(self):
        """v22913_s: B_01.02 c0110 assets value must be >= 0."""
        for row in self.b0102:
            val = row[10]  # c0110
            if val:
                self.assertGreaterEqual(float(val), 0)

    def test_v23716_b0201_expense_non_negative(self):
        """v23716_s: B_02.01 c0050 annual expense must be >= 0."""
        for row in self.b0201:
            val = row[4]  # c0050
            if val:
                self.assertGreaterEqual(float(val), 0)

    # --- Category 3: Conditional logic (6 tests) ---

    def test_v8803_b0102_assets_implies_currency(self):
        """v8803_m: If B_01.02 c0110 populated, c0100 must be populated."""
        for row in self.b0102:
            if row[10]:  # c0110 (assets)
                self.assertTrue(row[9], f"c0100 (currency) empty when c0110={row[10]}")

    @unittest.skip(
        "EBA rule not enforced: subsidiary has no entity_type, main entity has no assets"
    )
    def test_v8804_b0102_entity_type_implies_assets(self):
        """v8804_m: If B_01.02 c0040 not in {x318, x317}, c0110 must be populated."""
        exempt_types = {"eba_CT:x318", "eba_CT:x317"}
        for row in self.b0102:
            entity_type = row[3]  # c0040
            if entity_type and entity_type not in exempt_types:
                self.assertTrue(
                    row[10], f"c0110 (assets) empty for entity_type={entity_type}"
                )

    def test_v8805_b0201_subordinate_implies_overarching(self):
        """v8805_m: If B_02.01 c0020 is subordinate (x3), c0030 must be populated."""
        subordinate_types = {"eba_ZZ:x3"}
        for row in self.b0201:
            if row[1] in subordinate_types:  # c0020 (arrangement type)
                self.assertTrue(
                    row[2], f"c0030 empty for subordinate contract {row[0]}"
                )

    def test_v8825_b0701_not_substitutable_implies_reason(self):
        """v8825_m: If B_07.01 c0050 in {x959, x960}, c0060 must be populated."""
        non_sub_values = {"eba_ZZ:x959", "eba_ZZ:x960"}
        for row in self.b0701:
            if row[4] in non_sub_values:  # c0050 (substitutability)
                self.assertTrue(row[5], f"c0060 (reason) empty when c0050={row[4]}")

    def test_v8856_b0103_lei_implies_country(self):
        """v8856_m: If B_01.03 c0020 populated, c0040 must be populated."""
        for row in self.b0103:
            if row[1]:  # c0020 (head office LEI)
                self.assertTrue(row[3], f"c0040 (country) empty when c0020={row[1]}")

    def test_v8857_b0103_country_implies_lei(self):
        """v8857_m: If B_01.03 c0040 populated, c0020 must be populated."""
        for row in self.b0103:
            if row[3]:  # c0040 (country)
                self.assertTrue(row[1], f"c0020 (LEI) empty when c0040={row[3]}")

    # --- Category 4: Row completeness (7 tests) ---

    def test_completeness_b0101(self):
        """v8872-v8876: B_01.01 c0020-c0060 must be non-empty."""
        mandatory = {1: "c0020", 2: "c0030", 3: "c0040", 4: "c0050", 5: "c0060"}
        for i, row in enumerate(self.b0101):
            for col_idx, col_name in mandatory.items():
                self.assertTrue(row[col_idx], f"Row {i}: {col_name} is empty")

    @unittest.skip(
        "EBA rule not enforced: subsidiary missing entity_type and hierarchy"
    )
    def test_completeness_b0102(self):
        """v8858-v8865: B_01.02 c0020-c0090 must be non-empty."""
        mandatory = {
            1: "c0020",
            2: "c0030",
            3: "c0040",
            4: "c0050",
            5: "c0060",
            6: "c0070",
            7: "c0080",
            8: "c0090",
        }
        for i, row in enumerate(self.b0102):
            for col_idx, col_name in mandatory.items():
                self.assertTrue(row[col_idx], f"Row {i}: {col_name} is empty")

    @unittest.skip("EBA rule not enforced: contracts missing arrangement type")
    def test_completeness_b0201(self):
        """v8866-v8868: B_02.01 c0020, c0040, c0050 must be non-empty."""
        mandatory = {1: "c0020", 3: "c0040", 4: "c0050"}
        for i, row in enumerate(self.b0201):
            for col_idx, col_name in mandatory.items():
                self.assertTrue(row[col_idx], f"Row {i}: {col_name} is empty")

    @unittest.skip("EBA rule not enforced: some contracts missing start_date")
    def test_completeness_b0202(self):
        """v8869-v8871: B_02.02 c0040, c0070, c0080 must be non-empty."""
        mandatory = {3: "c0040", 6: "c0070", 7: "c0080"}
        for i, row in enumerate(self.b0202):
            for col_idx, col_name in mandatory.items():
                self.assertTrue(row[col_idx], f"Row {i}: {col_name} is empty")

    @unittest.skip("EBA rule not enforced: providers missing parent undertaking code")
    def test_completeness_b0501(self):
        """v8850-v8855: B_05.01 c0020, c0050, c0060, c0070, c0080, c0110 must be non-empty."""
        mandatory = {
            1: "c0020",
            4: "c0050",
            5: "c0060",
            6: "c0070",
            7: "c0080",
            10: "c0110",
        }
        for i, row in enumerate(self.b0501):
            for col_idx, col_name in mandatory.items():
                self.assertTrue(row[col_idx], f"Row {i}: {col_name} is empty")

    @unittest.skip(
        "EBA rule not enforced: functions missing licensed_activity and criticality"
    )
    def test_completeness_b0601(self):
        """v8877-v8883: B_06.01 c0020, c0030, c0050, c0070, c0080, c0090, c0100."""
        mandatory = {
            1: "c0020",
            2: "c0030",
            4: "c0050",
            6: "c0070",
            7: "c0080",
            8: "c0090",
            9: "c0100",
        }
        for i, row in enumerate(self.b0601):
            for col_idx, col_name in mandatory.items():
                self.assertTrue(row[col_idx], f"Row {i}: {col_name} is empty")

    @unittest.skip("EBA rule not enforced: solutions missing substitutability fields")
    def test_completeness_b0701(self):
        """v8884-v8889: B_07.01 c0050, c0070, c0080, c0100, c0110 must be non-empty."""
        mandatory = {4: "c0050", 6: "c0070", 7: "c0080", 9: "c0100", 10: "c0110"}
        for i, row in enumerate(self.b0701):
            for col_idx, col_name in mandatory.items():
                self.assertTrue(row[col_idx], f"Row {i}: {col_name} is empty")


# ===========================================================================
# TDD: Future features (skipped)
# ===========================================================================


class TestTDDFutureFeatures(DoraExportTestMixin, DoraDataFactory, TestCase):
    def test_b0502_rank_greater_than_1(self):
        """Sub-contracting chains should produce rank > 1."""
        parent = Entity.objects.create(
            name="TDD Parent",
            legal_identifiers={"LEI": "TDDP1234567890123456"},
        )
        child = Entity.objects.create(
            name="TDD Child",
            legal_identifiers={"LEI": "TDDC1234567890123456"},
            parent_entity=parent,
        )
        solution = Solution.objects.create(
            name="TDD Service",
            provider_entity=child,
            dora_ict_service_type="eba_ZZ:x755",
        )
        contract = Contract.objects.create(
            name="TDD Contract",
            ref_id="CA-TDD-RANK",
            provider_entity=parent,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        contract.solutions.add(solution)

        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains,
            Contract.objects.filter(pk=contract.pk),
        )
        rows = self._read_csv(buf, "reports/b_05.02.csv")
        data = [r for r in self._data_rows(rows) if r[0] == "CA-TDD-RANK"]
        ranks = [r[4] for r in data]
        self.assertIn("2", ranks)

        contract.solutions.clear()
        contract.delete()
        solution.delete()
        child.delete()
        parent.delete()

    def test_b0502_recipient_code_populated(self):
        """Rank > 1 rows should have recipient entity code+type."""
        parent = Entity.objects.create(
            name="TDD Rcpt Parent",
            legal_identifiers={"LEI": "RCPP1234567890123456"},
        )
        child = Entity.objects.create(
            name="TDD Rcpt Child",
            legal_identifiers={"LEI": "RCPC1234567890123456"},
            parent_entity=parent,
        )
        solution = Solution.objects.create(
            name="TDD Rcpt Service",
            provider_entity=child,
            dora_ict_service_type="eba_ZZ:x755",
        )
        contract = Contract.objects.create(
            name="TDD Rcpt Contract",
            ref_id="CA-TDD-RCPT",
            provider_entity=parent,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        contract.solutions.add(solution)

        buf = self._generate(
            dora_export.generate_b_05_02_supply_chains,
            Contract.objects.filter(pk=contract.pk),
        )
        rows = self._read_csv(buf, "reports/b_05.02.csv")
        data = [r for r in self._data_rows(rows) if r[0] == "CA-TDD-RCPT"]
        rank2_rows = [r for r in data if r[4] == "2"]
        self.assertTrue(len(rank2_rows) > 0)
        self.assertEqual(rank2_rows[0][5], "RCPP1234567890123456")
        self.assertEqual(rank2_rows[0][6], "eba_qCO:qx2000")  # LEI type code

        contract.solutions.clear()
        contract.delete()
        solution.delete()
        child.delete()
        parent.delete()

    @unittest.skip("TDD: not yet implemented")
    def test_b9901_aggregation_data_rows(self):
        """B.99.01 should produce actual aggregate counts."""
        pass

    @unittest.skip("TDD: not yet implemented")
    def test_b0501_latin_name_distinct(self):
        """c0060 should use a separate latin_name field, not duplicate name."""
        pass
