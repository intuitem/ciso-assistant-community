import csv
import io
import json
import zipfile
from datetime import date

from django.test import TestCase

from core.models import Asset
from tprm.models import Entity, Contract, Solution
from tprm import dora_export


class DoraExportHelpersTestCase(TestCase):
    def test_get_entity_identifier(self):
        # Empty entity
        entity = Entity()
        self.assertEqual(dora_export.get_entity_identifier(entity), ("", ""))

        # Priority test: LEI > EUID > VAT > DUNS
        entity.legal_identifiers = {
            "DUNS": "1111",
            "VAT": "2222",
            "EUID": "3333",
            "LEI": "4444",
        }
        self.assertEqual(
            dora_export.get_entity_identifier(entity), ("4444", "eba_qCO:qx2000")
        )

        entity.legal_identifiers = {"VAT": "2222", "DUNS": "1111"}
        self.assertEqual(
            dora_export.get_entity_identifier(entity), ("2222", "eba_qCO:qx2004")
        )

        entity.legal_identifiers = {"UNKNOWN": "9999"}
        self.assertEqual(
            dora_export.get_entity_identifier(entity), ("9999", "eba_qCO:qx2003")
        )

    def test_format_date(self):
        d = date(2023, 5, 17)
        self.assertEqual(dora_export.format_date(d), "2023-05-17")
        self.assertEqual(dora_export.format_date(None), "")


class DoraExportMetadataTestCase(TestCase):
    def setUp(self):
        self.entity_with_auth = Entity.objects.create(
            name="Test Entity With Auth",
            legal_identifiers={"LEI": "123456789ABCDEFGHI00"},
            dora_competent_authority="FSMA",
        )
        self.entity_without_auth = Entity.objects.create(
            name="Test Entity Without Auth",
            legal_identifiers={"LEI": "00IHGFEDCBA987654321"},
        )
        self.entity_no_lei = Entity.objects.create(
            name="Test Entity No LEI",
            legal_identifiers={"VAT": "BE0123456789"},
        )

    def test_get_dora_export_metadata_standard(self):
        """Test metadata generation for standard EBA format."""
        meta = dora_export.get_dora_export_metadata(
            self.entity_with_auth, style=dora_export.EXPORT_STYLE_STANDARD
        )

        self.assertEqual(
            meta["folder_prefix"], "LEI_123456789ABCDEFGHI00.CON_FSMA_DOR_DORA_ROI"
        )
        self.assertEqual(
            meta["filename"], "LEI_123456789ABCDEFGHI00.CON_FSMA_DOR_DORA_ROI.zip"
        )
        self.assertEqual(meta["entity_id"], "rs:123456789ABCDEFGHI00.CON")
        self.assertEqual(meta["competent_authority"], "FSMA")

    def test_get_dora_export_metadata_standard_unknown_auth(self):
        """Test standard format with missing competent authority."""
        meta = dora_export.get_dora_export_metadata(
            self.entity_without_auth, style=dora_export.EXPORT_STYLE_STANDARD
        )

        self.assertEqual(
            meta["folder_prefix"], "LEI_00IHGFEDCBA987654321.CON_UNKNOWN_DOR_DORA_ROI"
        )
        self.assertEqual(
            meta["filename"], "LEI_00IHGFEDCBA987654321.CON_UNKNOWN_DOR_DORA_ROI.zip"
        )
        self.assertEqual(meta["entity_id"], "rs:00IHGFEDCBA987654321.CON")
        self.assertEqual(meta["competent_authority"], "UNKNOWN")

    def test_get_dora_export_metadata_onegate(self):
        """Test metadata generation for OneGate format."""
        meta = dora_export.get_dora_export_metadata(
            self.entity_with_auth, style=dora_export.EXPORT_STYLE_ONEGATE
        )

        self.assertEqual(
            meta["folder_prefix"], "LEI_123456789ABCDEFGHI00.FSMA_DOR_DORA_ROI"
        )
        self.assertEqual(
            meta["filename"], "LEI_123456789ABCDEFGHI00.FSMA_DOR_DORA_ROI.zip"
        )
        self.assertEqual(meta["entity_id"], "rs:123456789ABCDEFGHI00.CON")
        self.assertEqual(meta["competent_authority"], "FSMA")

    def test_get_dora_export_metadata_onegate_default_auth(self):
        """Test OneGate format defaults to NBB if authority is missing."""
        meta = dora_export.get_dora_export_metadata(
            self.entity_without_auth, style=dora_export.EXPORT_STYLE_ONEGATE
        )

        self.assertEqual(
            meta["folder_prefix"], "LEI_00IHGFEDCBA987654321.NBB_DOR_DORA_ROI"
        )
        self.assertEqual(
            meta["filename"], "LEI_00IHGFEDCBA987654321.NBB_DOR_DORA_ROI.zip"
        )
        self.assertEqual(meta["entity_id"], "rs:00IHGFEDCBA987654321.CON")
        self.assertEqual(meta["competent_authority"], "NBB")

    def test_get_dora_export_metadata_no_lei(self):
        """Test that missing LEI raises ValueError."""
        with self.assertRaisesMessage(
            ValueError, "Cannot generate DORA RoI export: main entity has no LEI."
        ):
            dora_export.get_dora_export_metadata(self.entity_no_lei)


