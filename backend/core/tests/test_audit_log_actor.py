"""Regression tests for the audit-log actor/folder data contract.

LogEntry rows are produced in the community backend: auditlog.register(...) in
core.models, the AuditlogMiddleware (actor/actor_email native columns), and
AbstractBaseModel.get_additional_data() (folder_id). The enterprise audit-log
serializer only exposes them.

The audit-trail refactor (#4312/#4333) moved actor capture from an
additional_data["user_email"] blob to the native actor/actor_email columns, and
folder from additional_data["folder"] (a path string) to
additional_data["folder_id"]. These tests pin that contract so a producer-side
change can't silently blank the actor again.
"""

import pytest
from auditlog.context import set_actor
from auditlog.models import LogEntry

from core.models import Asset
from iam.models import Folder, User


@pytest.mark.django_db
class TestAuditLogActorContract:
    def _domain_folder(self):
        root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        return Folder.objects.create(
            name="Domain A",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root,
            create_iam_groups=False,
        )

    def test_create_populates_native_actor_and_folder_id(self):
        user = User.objects.create_user(email="auditor@test.com")
        folder = self._domain_folder()

        with set_actor(actor=user):
            asset = Asset.objects.create(name="A-audited", folder=folder)

        entry = LogEntry.objects.get(
            object_pk=str(asset.pk), action=LogEntry.Action.CREATE
        )

        # Actor lands in the native columns the serializer reads.
        assert entry.actor_id == user.pk
        assert entry.actor_email == user.email

        # Folder is captured as folder_id; the old enrichment keys are gone.
        assert entry.additional_data.get("folder_id") == str(folder.id)
        assert "user_email" not in entry.additional_data
        assert "folder" not in entry.additional_data

    def test_create_without_actor_leaves_actor_empty_but_keeps_folder(self):
        folder = self._domain_folder()
        asset = Asset.objects.create(name="A-no-actor", folder=folder)

        entry = LogEntry.objects.get(
            object_pk=str(asset.pk), action=LogEntry.Action.CREATE
        )

        assert entry.actor_id is None
        assert entry.actor_email is None
        assert entry.additional_data.get("folder_id") == str(folder.id)
