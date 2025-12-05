# Generated manually for data preservation
# Migrate from solution (ForeignKey) to solutions (ManyToMany)

from django.db import migrations, models


def copy_solution_to_solutions(apps, schema_editor):
    """Copy existing solution values to the new solutions field"""
    Contract = apps.get_model("tprm", "Contract")

    # Iterate through all contracts that have a solution assigned
    for contract in Contract.objects.filter(solution__isnull=False):
        # Add the single solution to the solutions ManyToMany field
        contract.solutions.add(contract.solution)


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0008_entity_country_entity_currency_and_more"),
    ]

    operations = [
        # Step 1: Add the new solutions ManyToManyField
        migrations.AddField(
            model_name="contract",
            name="solutions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Solutions covered by this contract",
                related_name="contracts",
                to="tprm.solution",
                verbose_name="Solutions",
            ),
        ),
        # Step 2: Copy data from solution to solutions
        migrations.RunPython(
            copy_solution_to_solutions,
            reverse_code=migrations.RunPython.noop,
        ),
        # Step 3: Remove the old solution ForeignKey field
        migrations.RemoveField(
            model_name="contract",
            name="solution",
        ),
    ]
