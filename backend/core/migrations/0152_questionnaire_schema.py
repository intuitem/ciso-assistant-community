"""Schema migration: questionnaire models and framework editing.

Combines schema operations from the iterative questionnaire branch:
- Rename JSON fields (questions → questions_json, answers → answers_json)
- Question, QuestionChoice, Answer models
- RequirementNode display_mode
- RequirementNodeAttachment model (with nullable requirement_node + framework FK)
- Framework editing_draft/editing_version/editing_history
- Field visibility on ComplianceAssessment and Framework
- RequirementNode verbose_name options
"""

import core.validators
import django.db.models.deletion
import iam.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0151_complianceassessment_scoring_enabled_and_more"),
        ("iam", "0021_fix_auditee_iam_groups"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- rename old JSON fields ---
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
        # --- outcomes ---
        migrations.AddField(
            model_name="complianceassessment",
            name="computed_outcome",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="framework",
            name="outcomes_definition",
            field=models.JSONField(
                blank=True, default=list, verbose_name="Outcomes definition"
            ),
        ),
        # --- Question model ---
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
                    "text",
                    models.TextField(blank=True, null=True, verbose_name="Text"),
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
                            ("unique_choice", "Unique choice"),
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
        # --- QuestionChoice model ---
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
                    "urn",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="URN",
                    ),
                ),
                (
                    "value",
                    models.TextField(blank=True, null=True, verbose_name="Value"),
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
                "unique_together": {("question", "urn")},
            },
        ),
        # --- Answer model ---
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
        # --- display_mode ---
        migrations.AddField(
            model_name="requirementnode",
            name="display_mode",
            field=models.CharField(
                choices=[("default", "Default"), ("splash", "Splash screen")],
                default="default",
                max_length=20,
                verbose_name="Display mode",
            ),
        ),
        # --- RequirementNodeAttachment (with nullable requirement_node + framework FK) ---
        migrations.CreateModel(
            name="RequirementNodeAttachment",
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
                    "file",
                    models.FileField(
                        upload_to="",
                        validators=[
                            core.validators.validate_file_size,
                            core.validators.validate_file_name,
                        ],
                        verbose_name="File",
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
                    "framework",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="image_attachments",
                        to="core.framework",
                        verbose_name="Framework",
                    ),
                ),
                (
                    "requirement_node",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="core.requirementnode",
                        verbose_name="Requirement node",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="requirement_node_attachments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Uploaded by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Requirement node attachment",
                "verbose_name_plural": "Requirement node attachments",
            },
        ),
        # --- framework editing ---
        migrations.AddField(
            model_name="framework",
            name="editing_draft",
            field=models.JSONField(
                blank=True,
                default=None,
                help_text="Work-in-progress definition. Null when no active draft.",
                null=True,
                verbose_name="Editing draft",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="editing_version",
            field=models.IntegerField(
                default=1,
                help_text="Incremented on each publish.",
                verbose_name="Editing version",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="editing_history",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Snapshots of previous published definitions.",
                verbose_name="Editing history",
            ),
        ),
        # --- field visibility ---
        migrations.AddField(
            model_name="complianceassessment",
            name="field_visibility",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Override visibility per field for this assessment. Overrides framework defaults.",
                verbose_name="Field visibility",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="field_visibility",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Override visibility per field. Keys: field names. Values: 'everyone', 'auditor', or 'hidden'.",
                verbose_name="Field visibility",
            ),
        ),
        # --- RequirementNode options ---
        migrations.AlterModelOptions(
            name="requirementnode",
            options={
                "verbose_name": "RequirementNode",
                "verbose_name_plural": "RequirementNodes",
            },
        ),
    ]
