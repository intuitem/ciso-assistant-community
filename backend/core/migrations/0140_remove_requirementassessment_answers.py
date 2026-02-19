"""Remove the old RequirementAssessment.answers JSON field.

The answers data has been migrated to the Answer model in migration 0139.
RequirementNode.questions is kept for now as the library importer still
writes to it (alongside the new Question/QuestionChoice models).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0139_migrate_questions_answers_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="requirementassessment",
            name="answers",
        ),
    ]
