import pytest
from django.urls import reverse

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from global_settings.models import GlobalSettings
from iam.models import Folder, User


@pytest.mark.django_db
class TestEvidenceRevisionReview:
    """The review record lives on the revision: who uploaded, who decided, when, why."""

    def _admin(self):
        return User.objects.get(email="admin@tests.com")

    def _revision(self, client, link="https://example.com/proof"):
        evidence = Evidence.objects.create(
            name="SOC 2 report", folder=Folder.get_root_folder()
        )
        response = client.post(
            reverse("evidence-revisions-list"),
            {"evidence": str(evidence.id), "link": link},
            format="json",
        )
        assert response.status_code == 201, response.json()
        return EvidenceRevision.objects.get(id=response.json()["id"])

    def _review(self, client, revision, decision, comment=""):
        return client.post(
            reverse("evidence-revisions-review", args=[revision.id]),
            {"decision": decision, "comment": comment},
            format="json",
        )

    def test_uploader_is_recorded(self, authenticated_client):
        revision = self._revision(authenticated_client)
        assert revision.uploaded_by == self._admin()
        assert revision.review_status == EvidenceRevision.ReviewStatus.PENDING

    def test_approve_records_reviewer_and_mirrors_status(self, authenticated_client):
        revision = self._revision(authenticated_client)
        response = self._review(authenticated_client, revision, "approved", "ok")
        assert response.status_code == 200, response.json()
        revision.refresh_from_db()
        assert revision.review_status == "approved"
        assert revision.reviewed_by == self._admin()
        assert revision.reviewed_at is not None
        assert revision.review_comment == "ok"
        assert revision.evidence.status == Evidence.Status.APPROVED

    def test_reject_needs_a_comment(self, authenticated_client):
        revision = self._revision(authenticated_client)
        response = self._review(authenticated_client, revision, "rejected")
        assert response.status_code == 400
        revision.refresh_from_db()
        assert revision.review_status == EvidenceRevision.ReviewStatus.PENDING

    def test_unknown_decision_is_refused(self, authenticated_client):
        revision = self._revision(authenticated_client)
        assert (
            self._review(authenticated_client, revision, "pending").status_code == 400
        )

    def test_four_eyes_blocks_the_uploader_only_when_enabled(
        self, authenticated_client
    ):
        revision = self._revision(authenticated_client)
        general, _ = GlobalSettings.objects.get_or_create(name="general")
        general.value = {**(general.value or {}), "evidence_four_eyes": True}
        general.save()
        assert (
            self._review(authenticated_client, revision, "approved").status_code == 400
        )

        general.value["evidence_four_eyes"] = False
        general.save()
        assert (
            self._review(authenticated_client, revision, "approved").status_code == 200
        )

    def test_new_content_voids_the_review(self, authenticated_client):
        revision = self._revision(authenticated_client)
        self._review(authenticated_client, revision, "approved")
        revision.refresh_from_db()
        revision.link = "https://example.com/other"
        revision.save()
        revision.refresh_from_db()
        assert revision.review_status == EvidenceRevision.ReviewStatus.PENDING
        assert revision.reviewed_by is None
        assert revision.evidence.status == Evidence.Status.IN_REVIEW

    def test_review_fields_are_not_writable_by_patch(self, authenticated_client):
        revision = self._revision(authenticated_client)
        authenticated_client.patch(
            reverse("evidence-revisions-detail", args=[revision.id]),
            {"review_status": "approved"},
            format="json",
        )
        revision.refresh_from_db()
        assert revision.review_status == EvidenceRevision.ReviewStatus.PENDING

    def test_status_select_is_recorded_on_the_latest_revision(
        self, authenticated_client
    ):
        revision = self._revision(authenticated_client)
        response = authenticated_client.patch(
            reverse("evidences-detail", args=[revision.evidence_id]),
            {"status": "approved"},
            format="json",
        )
        assert response.status_code == 200, response.json()
        revision.refresh_from_db()
        assert revision.review_status == "approved"
        assert revision.reviewed_by == self._admin()

    def test_queue_filter_follows_the_latest_revision(self, authenticated_client):
        first = self._revision(authenticated_client)
        self._review(authenticated_client, first, "approved")
        url = reverse("evidences-list")

        def ids(status):
            body = authenticated_client.get(url, {"review_status": status}).json()
            return {e["id"] for e in body["results"]}

        evidence_id = str(first.evidence_id)
        assert evidence_id in ids("approved")
        assert evidence_id not in ids("pending")

        # A newer revision puts the evidence back in the queue.
        authenticated_client.post(
            reverse("evidence-revisions-list"),
            {"evidence": evidence_id, "link": "https://example.com/v2"},
            format="json",
        )
        assert evidence_id in ids("pending")
        assert evidence_id not in ids("approved")

        row = authenticated_client.get(
            reverse("evidences-detail", args=[evidence_id])
        ).json()
        assert row["latest_revision"]["version"] == 2
        assert row["latest_revision"]["review_status"] == "pending"
        assert row["latest_revision"]["uploaded_by"]

    def test_decision_on_a_superseded_revision_is_refused(self, authenticated_client):
        old = self._revision(authenticated_client)
        authenticated_client.post(
            reverse("evidence-revisions-list"),
            {"evidence": str(old.evidence_id), "link": "https://example.com/v2"},
            format="json",
        )
        assert self._review(authenticated_client, old, "approved").status_code == 409
        old.refresh_from_db()
        assert old.review_status == EvidenceRevision.ReviewStatus.PENDING

    def test_first_file_on_approved_evidence_goes_back_to_review(self):
        evidence = Evidence.objects.create(
            name="Pen test", folder=Folder.get_root_folder()
        )
        evidence.status = Evidence.Status.APPROVED
        evidence.save()
        EvidenceRevision.objects.create(evidence=evidence, link="https://example.com")
        evidence.refresh_from_db()
        assert evidence.status == Evidence.Status.IN_REVIEW

    def test_third_parties_see_the_outcome_not_who_or_why(self, authenticated_client):
        from types import SimpleNamespace

        from core.serializers import (
            EvidenceReadSerializer,
            EvidenceRevisionReadSerializer,
        )

        revision = self._revision(authenticated_client)
        self._review(authenticated_client, revision, "rejected", "wrong scope")
        revision.refresh_from_db()
        vendor = User.objects.create_user("rep@vendor.test", is_third_party=True)
        for user, hidden in ((vendor, True), (self._admin(), False)):
            ctx = {"request": SimpleNamespace(user=user)}
            rev = EvidenceRevisionReadSerializer(revision, context=ctx).data
            ev = EvidenceReadSerializer(revision.evidence, context=ctx).data
            assert rev["review_status"] == "rejected"
            assert (rev["review_comment"] is None) is hidden
            assert (rev["reviewed_by"] is None) is hidden
            assert (rev["uploaded_by"] is None) is hidden
            assert (ev["latest_revision"]["uploaded_by"] is None) is hidden

    def test_undo_puts_the_decision_back_in_the_queue(self, authenticated_client):
        revision = self._revision(authenticated_client)
        assert (
            self._review(authenticated_client, revision, "approved").status_code == 200
        )
        response = self._review(authenticated_client, revision, "pending")
        assert response.status_code == 200, response.json()
        revision.refresh_from_db()
        assert revision.review_status == "pending"
        assert revision.reviewed_by is None and revision.reviewed_at is None
        assert Evidence.objects.get(pk=revision.evidence_id).status == "in_review"
        # Nothing left to undo.
        assert (
            self._review(authenticated_client, revision, "pending").status_code == 400
        )

    def test_only_the_reviewer_can_undo(self, authenticated_client):
        revision = self._revision(authenticated_client)
        self._review(authenticated_client, revision, "approved")
        other = User.objects.create_user(email="other@tests.com")
        EvidenceRevision.objects.filter(pk=revision.pk).update(reviewed_by=other)
        response = self._review(authenticated_client, revision, "pending")
        assert response.status_code == 400
        assert response.json() == {"decision": ["cannot_undo"]}

    def test_audit_context_crawls_direct_and_indirect_evidences(
        self, authenticated_client
    ):
        root = Folder.get_root_folder()
        framework = Framework.objects.create(
            urn="urn:test:review:framework", name="FW", folder=root
        )
        audit = ComplianceAssessment.objects.create(
            name="Audit",
            perimeter=Perimeter.objects.create(name="P", folder=root),
            framework=framework,
            folder=root,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=audit,
            requirement=RequirementNode.objects.create(
                urn="urn:test:review:req",
                framework=framework,
                folder=root,
                assessable=True,
            ),
            folder=root,
        )
        control = AppliedControl.objects.create(name="MFA", folder=root)
        ra.applied_controls.add(control)
        make = lambda n: Evidence.objects.create(name=n, folder=root)  # noqa: E731
        direct, on_requirement, via_control, unrelated = map(
            make, ["direct", "on requirement", "via control", "unrelated"]
        )
        audit.evidences.add(direct)
        ra.evidences.add(on_requirement)
        control.evidences.add(via_control)

        body = authenticated_client.get(
            reverse("evidences-list"), {"compliance_assessment": str(audit.id)}
        ).json()
        assert {e["name"] for e in body["results"]} == {
            "direct",
            "on requirement",
            "via control",
        }
