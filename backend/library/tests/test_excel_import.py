from django.test import SimpleTestCase
from django.conf import settings
import os
import io
from library.importers.excel import ExcelImporter


class ExcelImporterTest(SimpleTestCase):
    def test_parse_example_framework(self):
        # Locate the example file relative to the project root
        # settings.BASE_DIR is usually 'backend'
        base_dir = settings.BASE_DIR.parent
        file_path = os.path.join(base_dir, "tools", "example_framework.xlsx")

        if not os.path.exists(file_path):
            self.skipTest(f"Example file not found at {file_path}")

        with open(file_path, "rb") as f:
            result = ExcelImporter.parse(f)

        self.assertIsInstance(result, dict)
        self.assertIn("urn", result)
        self.assertIn("objects", result)
        # Check for framework object which is standard in the example
        self.assertIn("framework", result["objects"])

    def test_parse_invalid_file(self):
        # Create a dummy file that isn't a valid Excel
        dummy_file = io.BytesIO(b"not an excel file")
        
        with self.assertRaises(Exception): # openpyxl will raise an error (BadZipFile or similar)
            ExcelImporter.parse(dummy_file)
