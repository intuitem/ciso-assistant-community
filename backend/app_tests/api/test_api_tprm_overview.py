"""The third-party overview cards carry their vendor's criticality."""

import pytest

from iam.models import Folder
from tprm.models import Entity, EntityAssessment, Tier
from tprm.tiers import set_entity_tier

URL = "/api/entity-assessments/metrics/"


@pytest.mark.django_db
def test_cards_carry_the_vendors_tier(authenticated_client):
    Tier.objects.all().delete()
    Tier.create_default_tiers()
    domain = Folder.objects.create(
        name="overview-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    tiered = Entity.objects.create(name="Tiered", folder=domain)
    untiered = Entity.objects.create(name="Untiered", folder=domain)
    set_entity_tier(tiered, Tier.objects.get(key="critical"))
    for entity in (tiered, untiered):
        EntityAssessment.objects.create(name=entity.name, folder=domain, entity=entity)

    rows = {r["provider"]: r for r in authenticated_client.get(URL).json()}
    assert rows["Tiered"]["entity_id"] == str(tiered.id)
    assert rows["Tiered"]["tier"]["name"] == "critical"
    assert rows["Tiered"]["tier"]["hexcolor"]
    assert rows["Untiered"]["tier"] is None
