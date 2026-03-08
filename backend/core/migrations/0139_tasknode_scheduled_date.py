from django.db import migrations, models
from django.db.models import Count, Min


STATUS_PRIORITY = {"pending": 0, "in_progress": 1, "completed": 2, "cancelled": 3}


def merge_duplicate_task_nodes(apps, schema_editor):
    """
    Merge duplicate (task_template, due_date) TaskNode rows before the
    UniqueConstraint is applied. For each group of duplicates, keep the
    oldest row and merge evidences, evidence revisions, observation, and
    status from the others into it.
    """
    TaskNode = apps.get_model("core", "TaskNode")
    EvidenceRevision = apps.get_model("core", "EvidenceRevision")
    db_alias = schema_editor.connection.alias

    duplicates = (
        TaskNode.objects.using(db_alias)
        .filter(due_date__isnull=False)
        .values("task_template", "due_date")
        .annotate(min_id=Min("id"), cnt=Count("id"))
        .filter(cnt__gt=1)
    )

    for dup in duplicates:
        nodes = list(
            TaskNode.objects.using(db_alias)
            .filter(
                task_template=dup["task_template"],
                due_date=dup["due_date"],
            )
            .order_by("created_at")
        )
        keeper = nodes[0]
        extras = nodes[1:]

        for extra in extras:
            # Merge evidences (M2M)
            for evidence in extra.evidences.all():
                keeper.evidences.add(evidence)

            # Reassign evidence revisions (reverse FK)
            EvidenceRevision.objects.using(db_alias).filter(task_node=extra).update(
                task_node=keeper
            )

            # Merge observation (keep non-empty, concatenate if both have content)
            if extra.observation:
                if keeper.observation:
                    keeper.observation += "\n" + extra.observation
                else:
                    keeper.observation = extra.observation

            # Keep the most advanced status
            if STATUS_PRIORITY.get(extra.status, 0) > STATUS_PRIORITY.get(
                keeper.status, 0
            ):
                keeper.status = extra.status

            extra.delete()

        keeper.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0138_validationflow_accreditations_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tasknode",
            name="scheduled_date",
            field=models.DateField(
                blank=True,
                help_text="Original date from the recurrence rule. Not user-editable.",
                null=True,
                verbose_name="Scheduled date",
            ),
        ),
        migrations.RunPython(merge_duplicate_task_nodes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="tasknode",
            constraint=models.UniqueConstraint(
                fields=("task_template", "due_date"),
                condition=models.Q(due_date__isnull=False),
                name="unique_tasknode_template_due_date",
            ),
        ),
    ]
