from django.test import TestCase

from tprm.models import Entity
from tprm import dora_export


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
