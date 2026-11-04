import pytest

from core.models import Terminology
from core.serializers import AssetWriteSerializer


def _errors(terminology):
    serializer = AssetWriteSerializer(
        data={"lifecycle_stage": str(terminology.id)}, partial=True
    )
    serializer.is_valid()
    return serializer.errors


@pytest.mark.django_db
def test_lifecycle_stage_accepts_only_visible_asset_lifecycle_terms():
    Terminology.create_default_asset_lifecycle_stages()
    active = Terminology.objects.get(
        field_path=Terminology.FieldPath.ASSET_LIFECYCLE_STAGE, name="active"
    )
    assert "lifecycle_stage" not in _errors(active)

    other, _ = Terminology.objects.get_or_create(
        name="draft", field_path=Terminology.FieldPath.PROJECT_STATUS
    )
    assert "lifecycle_stage" in _errors(other)

    active.is_visible = False
    active.save()
    assert "lifecycle_stage" in _errors(active)


@pytest.mark.django_db
def test_hidden_stage_survives_on_assets_that_already_carry_it():
    from core.models import Asset
    from iam.models import Folder

    Terminology.create_default_asset_lifecycle_stages()
    active = Terminology.objects.get(
        field_path=Terminology.FieldPath.ASSET_LIFECYCLE_STAGE, name="active"
    )
    asset = Asset.objects.create(
        name="crm", folder=Folder.get_root_folder(), lifecycle_stage=active
    )
    active.is_visible = False
    active.save()

    asset.description = "edited after the stage was hidden"
    asset.save()  # Asset.save runs full_clean

    kept = AssetWriteSerializer(
        asset, data={"lifecycle_stage": str(active.id)}, partial=True
    )
    assert kept.is_valid(), kept.errors

    other = Asset.objects.create(name="erp", folder=Folder.get_root_folder())
    moved = AssetWriteSerializer(
        other, data={"lifecycle_stage": str(active.id)}, partial=True
    )
    assert not moved.is_valid()
    assert "lifecycle_stage" in moved.errors


@pytest.mark.django_db
def test_custom_stage_in_use_cannot_move_to_another_field_path():
    from core.models import Asset
    from core.serializers import TerminologyWriteSerializer
    from iam.models import Folder

    stage = Terminology.objects.create(
        name="frozen", field_path=Terminology.FieldPath.ASSET_LIFECYCLE_STAGE
    )
    moving = {"field_path": Terminology.FieldPath.PROJECT_STATUS}

    unused = TerminologyWriteSerializer(stage, data=moving, partial=True)
    assert unused.is_valid(), unused.errors

    Asset.objects.create(
        name="mainframe", folder=Folder.get_root_folder(), lifecycle_stage=stage
    )
    used = TerminologyWriteSerializer(stage, data=moving, partial=True)
    assert not used.is_valid()
    assert "field_path" in used.errors
