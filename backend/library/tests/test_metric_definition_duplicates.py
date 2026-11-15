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
    ws = openpyxl.Workbook().active
    ws.append(["ref_id", "name"])
    ws.append(["M1", "First"])
    ws.append(["M1", "Second"])
    obj = {"meta": {"base_urn": "urn:test:risk:metric"}, "content_sheet": ws}

    with pytest.raises(ValueError, match="Duplicate ref_id 'M1'"):
        _converter()._handle_metric_definitions(obj, {"objects": {}}, 0, False)


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
