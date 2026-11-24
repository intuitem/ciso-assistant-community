"""Saving a threat model graph follows the generic many-to-many rule for the
objects its nodes carry: view on each new link, nothing on a kept or dropped one."""

import uuid

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Asset
from core.utils import RoleCodename
from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
from iam.models import Folder, Role, RoleAssignment, User
from sec_intel.models import TTPCatalog
from threat_modeling.models import ThreatModel, ThreatModelNode


def _domain(label):
    return Folder.objects.create(
        name=f"tm-{label}-{uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.mark.django_db
class TestGraphSaveLinks:
    def setup_method(self):
        row = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
        flags = FeatureFlagsSerializer(
            row, data={"threat_modeling": True}, partial=True
        )
        flags.is_valid(raise_exception=True)
        flags.save()
        self.mine, hidden = _domain("mine"), _domain("hidden")
        catalog = TTPCatalog.objects.create(
            name="Test catalog", folder=Folder.get_root_folder()
        )
        self.threat_model = ThreatModel.objects.create(
            name="Model", folder=self.mine, catalog=catalog
        )
        self.node = ThreatModelNode.objects.create(
            threat_model=self.threat_model,
            folder=self.mine,
            kind="custom",
            label="Step",
        )
        self.hidden_asset = Asset.objects.create(name="Hidden", folder=hidden)
        user = User.objects.create_user(f"tm-{uuid.uuid4().hex[:6]}@test.com")
        RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=RoleCodename.ANALYST.value),
            folder=Folder.get_root_folder(),
            is_recursive=True,
        ).perimeter_folders.add(self.mine)
        self.client = APIClient()
        _, token = AuthToken.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    def _save(self, assets):
        node = {
            "id": str(self.node.id),
            "kind": "custom",
            "label": "Step",
            "position_x": 0,
            "position_y": 0,
            "assets": [str(a.id) for a in assets],
        }
        return self.client.post(
            f"/api/threat-models/{self.threat_model.id}/save-graph/",
            {"nodes": [node], "edges": []},
            format="json",
        )

    def test_kept_hidden_link_saves(self):
        self.node.assets.add(self.hidden_asset)
        r = self._save([self.hidden_asset])
        assert r.status_code == status.HTTP_200_OK, r.content
        assert list(self.node.assets.all()) == [self.hidden_asset]

    def test_new_hidden_link_is_refused(self):
        r = self._save([self.hidden_asset])
        assert r.status_code == status.HTTP_400_BAD_REQUEST, r.content
        assert "is not accessible" in str(r.json()["errors"])
        assert not self.node.assets.exists()

    def test_hidden_link_can_be_dropped(self):
        self.node.assets.add(self.hidden_asset)
        r = self._save([])
        assert r.status_code == status.HTTP_200_OK, r.content
        assert not self.node.assets.exists()
