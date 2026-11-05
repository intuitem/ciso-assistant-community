from collections import defaultdict

import core.validators
import django.db.models.deletion
import iam.models
import uuid
from django.db import migrations, models


def backfill_containers(apps, schema_editor):
    """Group existing policy-anchored documents under one DocumentContainer per
    policy (locale variants share a policy), and give standalone documents their
    own container. Populates container.policies with the source policy.
    """
    ManagedDocument = apps.get_model("doc_management", "ManagedDocument")
    DocumentContainer = apps.get_model("doc_management", "DocumentContainer")
    AppliedControl = apps.get_model("core", "AppliedControl")
    db = schema_editor.connection.alias

    by_policy = defaultdict(list)
    orphans = []
    for doc in ManagedDocument.objects.using(db).filter(container__isnull=True):
        if doc.policy_id:
            by_policy[doc.policy_id].append(doc)
        else:
            orphans.append(doc)

    policy_names = dict(
        AppliedControl.objects.using(db)
        .filter(id__in=list(by_policy.keys()))
        .values_list("id", "name")
    )

    def default_of(docs):
        return next((d for d in docs if d.default_locale), docs[0])

    for policy_id, docs in by_policy.items():
        default = default_of(docs)
        container = DocumentContainer.objects.using(db).create(
            document_type=default.document_type,
            name=default.name or policy_names.get(policy_id, ""),
            folder_id=default.folder_id,
            is_published=default.is_published,
        )
        container.policies.add(policy_id)
        for d in docs:
            d.container = container
            d.folder_id = container.folder_id
            d.is_published = container.is_published
        ManagedDocument.objects.using(db).bulk_update(
            docs, ["container", "folder", "is_published"]
        )

    for doc in orphans:
        container = DocumentContainer.objects.using(db).create(
            document_type=doc.document_type,
            name=doc.name or "",
            folder_id=doc.folder_id,
            is_published=doc.is_published,
        )
        doc.container = container
        doc.save(update_fields=["container"])


class Migration(migrations.Migration):
    """Documents management expansion: DocumentContainer identity, typed object
    links, standalone/uploaded documents, templates, and computed references.

    The expand -> backfill -> contract order is load-bearing: the container FK is
    added while the legacy ``policy``/``document_type`` columns still exist, the
    backfill migrates their data into containers, then the columns are dropped.
    """

    dependencies = [
        ("core", "0172_view_compliance_assessment_full_permission"),
        ("doc_management", "0002_sync_is_published"),
        ("iam", "0023_alter_folder_content_type"),
        ("privacy", "0018_alter_datatransfer_transfer_mechanism"),
    ]

    operations = [
        # --- Expand -------------------------------------------------------
        # Transitional related_name avoids a reverse-accessor clash with
        # DocumentContainer.policies while both coexist during the backfill.
        migrations.AlterField(
            model_name="manageddocument",
            name="policy",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="core.policy",
            ),
        ),
        migrations.CreateModel(
            name="DocumentContainer",
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
                    "document_type",
                    models.CharField(
                        choices=[
                            ("policy", "Policy"),
                            ("procedure", "Procedure"),
                            ("charter", "Charter"),
                            ("record", "Record"),
                            ("meeting_minutes", "Meeting minutes"),
                            ("other", "Other"),
                        ],
                        default="policy",
                        max_length=20,
                        verbose_name="Document type",
                    ),
                ),
                (
                    "name",
                    models.CharField(blank=True, max_length=200, verbose_name="Name"),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                (
                    "applied_controls",
                    models.ManyToManyField(
                        blank=True,
                        related_name="control_documents",
                        to="core.appliedcontrol",
                    ),
                ),
                (
                    "filtering_labels",
                    models.ManyToManyField(
                        blank=True, to="core.filteringlabel", verbose_name="Labels"
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
                    "policies",
                    models.ManyToManyField(
                        blank=True, related_name="documents", to="core.policy"
                    ),
                ),
                (
                    "processings",
                    models.ManyToManyField(
                        blank=True, related_name="documents", to="privacy.processing"
                    ),
                ),
                (
                    "task_templates",
                    models.ManyToManyField(
                        blank=True, related_name="documents", to="core.tasktemplate"
                    ),
                ),
            ],
            options={
                "verbose_name": "Document container",
                "verbose_name_plural": "Document containers",
            },
        ),
        migrations.AddField(
            model_name="manageddocument",
            name="container",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="documents",
                to="doc_management.documentcontainer",
            ),
        ),
        # --- Backfill (data) ---------------------------------------------
        migrations.RunPython(backfill_containers, migrations.RunPython.noop),
        # --- Contract -----------------------------------------------------
        migrations.RemoveField(model_name="manageddocument", name="document_type"),
        migrations.RemoveField(model_name="manageddocument", name="policy"),
        # --- Remaining additive schema -----------------------------------
        migrations.AddField(
            model_name="documentrevision",
            name="file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="",
                validators=[
                    core.validators.validate_file_size,
                    core.validators.validate_file_name,
                ],
            ),
        ),
        migrations.AddField(
            model_name="documentrevision",
            name="source",
            field=models.CharField(
                choices=[("authored", "Authored"), ("uploaded", "Uploaded")],
                default="authored",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="DocumentTemplate",
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
                    "locale",
                    models.CharField(
                        default="en", max_length=100, verbose_name="Locale"
                    ),
                ),
                (
                    "default_locale",
                    models.BooleanField(default=True, verbose_name="Default locale"),
                ),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("policy", "Policy"),
                            ("procedure", "Procedure"),
                            ("charter", "Charter"),
                            ("record", "Record"),
                            ("meeting_minutes", "Meeting minutes"),
                            ("other", "Other"),
                        ],
                        default="policy",
                        max_length=20,
                        verbose_name="Document type",
                    ),
                ),
                ("ref_id", models.CharField(max_length=100, verbose_name="Reference")),
                ("name", models.CharField(max_length=200, verbose_name="Name")),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                ("content", models.TextField(blank=True)),
                ("builtin", models.BooleanField(default=False)),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
            ],
            options={
                "verbose_name": "Document template",
                "verbose_name_plural": "Document templates",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("ref_id", "locale"), name="unique_template_ref_locale"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="DocumentReference",
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
                    "source_container",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outgoing_references",
                        to="doc_management.documentcontainer",
                    ),
                ),
                (
                    "target_container",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incoming_references",
                        to="doc_management.documentcontainer",
                    ),
                ),
            ],
            options={
                "verbose_name": "Document reference",
                "verbose_name_plural": "Document references",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source_container", "target_container"),
                        name="unique_document_reference",
                    )
                ],
            },
        ),
    ]
