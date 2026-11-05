from django.db import migrations
from django.db.models import F


def carry_over(apps, schema_editor):
    Solution = apps.get_model("tprm", "Solution")
    SolutionTierChange = apps.get_model("tprm", "SolutionTierChange")
    solutions = Solution.objects.filter(tier__isnull=False, tier_source="")
    for solution in solutions.exclude(tier_changes__isnull=False):
        change = SolutionTierChange.objects.create(
            solution=solution, tier_id=solution.tier_id, source="manual"
        )
        SolutionTierChange.objects.filter(pk=change.pk).update(
            created_at=solution.updated_at
        )
    solutions.update(tier_source="manual", tier_set_at=F("updated_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0026_solution_tier"),
    ]

    operations = [
        migrations.RunPython(carry_over, migrations.RunPython.noop),
    ]
