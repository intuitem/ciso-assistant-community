from datetime import timedelta
from django.db import migrations, models
from core.utils import _generate_occurrences

def populate_scheduled_date(apps, schema_editor):
    TaskNode = apps.get_model("core", "TaskNode")
    TaskTemplate = apps.get_model("core", "TaskTemplate")

    db_alias = schema_editor.connection.alias

    for template in TaskTemplate.objects.using(db_alias).filter(is_recurrent=True):

        # Get nodes without scheduled_date
        qs = (
            TaskNode.objects.using(db_alias)
            .filter(task_template=template, scheduled_date__isnull=True)
            .exclude(due_date__isnull=True)
            .order_by("due_date")
        )

        nodes = list(qs)
        if not nodes:
            continue

        min_due = nodes[0].due_date
        max_due = nodes[-1].due_date

        # Generate occurrences only around real data
        start_date = min_due - timedelta(days=400)
        end_date = max_due + timedelta(days=400)

        occurrences = _generate_occurrences(template, start_date, end_date)
        generated_dates = sorted(o["due_date"] for o in occurrences)

        # assign exact matches

        i = 0  # node pointer
        j = 0  # generated pointer

        remaining_nodes = []
        remaining_generated = []

        while i < len(nodes) and j < len(generated_dates):
            node_date = nodes[i].due_date
            gen_date = generated_dates[j]

            if node_date == gen_date:
                # Not modified by user
                nodes[i].scheduled_date = gen_date
                i += 1
                j += 1
            elif node_date < gen_date:
                remaining_nodes.append(nodes[i])
                i += 1
            else:
                remaining_generated.append(gen_date)
                j += 1

        # Add remaining items
        while i < len(nodes):
            remaining_nodes.append(nodes[i])
            i += 1

        while j < len(generated_dates):
            remaining_generated.append(generated_dates[j])
            j += 1

        # match remaining by closest date

        g_index = 0

        for node in remaining_nodes:
            best_date = None
            best_distance = None

            while g_index < len(remaining_generated):
                gen_date = remaining_generated[g_index]
                distance = abs((gen_date - node.due_date).days)

                if best_distance is None or distance <= best_distance:
                    best_distance = distance
                    best_date = gen_date
                    g_index += 1
                else:
                    # Distance increases, stop here
                    g_index -= 1
                    break

            if best_date is not None:
                node.scheduled_date = best_date
            else:
                # Fallback safety
                node.scheduled_date = node.due_date

        # Bulk update in batches
        for k in range(0, len(nodes), 1000):
            TaskNode.objects.using(db_alias).bulk_update(
                nodes[k:k + 1000],
                ["scheduled_date"],
            )

    # Non-recurrent tasks: copy due_date
    TaskNode.objects.using(db_alias).filter(
        scheduled_date__isnull=True,
        due_date__isnull=False,
    ).update(scheduled_date=models.F("due_date"))


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0137_add_threats_to_finding"),
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
        migrations.RunPython(populate_scheduled_date, migrations.RunPython.noop),
    ]
