# Generated by Django 5.1.9 on 2025-06-10 15:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0078_complianceassessment_evidences"),
    ]

    operations = [
        migrations.AddField(
            model_name="finding",
            name="evidences",
            field=models.ManyToManyField(
                blank=True,
                help_text="Evidences related to the follow-up",
                related_name="findings",
                to="core.evidence",
                verbose_name="Evidences",
            ),
        ),
        migrations.AddField(
            model_name="findingsassessment",
            name="evidences",
            field=models.ManyToManyField(
                blank=True,
                help_text="Evidences related to the follow-up",
                related_name="findings_assessments",
                to="core.evidence",
                verbose_name="Evidences",
            ),
        ),
    ]
