from typing import Final, Optional

from django.db import migrations

OUTDATED_FIELD: Final[str] = "source_requirement_assessment"
NEW_FIELD: Final[str] = "source_requirement_assessments"
BATCH_SIZE: Final[int] = 100


def fix_outdated_mapping_inferences(apps, schema_editor):
    """
    Update all `RequirementAssessment` objects with an outdated `mapping_inference` structure to the the new structure.

    **WARNING:** This function doesn't fix the missing `"source_framework"` and `"used_mapping_set"` mapping_inference fields.
    """

    RequirementAssessment = apps.get_model("core", "RequirementAssessment")

    requirement_assessments_to_update = []

    requirement_assessments = list(RequirementAssessment.objects.all())

    # The `requirement_assessment_urn` value may be `None` because we made `RequirementNode.urn` nullable (for whatever reason).
    requirement_assessment_id_to_urn: dict[str, Optional[str]] = {
        str(requirement_assessment_id): requirement_assessment_urn
        for requirement_assessment_id, requirement_assessment_urn in RequirementAssessment.objects.values_list(
            "id", "requirement__urn"
        )
    }

    # I am using `.value_list(...)` and the `.all()` iterator to avoid abusive RAM usage (by preventing loading all `RequirementAssessment` in memory at once (at the same time)).

    for requirement_assessment in RequirementAssessment.objects.all():
        mapping_inference = requirement_assessment.mapping_inference
        old_field_value = mapping_inference.pop(OUTDATED_FIELD, None)

        is_mapping_inference_outdated = old_field_value is not None

        if is_mapping_inference_outdated:
            new_field_value = {}

            if not isinstance(old_field_value, dict):
                # Handle non-dict `old_field_value` just in case (makes the code more defensive, this JSONField could contain anything as there's no django validator/db constraint for it.)
                old_field_value = {}

            source_requirement_id = old_field_value.get("id")
            source_requirement_urn = requirement_assessment_id_to_urn.get(
                source_requirement_id
            )

            if source_requirement_urn is not None:
                # This check makes the code more defensive again for the same reason as the one mentionned herebefore.
                # This will erase the source_requirement_assessment if he's not in the codebase anymore, i guess that's fine.

                old_field_value["urn"] = source_requirement_urn
                new_field_value = {source_requirement_urn: old_field_value}

            mapping_inference[NEW_FIELD] = new_field_value
            requirement_assessment.mapping_inference = mapping_inference

            requirement_assessments_to_update.append(requirement_assessment)

            if len(requirement_assessments_to_update) >= BATCH_SIZE:
                RequirementAssessment.objects.bulk_update(
                    requirement_assessments_to_update,
                    ["mapping_inference"],
                    batch_size=BATCH_SIZE,
                )
                requirement_assessments_to_update.clear()

    if len(requirement_assessments_to_update) > 0:
        RequirementAssessment.objects.bulk_update(
            requirement_assessments_to_update, ["mapping_inference"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0171_requirementnode_score_and_target_score"),
    ]

    operations = [
        migrations.RunPython(fix_outdated_mapping_inferences),
    ]
