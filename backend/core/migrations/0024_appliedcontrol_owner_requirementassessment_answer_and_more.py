# Generated by Django 5.1 on 2024-09-03 08:21

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0023_alter_appliedcontrol_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="appliedcontrol",
            name="owner",
            field=models.ManyToManyField(
                blank=True,
                related_name="applied_controls",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Owner",
            ),
        ),
        migrations.AddField(
            model_name="requirementassessment",
            name="answer",
            field=models.JSONField(blank=True, null=True, verbose_name="Answer"),
        ),
        migrations.AddField(
            model_name="requirementassessment",
            name="review_conclusion",
            field=models.CharField(
                blank=True,
                choices=[
                    ("na", "N/A"),
                    ("ok", "OK"),
                    ("warning", "Warning"),
                    ("blocker", "Blocker"),
                ],
                max_length=10,
                null=True,
                verbose_name="Review conclusion",
            ),
        ),
        migrations.AddField(
            model_name="requirementassessment",
            name="review_observation",
            field=models.TextField(
                blank=True, null=True, verbose_name="Review Observation"
            ),
        ),
        migrations.AddField(
            model_name="requirementnode",
            name="question",
            field=models.JSONField(blank=True, null=True, verbose_name="Question"),
        ),
    ]