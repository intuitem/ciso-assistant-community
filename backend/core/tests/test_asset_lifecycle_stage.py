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
