from django.db import migrations


def fix_folder_inheritance(apps, schema_editor):
    """
    Fix folder inheritance for existing QuantScenarios and QuantHypotheses.

    Previously, scenarios and hypotheses were created with the default root folder
    instead of inheriting from their parent study/scenario.
    """
    QuantitativeRiskScenario = apps.get_model("crq", "QuantitativeRiskScenario")
    QuantitativeRiskHypothesis = apps.get_model("crq", "QuantitativeRiskHypothesis")

    # Fix scenarios: inherit folder from parent study
    for scenario in QuantitativeRiskScenario.objects.select_related(
        "quantitative_risk_study"
    ).all():
        if scenario.quantitative_risk_study:
            study_folder = scenario.quantitative_risk_study.folder
            if scenario.folder != study_folder:
                scenario.folder = study_folder
                scenario.save(update_fields=["folder"])

    # Fix hypotheses: inherit folder from parent scenario
    for hypothesis in QuantitativeRiskHypothesis.objects.select_related(
        "quantitative_risk_scenario"
    ).all():
        if hypothesis.quantitative_risk_scenario:
            scenario_folder = hypothesis.quantitative_risk_scenario.folder
            if hypothesis.folder != scenario_folder:
                hypothesis.folder = scenario_folder
                hypothesis.save(update_fields=["folder"])


def reverse_migration(apps, schema_editor):
    """
    No reverse operation - we don't want to break folder assignments.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("crq", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fix_folder_inheritance, reverse_migration),
    ]
