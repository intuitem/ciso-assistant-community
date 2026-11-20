import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse
from knox.models import AuthToken
from rest_framework.test import APIClient

from enterprise_core.views import ObjectAuditTrailView
from iam.models import Folder, User, UserGroup

# Logged on users, served only to who has the full view of the user.
FULL_VIEW_LOG_FIELDS = {
    "is_superuser",
    "expiry_date",
    "keep_local_login",
    "is_scim_managed",
    "is_jit_provisioned",
    "observation",
    "last_login",
    "first_login",
}


def _client(user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


@pytest.mark.django_db
class TestUserAuditTrailFullViewFields:
    """A user's audit trail shows full-view fields to whoever the users API shows
    them to. A Global analyst holds the audit trail permission on Global but only
    the base view of users."""

    @pytest.fixture
    def target(self, app_config):
        target = User.objects.create_user("aaron.target@tests.com")
        target.expiry_date = "2030-01-01"
        target.keep_local_login = True
        target.observation = "contractor, leaves in January"
        target.save()
        target.first_name = "Aaron"
        target.save()
        return target

    @pytest.fixture
    def analyst(self, app_config):
        analyst = User.objects.create_user("global.analyst@tests.com")
        UserGroup.objects.get(
            name="BI-UG-ANA", folder=Folder.get_root_folder()
        ).user_set.add(analyst)
        return analyst

    @staticmethod
    def _trail(client, user_id):
        response = client.get(
            reverse("object-audit-trail"),
            {"content_type": "user", "object_id": str(user_id)},
        )
        assert response.status_code == 200, response.content
        return response.data

    @staticmethod
    def _fields(trail):
        return {field for entry in trail for field in entry["changes"] or {}}

    def test_base_viewer_gets_base_changes_only(self, target, analyst):
        trail = self._trail(_client(analyst), target.id)
        assert not FULL_VIEW_LOG_FIELDS & self._fields(trail)
        assert {"email", "first_name"} <= self._fields(trail)
        # The update that only touched full-view fields is left out, not shown empty.
        assert [entry["action"] for entry in trail] == ["update", "create"]

    def test_base_viewer_gets_no_field_outside_the_base_view(
        self, target, analyst, admin_client
    ):
        # The users API shows none of these to a base viewer: SCIM ids, group
        # membership (logged with group names), a field since removed from the model.
        target.scim_external_id = "okta-00u1a2b3"
        target.save()
        target.user_groups.add(
            UserGroup.objects.get(name="BI-UG-ANA", folder=Folder.get_root_folder())
        )
        LogEntry.objects.create(
            content_type=ContentType.objects.get_for_model(User),
            object_pk=str(target.id),
            object_repr=str(target),
            action=LogEntry.Action.UPDATE,
            changes={"is_published": ["False", "True"]},
        )
        others = {"scim_external_id", "user_groups", "is_published"}
        trail = self._trail(_client(analyst), target.id)
        assert not others & self._fields(trail)
        assert [entry["action"] for entry in trail] == ["update", "create"]
        assert others <= self._fields(self._trail(admin_client, target.id))

    def test_password_resets_do_not_date_full_view_changes(self, analyst, admin_client):
        # A user without local login gets a new unusable password on every save, so
        # changing a full-view field alone also logs a redacted password change.
        sso_user = User.objects.create_user("sso.user@tests.com")
        sso_user.is_jit_provisioned = True
        sso_user.save()
        sso_user.observation = "moved to the Lyon office"
        sso_user.save()
        trail = self._trail(_client(analyst), sso_user.id)
        assert "password" not in self._fields(trail)
        assert [entry["action"] for entry in trail] == ["create"]
        assert {"observation", "password"} <= self._fields(
            self._trail(admin_client, sso_user.id)
        )

    def test_sign_ins_do_not_crowd_out_base_changes(self, target, analyst, monkeypatch):
        # Every sign-in logs an update of last_login alone. Past the entry limit, they
        # must not push the changes a base viewer may see out of the trail.
        monkeypatch.setattr(ObjectAuditTrailView, "MAX_ENTRIES", 3)
        for _ in range(4):
            Client().force_login(target)
        trail = self._trail(_client(analyst), target.id)
        assert [entry["action"] for entry in trail] == ["update", "create"]
        assert "first_name" in self._fields(trail)

    def test_full_viewer_gets_full_view_changes(self, target, admin_client):
        trail = self._trail(admin_client, target.id)
        assert {"expiry_date", "keep_local_login", "observation"} <= self._fields(trail)
        assert [entry["action"] for entry in trail] == ["update", "update", "create"]

    def test_self_gets_own_full_view_changes(self, analyst):
        analyst.keep_local_login = True
        analyst.save()
        assert "keep_local_login" in self._fields(
            self._trail(_client(analyst), analyst.id)
        )

    def test_deleted_user_stays_masked(self, target, analyst, admin_client):
        target_id = target.id
        target.delete()
        assert not FULL_VIEW_LOG_FIELDS & self._fields(
            self._trail(_client(analyst), target_id)
        )
        assert "expiry_date" in self._fields(self._trail(admin_client, target_id))


@pytest.mark.django_db
class TestComplianceAssessmentAuditTrail:
    """An audit's trail also holds the changes to its requirement assessments, each
    entry naming the object it is about."""

    @pytest.fixture
    def audit(self, app_config):
        from core.models import (
            ComplianceAssessment,
            Framework,
            Perimeter,
            RequirementAssessment,
            RequirementNode,
        )

        root = Folder.get_root_folder()
        framework = Framework.objects.create(name="Trail framework", folder=root)
        nodes = [
            RequirementNode.objects.create(
                framework=framework,
                folder=root,
                ref_id=ref_id,
                name=name,
                assessable=True,
            )
            for ref_id, name in (("R.1", "Backups"), ("R.2", "Logging"))
        ]
        perimeter = Perimeter.objects.create(name="Trail perimeter", folder=root)
        audit = ComplianceAssessment.objects.create(
            name="Trail audit", framework=framework, perimeter=perimeter, folder=root
        )
        for node in nodes:
            RequirementAssessment.objects.create(
                compliance_assessment=audit, requirement=node, folder=root
            )
        return audit

    @staticmethod
    def _trail(client, audit_id):
        response = client.get(
            reverse("object-audit-trail"),
            {"content_type": "complianceassessment", "object_id": str(audit_id)},
        )
        assert response.status_code == 200, response.content
        return response.data

    def test_trail_holds_requirement_assessment_changes(self, audit, admin_client):
        ra = audit.requirement_assessments.get(requirement__ref_id="R.1")
        ra.result = "compliant"
        ra.save()

        trail = self._trail(admin_client, audit.id)
        ra_entries = [e for e in trail if e["object"]["id"] == str(ra.id)]
        assert ra_entries
        assert all(
            e["object"]
            == {"model": "requirementassessment", "id": str(ra.id), "label": str(ra)}
            for e in ra_entries
        )
        assert "R.1" in ra_entries[0]["object"]["label"]
        assert any("result" in (e["changes"] or {}) for e in ra_entries)
        assert any(
            e["object"]
            == {
                "model": "complianceassessment",
                "id": str(audit.id),
                "label": str(audit),
            }
            for e in trail
        )

    def test_trail_leaves_out_other_audits(self, audit, admin_client):
        from core.models import ComplianceAssessment, RequirementAssessment

        other = ComplianceAssessment.objects.create(
            name="Other audit",
            framework=audit.framework,
            perimeter=audit.perimeter,
            folder=audit.folder,
        )
        other_ra = RequirementAssessment.objects.create(
            compliance_assessment=other,
            requirement=audit.framework.requirement_nodes.first(),
            folder=audit.folder,
        )
        ids = {e["object"]["id"] for e in self._trail(admin_client, audit.id)}
        assert str(other.id) not in ids
        assert str(other_ra.id) not in ids
