"""Unit tests for the permission-based respondent-view classification.

`get_respondent_scoped_folder_ids` returns the folders where a user is shown the
scoped/stripped *respondent* view. Under the permission model a folder is a
respondent folder iff the user can access compliance assessments there
(`view_complianceassessment`) but lacks the full auditor view (`view_compliance_assessment_full`).

The helper is a thin filter over `RoleAssignment.get_permissions_per_folder`, so we
stub that to exercise the classification logic directly (no DB / IAM cache needed).
"""

import uuid
from types import SimpleNamespace

import iam.models
from core.utils import get_respondent_scoped_folder_ids


def _stub_perms(monkeypatch, perms_by_folder):
    """Make RoleAssignment.get_permissions_per_folder return a canned map."""
    monkeypatch.setattr(
        iam.models.RoleAssignment,
        "get_permissions_per_folder",
        staticmethod(lambda principal, is_recursive=False: perms_by_folder),
    )


class TestRespondentFolderClassification:
    def test_audit_access_without_full_view_is_respondent(self, monkeypatch):
        f = str(uuid.uuid4())
        _stub_perms(monkeypatch, {f: {"view_complianceassessment"}})
        assert get_respondent_scoped_folder_ids(object()) == {uuid.UUID(f)}

    def test_full_view_grant_excludes_folder(self, monkeypatch):
        # Auditor-side roles hold view_compliance_assessment_full → NOT a respondent folder.
        f = str(uuid.uuid4())
        _stub_perms(
            monkeypatch,
            {f: {"view_complianceassessment", "view_compliance_assessment_full"}},
        )
        assert get_respondent_scoped_folder_ids(object()) == set()

    def test_no_audit_access_excluded(self, monkeypatch):
        # A folder the user can touch but with no compliance-assessment access
        # is not a respondent (audit) folder at all.
        f = str(uuid.uuid4())
        _stub_perms(monkeypatch, {f: {"view_riskassessment"}})
        assert get_respondent_scoped_folder_ids(object()) == set()

    def test_dual_hat_full_view_wins(self, monkeypatch):
        # Reader (view_compliance_assessment_full) + auditee on the SAME folder → the folder
        # carries view_compliance_assessment_full, so the user gets the full view there.
        f = str(uuid.uuid4())
        _stub_perms(
            monkeypatch,
            {f: {"view_complianceassessment", "view_compliance_assessment_full"}},
        )
        assert get_respondent_scoped_folder_ids(object()) == set()

    def test_default_deny_for_custom_role(self, monkeypatch):
        # A role that grants audit access but was never granted view_compliance_assessment_full
        # is treated as a respondent (default-deny) — the key safety property.
        f = str(uuid.uuid4())
        _stub_perms(
            monkeypatch,
            {f: {"view_complianceassessment", "change_requirementassessment"}},
        )
        assert get_respondent_scoped_folder_ids(object()) == {uuid.UUID(f)}

    def test_mixed_folders(self, monkeypatch):
        respondent = str(uuid.uuid4())
        auditor = str(uuid.uuid4())
        unrelated = str(uuid.uuid4())
        _stub_perms(
            monkeypatch,
            {
                respondent: {"view_complianceassessment"},
                auditor: {
                    "view_complianceassessment",
                    "view_compliance_assessment_full",
                },
                unrelated: {"view_asset"},
            },
        )
        assert get_respondent_scoped_folder_ids(object()) == {uuid.UUID(respondent)}


class TestComplianceAssessmentViewerRole:
    """The audit detail tells the page which side it is seen from, by the same rule."""

    def _viewer_role(self, folder_id, context):
        from core.serializers import ComplianceAssessmentReadSerializer

        return ComplianceAssessmentReadSerializer(context=context).get_viewer_role(
            SimpleNamespace(folder_id=folder_id)
        )

    def test_respondent_folder(self, monkeypatch):
        f = str(uuid.uuid4())
        _stub_perms(monkeypatch, {f: {"view_complianceassessment"}})
        request = SimpleNamespace(user=object())
        assert self._viewer_role(uuid.UUID(f), {"request": request}) == "respondent"

    def test_full_view_folder(self, monkeypatch):
        f = str(uuid.uuid4())
        _stub_perms(
            monkeypatch,
            {f: {"view_complianceassessment", "view_compliance_assessment_full"}},
        )
        request = SimpleNamespace(user=object())
        assert self._viewer_role(uuid.UUID(f), {"request": request}) == "auditor"

    def test_no_requester(self):
        assert self._viewer_role(uuid.uuid4(), {}) is None
