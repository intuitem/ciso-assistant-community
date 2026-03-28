"""Remove old JSON fields after data migration.

RequirementNode.questions_json and RequirementAssessment.answers_json
have been migrated to the Question/QuestionChoice/Answer models.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0153_questionnaire_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="requirementnode",
            name="questions_json",
        ),
        migrations.RemoveField(
            model_name="requirementassessment",
            name="answers_json",
        ),
    ]
