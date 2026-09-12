"""A score is only ever as visible as the entity it is about: the folder is copied
from the entity at score save time, so moving the entity must carry the scores
along — otherwise they stay scoped (and editable) in the old domain."""

import pytest
from rest_framework.test import APIClient

from core.models import Terminology
from iam.models import Folder, User
from tprm.models import Entity, EntityScore


@pytest.fixture
def setup(db):
    domain_a = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="Score Domain A",
        content_type=Folder.ContentType.DOMAIN,
    )
    domain_b = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="Score Domain B",
        content_type=Folder.ContentType.DOMAIN,
    )
    entity = Entity.objects.create(name="Rated Vendor", folder=domain_a)
    provider = Terminology.objects.create(
        name="Test Ratings Inc",
        field_path="entity_score.provider",
        is_visible=True,
    )
    score = EntityScore.objects.create(
        entity=entity,
        provider=provider,
        score=87.5,
        scale_max=100,
        as_of="2026-09-01",
    )
    admin = APIClient()
    admin.force_authenticate(User.objects.create_superuser("scores-admin@tests.com"))
    return {
        "domain_a": domain_a,
        "domain_b": domain_b,
        "entity": entity,
        "score": score,
        "admin": admin,
    }


def test_score_folder_follows_the_entity(setup):
    score = setup["score"]
    assert score.folder == setup["domain_a"]

    response = setup["admin"].patch(
        f"/api/entities/{setup['entity'].id}/",
        {"folder": str(setup["domain_b"].id)},
        format="json",
    )
    assert response.status_code == 200, response.data

    score.refresh_from_db()
    assert score.folder == setup["domain_b"]


def test_update_without_a_move_leaves_scores_alone(setup):
    response = setup["admin"].patch(
        f"/api/entities/{setup['entity'].id}/",
        {"description": "renamed, not moved"},
        format="json",
    )
    assert response.status_code == 200, response.data

    setup["score"].refresh_from_db()
    assert setup["score"].folder == setup["domain_a"]
