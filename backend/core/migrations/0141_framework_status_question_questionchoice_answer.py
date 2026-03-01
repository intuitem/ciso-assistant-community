"""Schema migration: questionnaire models.

- Rename old JSON fields (questions → questions_json, answers → answers_json)
- Add Framework.status field
- Create Question, QuestionChoice, Answer models
- Answer includes selected_choices M2M to QuestionChoice
- QuestionChoice has unique_together on (question, ref_id)
"""

import django.db.models.deletion
import iam.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0140_populate_tasknode_scheduled_date"),
        ("iam", "0019_add_view_globalsettings_in_custom_roles"),
    ]

    operations = [
        # Rename old JSON fields before creating models whose FKs use the same related_names
        migrations.RenameField(
            model_name="requirementnode",
            old_name="questions",
            new_name="questions_json",
        ),
        migrations.RenameField(
            model_name="requirementassessment",
            old_name="answers",
            new_name="answers_json",
        ),
        migrations.AddField(
            model_name="framework",
            name="status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("published", "Published")],
                default="draft",
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                (
                    "urn",
                    models.CharField(max_length=255, unique=True, verbose_name="URN"),
                ),
                (
                    "ref_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Reference ID",
                    ),
                ),
                (
                    "annotation",
                    models.TextField(blank=True, null=True, verbose_name="Annotation"),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("text", "Text"),
                            ("number", "Number"),
                            ("boolean", "Boolean"),
                            ("single_choice", "Single choice"),
                            ("multiple_choice", "Multiple choice"),
                            ("date", "Date"),
                        ],
                        default="text",
                        max_length=20,
                        verbose_name="Type",
                    ),
                ),
                (
                    "config",
                    models.JSONField(blank=True, null=True, verbose_name="Config"),
                ),
                (
                    "depends_on",
                    models.JSONField(blank=True, null=True, verbose_name="Depends on"),
                ),
                ("order", models.IntegerField(default=0, verbose_name="Order")),
                ("weight", models.IntegerField(default=1, verbose_name="Weight")),
                (
                    "translations",
                    models.JSONField(
                        blank=True, null=True, verbose_name="Translations"
                    ),
                ),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
                (
                    "requirement_node",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="core.requirementnode",
                        verbose_name="Requirement node",
                    ),
                ),
            ],
            options={
                "verbose_name": "Question",
                "verbose_name_plural": "Questions",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="QuestionChoice",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                (
                    "ref_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Reference ID",
                    ),
                ),
                (
                    "annotation",
                    models.TextField(blank=True, null=True, verbose_name="Annotation"),
                ),
                (
                    "add_score",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="Add score"
                    ),
                ),
                (
                    "compute_result",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Compute result",
                    ),
                ),
                ("order", models.IntegerField(default=0, verbose_name="Order")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "color",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="Color"
                    ),
                ),
                (
                    "select_implementation_groups",
                    models.JSONField(
                        blank=True,
                        null=True,
                        verbose_name="Select implementation groups",
                    ),
                ),
                (
                    "translations",
                    models.JSONField(
                        blank=True, null=True, verbose_name="Translations"
                    ),
                ),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="core.question",
                        verbose_name="Question",
                    ),
                ),
            ],
            options={
                "verbose_name": "Question choice",
                "verbose_name_plural": "Question choices",
                "ordering": ["order"],
                "unique_together": {("question", "ref_id")},
            },
        ),
        migrations.CreateModel(
            name="Answer",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                (
                    "value",
                    models.JSONField(blank=True, null=True, verbose_name="Value"),
                ),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
                (
                    "requirement_assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="core.requirementassessment",
                        verbose_name="Requirement assessment",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="given_answers",
                        to="core.question",
                        verbose_name="Question",
                    ),
                ),
                (
                    "selected_choices",
                    models.ManyToManyField(
                        blank=True,
                        related_name="choice_answers",
                        to="core.questionchoice",
                        verbose_name="Selected choices",
                    ),
                ),
            ],
            options={
                "verbose_name": "Answer",
                "verbose_name_plural": "Answers",
                "unique_together": {("requirement_assessment", "question")},
            },
        ),
    ]
