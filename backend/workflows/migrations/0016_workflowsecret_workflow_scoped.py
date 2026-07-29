"""Workflow-scoped secrets (Round 2, supersedes folder subtree resolution).

A WorkflowSecret now belongs to one Workflow and is only resolvable by that
workflow's instances. No data migration: existing secrets have no workflow link
to backfill, so they are wiped (feature unreleased). Wiping first lets the
non-null `workflow` FK add cleanly on the empty table.
"""

import django.db.models.deletion
from django.db import migrations, models


def wipe_secrets(apps, schema_editor):
    apps.get_model("workflows", "WorkflowSecret").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("workflows", "0015_remove_workflownode_join_type_and_more"),
    ]

    operations = [
        migrations.RunPython(wipe_secrets, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="workflowsecret",
            name="unique_workflow_secret_name",
        ),
        migrations.AddField(
            model_name="workflowsecret",
            name="workflow",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="secrets",
                to="workflows.workflow",
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="workflowsecret",
            constraint=models.UniqueConstraint(
                fields=["workflow", "name"],
                name="unique_workflow_secret_name",
            ),
        ),
    ]
