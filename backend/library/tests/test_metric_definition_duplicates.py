import importlib.util
from pathlib import Path

import openpyxl
import pytest

from core.models import StoredLibrary
from library.utils import LibraryImporter


def _converter():
    script = Path(__file__).resolve().parents[2] / "scripts" / "convert_library_v2.py"
    spec = importlib.util.spec_from_file_location("convert_library_v2", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_converter_rejects_duplicate_metric_ref_id():
    with pytest.raises(ValueError, match="Duplicate ref_id 'M1'"):
        _converter()._handle_metric_definitions(
            _metric_sheet("M1", "M1"), {"objects": {}}, 0, False
        )


def _metric_sheet(*ref_ids):
    ws = openpyxl.Workbook().active
    ws.append(["ref_id", "name"])
    for ref_id in ref_ids:
        ws.append([ref_id, "Metric"])
    return {"meta": {"base_urn": "urn:test:risk:metric"}, "content_sheet": ws}


def test_converter_rejects_duplicate_metric_ref_id_across_sheets():
    converter = _converter()
    library = {"objects": {}}
    converter._handle_metric_definitions(_metric_sheet("M1"), library, 0, False)

    with pytest.raises(ValueError, match="Duplicate ref_id 'm1'"):
        converter._handle_metric_definitions(_metric_sheet("m1"), library, 0, False)


@pytest.mark.django_db
def test_importer_rejects_duplicate_metric_urn():
    importer = LibraryImporter(StoredLibrary())
    error = importer.init_metric_definitions(
        [
            {"urn": "urn:test:risk:metric:m1", "ref_id": "M1"},
            {"urn": "URN:test:risk:metric:M1", "ref_id": "M1"},
        ]
    )

    assert error is not None
    assert error.startswith("[METRIC_DEFINITION_ERROR]")
    assert "Duplicate URN" in error
