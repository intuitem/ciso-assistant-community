# Generated manually for data backfill

from django.db import migrations


def populate_risk_scenario_folder(apps, schema_editor):
    """
    Populate the folder field on RiskScenario based on its parent risk assessment's folder.
    """
    RiskScenario = apps.get_model("core", "RiskScenario")

    for scenario in RiskScenario.objects.select_related(
        "risk_assessment", "risk_assessment__folder"
    ).iterator():
        if scenario.risk_assessment and scenario.risk_assessment.folder:
            scenario.folder = scenario.risk_assessment.folder
            scenario.save(update_fields=["folder"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0133_riskscenario_folder_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_risk_scenario_folder, migrations.RunPython.noop),
    ]
