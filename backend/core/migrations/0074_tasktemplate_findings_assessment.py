# Generated by Django 5.1.9 on 2025-05-16 13:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0073_alter_asset_security_objectives"),
    ]

    operations = [
        migrations.AddField(
            model_name="tasktemplate",
            name="findings_assessment",
            field=models.ManyToManyField(
                blank=True,
                help_text="Finding assessments related to the task",
                related_name="task_templates",
                to="core.findingsassessment",
                verbose_name="Finding assessments",
            ),
        ),
    ]
