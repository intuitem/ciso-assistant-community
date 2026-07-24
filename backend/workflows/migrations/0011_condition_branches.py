"""Branches as first-class node data (spec D25).

Conditions move from edges to a new node-owned ConditionBranch. No data
migration by decision: all workflows are wiped and reseeded (feature
unreleased). Wiping first lets the ConditionGroup.edge → branch swap and the
non-null-on-empty-table changes apply cleanly.
"""

import uuid

import django.db.models.deletion
import iam.models
from django.db import migrations, models


def wipe_workflows(apps, schema_editor):
    # Clear the two PROTECT references that would block a plain cascade delete:
    # WorkflowNode.subprocess_workflow (→ Workflow) and Condition.variable
    # (→ WorkflowVariable). Then everything else cascades from Workflow.
    apps.get_model("workflows", "WorkflowNode").objects.update(
        subprocess_workflow=None
    )
    apps.get_model("workflows", "Condition").objects.all().delete()
    apps.get_model("workflows", "ConditionGroup").objects.all().delete()
    apps.get_model("workflows", "Workflow").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0001_initial"),
        ("workflows", "0010_remove_workflowinstance_event_trigger_and_more"),
    ]

    operations = [
        migrations.RunPython(wipe_workflows, migrations.RunPython.noop),
        migrations.CreateModel(
            name="ConditionBranch",
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
                ("name", models.CharField(blank=True, max_length=200)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_default", models.BooleanField(default=False)),
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
                    "node",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branches",
                        to="workflows.workflownode",
                    ),
                ),
            ],
            options={"ordering": ["order", "created_at"]},
        ),
        migrations.AddField(
            model_name="workflowedge",
            name="source_branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="edges",
                to="workflows.conditionbranch",
            ),
        ),
        migrations.RemoveField(model_name="conditiongroup", name="edge"),
        migrations.AddField(
            model_name="conditiongroup",
            name="branch",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="condition_groups",
                to="workflows.conditionbranch",
            ),
            preserve_default=False,
        ),
    ]
