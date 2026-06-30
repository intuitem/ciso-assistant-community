"""Unit tests for `BaseModelSerializer.RESPONDENT_PROTECTED_FIELDS`.

This is the high-level, declarative mechanism that strips fields a third-party
respondent must not write (e.g. Evidence.status — an auditor-side decision).
A serializer opts in by listing field names; the base class strips them for any
user whose access to the target object's folder is respondent-scoped.

We stub `get_respondent_scoped_folder_ids` (the same seam used by
test_respondent_view_permission) so no DB / IAM cache is needed.
"""

import uuid
from types import SimpleNamespace

import core.utils
from core.serializers import BaseModelSerializer, EvidenceWriteSerializer


def _request(authenticated=True):
    return SimpleNamespace(user=SimpleNamespace(is_authenticated=authenticated))


def _stub_respondent_folders(monkeypatch, folder_ids):
    monkeypatch.setattr(
        core.utils,
        "get_respondent_scoped_folder_ids",
        lambda user: set(folder_ids),
    )


class _Protected(BaseModelSerializer):
    """Minimal serializer exercising the base behaviour without a model."""

    RESPONDENT_PROTECTED_FIELDS = {"status"}


def _bare(cls):
    """Instantiate a serializer without ModelSerializer field introspection.

    `parent = None` makes it the DRF `context` root so `self.context` resolves
    to our injected `_context`.
    """
    ser = cls.__new__(cls)
    ser.parent = None
    return ser


def _serializer(monkeypatch, *, instance=None, request, respondent_folders):
    _stub_respondent_folders(monkeypatch, respondent_folders)
    ser = _bare(_Protected)
    ser.instance = instance
    ser._context = {"request": request} if request is not None else {}
    return ser


class TestStripOnCreate:
    """On create there is no instance; the folder comes from the payload."""

    def test_stripped_for_respondent(self, monkeypatch):
        fid = uuid.uuid4()
        folder = SimpleNamespace(id=fid)
        ser = _serializer(
            monkeypatch, instance=None, request=_request(), respondent_folders={fid}
        )
        out = ser._strip_respondent_protected_fields(
            {"folder": folder, "status": "approved", "name": "x"}
        )
        assert "status" not in out
        assert out["name"] == "x"

    def test_kept_for_auditor(self, monkeypatch):
        fid = uuid.uuid4()
        folder = SimpleNamespace(id=fid)
        ser = _serializer(
            monkeypatch,
            instance=None,
            request=_request(),
            respondent_folders={uuid.uuid4()},  # some other folder
        )
        out = ser._strip_respondent_protected_fields(
            {"folder": folder, "status": "approved"}
        )
        assert out["status"] == "approved"


class TestStripOnUpdate:
    """On update the folder is resolved from the existing instance."""

    def test_stripped_for_respondent(self, monkeypatch):
        fid = uuid.uuid4()
        instance = SimpleNamespace(folder=SimpleNamespace(id=fid))
        ser = _serializer(
            monkeypatch, instance=instance, request=_request(), respondent_folders={fid}
        )
        out = ser._strip_respondent_protected_fields({"status": "rejected"})
        assert "status" not in out


class TestNoOpCases:
    def test_no_protected_fields_is_noop(self, monkeypatch):
        _stub_respondent_folders(monkeypatch, {uuid.uuid4()})
        ser = _bare(_Protected)
        ser.RESPONDENT_PROTECTED_FIELDS = set()
        ser.instance = None
        ser._context = {"request": _request()}
        attrs = {"status": "approved"}
        assert ser._strip_respondent_protected_fields(attrs) is attrs

    def test_unauthenticated_request_is_noop(self, monkeypatch):
        fid = uuid.uuid4()
        ser = _serializer(
            monkeypatch,
            instance=None,
            request=_request(authenticated=False),
            respondent_folders={fid},
        )
        out = ser._strip_respondent_protected_fields(
            {"folder": SimpleNamespace(id=fid), "status": "approved"}
        )
        assert out["status"] == "approved"

    def test_no_resolvable_folder_is_noop(self, monkeypatch):
        ser = _serializer(
            monkeypatch,
            instance=None,
            request=_request(),
            respondent_folders={uuid.uuid4()},
        )
        out = ser._strip_respondent_protected_fields({"status": "approved"})
        assert out["status"] == "approved"


def test_evidence_serializer_declares_status_protected():
    # The concrete opt-in that fixes the reported TPRM bug.
    assert "status" in EvidenceWriteSerializer.RESPONDENT_PROTECTED_FIELDS
