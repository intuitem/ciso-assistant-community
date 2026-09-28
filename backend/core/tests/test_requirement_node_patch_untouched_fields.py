"""Regression for #4715: PATCH must not validate fields the request never sent."""

import pytest

from core.models import Framework, RequirementNode
from core.serializers import RequirementNodeWriteSerializer
from iam.models import Folder


@pytest.mark.django_db
def test_patch_survives_when_untouched_nullable_fields_are_blank():
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(name="FW", folder=folder, min_score=0, max_score=100)
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:patch:req:001",
        ref_id="REQ-1",
        assessable=True,
        folder=folder,
    )
    assert rn.name is None
    assert rn.order_id is None
    assert rn.implementation_groups is None

    RequirementNodeWriteSerializer().update(rn, {"ref_id": "REQ-1-renamed"})

    rn.refresh_from_db()
    assert rn.ref_id == "REQ-1-renamed"
    assert rn.name is None
    assert rn.order_id is None
    assert rn.implementation_groups is None


@pytest.mark.django_db
def test_patch_still_validates_the_field_it_touches():
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(name="FW", folder=folder, min_score=0, max_score=100)
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:patch:req:002",
        ref_id="REQ-2",
        assessable=True,
        folder=folder,
        min_score=0,
        max_score=10,
    )

    with pytest.raises(Exception):
        RequirementNodeWriteSerializer().update(
            rn, {"scores_definition_ref": "does-not-exist"}
        )


@pytest.mark.django_db
def test_patch_accepts_explicit_null_on_nullable_fields():
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(name="FW", folder=folder, min_score=0, max_score=100)
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:patch:req:003",
        ref_id="REQ-3",
        assessable=True,
        folder=folder,
    )

    RequirementNodeWriteSerializer().update(
        rn,
        {
            "ref_id": "REQ-3-renamed",
            "name": None,
            "order_id": None,
            "implementation_groups": None,
        },
    )

    rn.refresh_from_db()
    assert rn.ref_id == "REQ-3-renamed"
    assert rn.implementation_groups is None
