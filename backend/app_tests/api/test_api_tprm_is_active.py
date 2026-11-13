import pytest
from rest_framework import status

from iam.models import Folder
from tprm.models import Entity, Solution


@pytest.fixture
def entity(authenticated_client):
    folder = Folder.objects.create(
        name="active-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    return Entity.objects.create(name="Acme", folder=folder)


@pytest.mark.django_db
@pytest.mark.parametrize("model", ["entities", "solutions"])
def test_batch_deactivate_then_filter_and_export(authenticated_client, entity, model):
    if model == "entities":
        kept = Entity.objects.create(name="Kept", folder=entity.folder)
        dropped = Entity.objects.create(name="Dropped", folder=entity.folder)
    else:
        kept = Solution.objects.create(name="Kept", provider_entity=entity)
        dropped = Solution.objects.create(name="Dropped", provider_entity=entity)
    url = f"/api/{model}/"

    choices = authenticated_client.get(f"{url}is_active/")
    assert set(choices.json()) == {"true", "false"}

    response = authenticated_client.post(
        f"{url}batch-action/",
        {
            "action": "change_field",
            "ids": [str(dropped.id)],
            "field": "is_active",
            "value": "false",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.json()
    dropped.refresh_from_db()
    assert dropped.is_active is False

    names = {
        r["name"]
        for r in authenticated_client.get(url, {"is_active": "true"}).json()["results"]
    }
    assert "Kept" in names and "Dropped" not in names

    export = authenticated_client.get(f"{url}export_csv/", {"is_active": "false"})
    assert export.status_code == status.HTTP_200_OK
    body = (
        b"".join(export.streaming_content).decode()
        if export.streaming
        else export.content.decode()
    )
    assert "is_active" in body.splitlines()[0]
    assert "Dropped" in body and "Kept" not in body
