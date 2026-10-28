"""Assets, applied controls and vulnerabilities list the threat models that use
them: those with a graph node carrying the object."""

import pytest
from rest_framework import status

from core.models import AppliedControl, Asset, Vulnerability
from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
from iam.models import Folder
from sec_intel.models import TTPCatalog
from threat_modeling.models import ThreatModel, ThreatModelNode


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model, field",
    [
        (Asset, "assets"),
        (AppliedControl, "applied_controls"),
        (Vulnerability, "vulnerabilities"),
    ],
)
def test_threat_models_using_an_object(authenticated_client, model, field):
    row = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
    flags = FeatureFlagsSerializer(row, data={"threat_modeling": True}, partial=True)
    flags.is_valid(raise_exception=True)
    flags.save()
    root = Folder.get_root_folder()
    obj = model.objects.create(name="Linked", folder=root)
    catalog = TTPCatalog.objects.create(name="Test catalog", folder=root)
    using = ThreatModel.objects.create(name="Uses it", folder=root, catalog=catalog)
    ThreatModel.objects.create(name="Does not", folder=root, catalog=catalog)
    # Two of its nodes carry the object: the model is listed once.
    for label in ("Initial access", "Exploitation"):
        node = ThreatModelNode.objects.create(
            threat_model=using, folder=root, kind="custom", label=label
        )
        getattr(node, field).add(obj)

    resp = authenticated_client.get(f"/api/threat-models/?{field}={obj.id}")

    assert resp.status_code == status.HTTP_200_OK, resp.json()
    assert [row["name"] for row in resp.json()["results"]] == ["Uses it"]