class DoraExportReportsTestCase(TestCase):
    def setUp(self):
        # Set up a robust dataset for all reports
        self.main_entity = Entity.objects.create(
            name="Main Entity",
            legal_identifiers={"LEI": "MAIN1234567890123456"},
            country="BE",
            currency="EUR",
            dora_entity_type="bank",
        )

        self.subsidiary = Entity.objects.create(
            name="Subsidiary Entity",
            legal_identifiers={"LEI": "SUB00000000000000000"},
            country="FR",
            currency="EUR",
            parent_entity=self.main_entity,
            dora_provider_person_type="legal",  # Indicates subsidiary
        )

        self.branch = Entity.objects.create(
            name="Branch Entity",
            legal_identifiers={"VAT": "BE0999999999"},
            country="BE",
            parent_entity=self.main_entity,
            # No dora_provider_person_type for branches
        )

        self.provider = Entity.objects.create(
            name="Third Party Provider",
            legal_identifiers={"LEI": "PROV1234567890123456"},
            country="US",
            dora_provider_person_type="legal",
        )

        self.intragroup_provider = Entity.objects.create(
            name="Intragroup Provider",
            legal_identifiers={"LEI": "INTRA000000000000000"},
            parent_entity=self.main_entity,
        )

        self.business_function = Asset.objects.create(
            name="Critical Payment Service",
            is_business_function=True,
            disaster_recovery_objectives={
                "objectives": {"rto": {"value": 2}, "rpo": {"value": 1}}
            },
            dora_criticality_assessment="eba_BT:x28",
        )

        self.solution = Solution.objects.create(
            name="Cloud Hosting",
            provider_entity=self.provider,
            dora_ict_service_type="cloud",
            storage_of_data=True,
            data_location_storage="US",
        )
        self.solution.assets.add(self.business_function)

        self.contract = Contract.objects.create(
            name="Main Cloud Contract",
            provider_entity=self.provider,
            beneficiary_entity=self.main_entity,
            annual_expense=100000,
            currency="EUR",
            is_intragroup=False,
        )
        self.contract.solutions.add(self.solution)

        self.overarching_contract = Contract.objects.create(
            name="Group Framework Agreement",
            provider_entity=self.intragroup_provider,
            beneficiary_entity=self.main_entity,
            is_intragroup=True,
        )

        self.sub_contract = Contract.objects.create(
            name="Local IT Support",
            provider_entity=self.intragroup_provider,
            beneficiary_entity=self.subsidiary,
            is_intragroup=True,
            overarching_contract=self.overarching_contract,
        )

    def _read_csv_from_zip(self, zip_buffer, filename):
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as z:
            with z.open(filename) as f:
                content = f.read().decode("utf-8")
                return list(csv.reader(io.StringIO(content)))

    def _read_json_from_zip(self, zip_buffer, filename):
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as z:
            with z.open(filename) as f:
                return json.loads(f.read().decode("utf-8"))

    def test_generate_b_01_01_main_entity(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_01_01_main_entity(z, self.main_entity)

        rows = self._read_csv_from_zip(buf, "reports/b_01.01.csv")
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[0], ["c0010", "c0020", "c0030", "c0040", "c0050", "c0060"]
        )
        self.assertEqual(rows[1][0], "MAIN1234567890123456")
        self.assertEqual(rows[1][1], "Main Entity")
        self.assertEqual(rows[1][2], "eba_GA:BE")

    def test_generate_b_01_02_entities(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_01_02_entities(
                z, self.main_entity, [self.main_entity, self.subsidiary]
            )

        rows = self._read_csv_from_zip(buf, "reports/b_01.02.csv")
        self.assertEqual(len(rows), 3)  # Header + 2 entities
        self.assertEqual(rows[0][0], "c0010")

        main_row = next(r for r in rows[1:] if r[0] == "MAIN1234567890123456")
        self.assertEqual(
            main_row[5], "MAIN1234567890123456"
        )  # Parent LEI is itself if no parent
        self.assertEqual(main_row[9], "eba_CU:EUR")

        sub_row = next(r for r in rows[1:] if r[0] == "SUB00000000000000000")
        self.assertEqual(sub_row[5], "MAIN1234567890123456")  # Parent LEI is main

    def test_generate_b_01_03_branches(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_01_03_branches(z, [self.branch])

        rows = self._read_csv_from_zip(buf, "reports/b_01.03.csv")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "BE0999999999")  # Branch code
        self.assertEqual(rows[1][1], "MAIN1234567890123456")  # Head office LEI

    def test_generate_b_02_01_contracts(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_02_01_contracts(z, Contract.objects.all())

        rows = self._read_csv_from_zip(buf, "reports/b_02.01.csv")
        self.assertEqual(len(rows), 4)  # Header + 3 contracts

        # Check sub_contract to see overarching reference
        sub_row = next(r for r in rows[1:] if r[0] == str(self.sub_contract.id))
        self.assertEqual(sub_row[2], str(self.overarching_contract.id))

    def test_generate_b_02_02_ict_services(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_02_02_ict_services(z, Contract.objects.all())

        rows = self._read_csv_from_zip(buf, "reports/b_02.02.csv")
        self.assertEqual(
            len(rows), 2
        )  # Header + 1 combination (contract + solution + asset)
        self.assertEqual(rows[1][1], "MAIN1234567890123456")  # Beneficiary LEI
        self.assertEqual(rows[1][2], "PROV1234567890123456")  # Provider code
        self.assertEqual(rows[1][4], str(self.business_function.id))  # Function ID
        self.assertEqual(rows[1][13], "eba_BT:x28")  # Storage of data
        self.assertEqual(rows[1][14], "eba_GA:US")  # Data location

    def test_generate_b_02_03_intragroup_contracts(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_02_03_intragroup_contracts(z, Contract.objects.all())

        rows = self._read_csv_from_zip(buf, "reports/b_02.03.csv")
        self.assertEqual(len(rows), 2)  # Header + 1 (only sub_contract has overarching)
        self.assertEqual(rows[1][0], str(self.sub_contract.id))
        self.assertEqual(rows[1][1], str(self.overarching_contract.id))
        self.assertEqual(rows[1][2], "true")

    def test_generate_b_03_01_signing_entities(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_03_01_signing_entities(
                z, self.main_entity, Contract.objects.all()
            )

        rows = self._read_csv_from_zip(buf, "reports/b_03.01.csv")
        self.assertEqual(len(rows), 4)  # Header + 3 contracts
        for row in rows[1:]:
            self.assertEqual(row[1], "MAIN1234567890123456")
            self.assertEqual(row[2], "true")

    def test_generate_b_03_02_ict_providers(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_03_02_ict_providers(z, Contract.objects.all())

        rows = self._read_csv_from_zip(buf, "reports/b_03.02.csv")
        self.assertEqual(len(rows), 2)  # Header + 1 third party contract
        self.assertEqual(rows[1][0], str(self.contract.id))
        self.assertEqual(rows[1][1], "PROV1234567890123456")

    def test_generate_b_03_03_intragroup_providers(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_03_03_intragroup_providers(
                z, self.main_entity, Contract.objects.all()
            )

        rows = self._read_csv_from_zip(buf, "reports/b_03.03.csv")
        self.assertEqual(len(rows), 3)  # Header + 2 intragroup
        for row in rows[1:]:
            self.assertEqual(row[1], "INTRA000000000000000")
            self.assertEqual(row[2], "true")

    def test_generate_b_04_01_service_users(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_04_01_service_users(
                z, [self.branch], Contract.objects.all()
            )

        rows = self._read_csv_from_zip(buf, "reports/b_04.01.csv")
        # 3 contracts -> 3 rows for beneficiaries. main_entity has 1 branch -> +2 rows for main_entity contracts
        self.assertEqual(len(rows), 6)  # Header + 5 rows

        main_contracts = [str(self.contract.id), str(self.overarching_contract.id)]
        for c_id in main_contracts:
            c_rows = [r for r in rows if r[0] == c_id]
            self.assertEqual(len(c_rows), 2)  # 1 for beneficiary, 1 for branch

            non_branch = next(r for r in c_rows if r[2] == "eba_ZZ:x839")
            branch_row = next(r for r in c_rows if r[2] == "eba_ZZ:x838")

            self.assertEqual(non_branch[3], "")
            self.assertEqual(branch_row[3], "BE0999999999")

    def test_generate_b_05_01_provider_details(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_05_01_provider_details(
                z, self.main_entity, Contract.objects.all()
            )

        rows = self._read_csv_from_zip(buf, "reports/b_05.01.csv")
        self.assertEqual(len(rows), 2)  # Header + 1 third party provider
        self.assertEqual(rows[1][0], "PROV1234567890123456")
        self.assertEqual(rows[1][4], "Third Party Provider")
        self.assertEqual(rows[1][7], "eba_GA:US")
        self.assertEqual(
            rows[1][9], "100000.0"
        )  # Annual expense string representation might differ based on model, but we compare string if it's decimal

    def test_generate_b_05_02_supply_chains(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_05_02_supply_chains(z, Contract.objects.all())

        rows = self._read_csv_from_zip(buf, "reports/b_05.02.csv")
        self.assertEqual(len(rows), 2)  # Header + 1 supply chain row
        self.assertEqual(rows[1][0], str(self.contract.id))
        self.assertEqual(rows[1][1], "cloud")
        self.assertEqual(rows[1][4], "1")  # Rank

    def test_generate_b_06_01_functions(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_06_01_functions(
                z, self.main_entity, Asset.objects.filter(is_business_function=True)
            )

        rows = self._read_csv_from_zip(buf, "reports/b_06.01.csv")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(self.business_function.id))
        self.assertEqual(rows[1][4], "eba_BT:x28")
        self.assertEqual(rows[1][7], "2")  # RTO
        self.assertEqual(rows[1][8], "1")  # RPO

    def test_generate_b_07_01_assessment(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_07_01_assessment(z, Contract.objects.all())

        rows = self._read_csv_from_zip(buf, "reports/b_07.01.csv")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(self.contract.id))
        self.assertEqual(rows[1][3], "cloud")  # Service type

    def test_generate_b_99_01_aggregation(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_b_99_01_aggregation(
                z, Contract.objects.all(), Asset.objects.all()
            )

        rows = self._read_csv_from_zip(buf, "reports/b_99.01.csv")
        self.assertEqual(len(rows), 1)  # Only header implemented currently

    def test_generate_filing_indicators(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_filing_indicators(z)

        rows = self._read_csv_from_zip(buf, "reports/FilingIndicators.csv")
        self.assertTrue(len(rows) > 10)
        self.assertEqual(rows[0], ["templateID", "reported"])
        for row in rows[1:]:
            self.assertEqual(row[1], "true")

    def test_generate_parameters(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_parameters(z, self.main_entity)

        rows = self._read_csv_from_zip(buf, "reports/parameters.csv")
        params = dict(rows[1:])
        self.assertEqual(params["entityID"], "rs:MAIN1234567890123456.CON")
        self.assertEqual(params["baseCurrency"], "eba_CU:EUR")

    def test_generate_report_package_json(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_report_package_json(z)

        data = self._read_json_from_zip(buf, "META-INF/reportPackage.json")
        self.assertEqual(
            data["documentInfo"]["documentType"], "https://xbrl.org/report-package/2023"
        )

    def test_generate_report_json(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            dora_export.generate_report_json(z)

        data = self._read_json_from_zip(buf, "reports/report.json")
        self.assertEqual(
            data["documentInfo"]["documentType"], "https://xbrl.org/2021/xbrl-csv"
        )
