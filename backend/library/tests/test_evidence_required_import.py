from core.models import LoadedLibrary, RequirementNode, StoredLibrary
from django.test import TestCase


LIBRARY = """
urn: urn:intuitem:test:library:evidence-required
locale: en
ref_id: EVIDENCE-REQUIRED
name: Evidence required
description: Evidence required flag
copyright: Test
version: {version}
publication_date: 2026-10-28
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:evidence-required
    ref_id: EVIDENCE-REQUIRED
    name: Evidence required
    requirement_nodes:
      - urn: urn:intuitem:test:req_node:evidence-required:flagged
        assessable: true
        depth: 1
        ref_id: FLAGGED
        name: Flagged
        evidence_required: {flagged}
      - urn: urn:intuitem:test:req_node:evidence-required:loose
        assessable: true
        depth: 1
        ref_id: LOOSE
        name: Loose
        evidence_required: {loose}
""".lstrip()

FLAGGED_URN = "urn:intuitem:test:req_node:evidence-required:flagged"
LOOSE_URN = "urn:intuitem:test:req_node:evidence-required:loose"


def _store(version, flagged, loose):
    stored, error = StoredLibrary.store_library_content(
        LIBRARY.format(version=version, flagged=flagged, loose=loose).encode("utf-8")
    )
    assert error is None
    assert stored is not None
    return stored


def _flag(urn):
    return RequirementNode.objects.get(urn=urn).evidence_required


class TestEvidenceRequiredImport(TestCase):
    def test_flag_survives_import_and_update(self):
        stored = _store(1, "true", '"x"')
        assert stored.load() is None
        assert _flag(FLAGGED_URN) is True
        # Only a real boolean true sets the flag.
        assert _flag(LOOSE_URN) is False

        _store(2, "false", '"x"')
        loaded = LoadedLibrary.objects.get(urn=stored.urn)
        assert loaded.update(strategy="clamp") is None
        assert _flag(FLAGGED_URN) is False
        assert _flag(LOOSE_URN) is False

        _store(3, "true", "true")
        assert loaded.update(strategy="clamp") is None
        assert _flag(FLAGGED_URN) is True
        assert _flag(LOOSE_URN) is True
