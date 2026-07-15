import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Max, Min


def create_runs(apps, schema_editor):
    PostureResult = apps.get_model("automation", "PostureResult")
    PostureRun = apps.get_model("automation", "PostureRun")
    groups = (
        PostureResult.objects.values("legacy_run_id", "posture_assessment_id")
        .annotate(started_at=Min("timestamp"), tool=Max("tool"))
        .order_by()
    )
    PostureRun.objects.bulk_create(
        [
            PostureRun(
                id=g["legacy_run_id"],
                posture_assessment_id=g["posture_assessment_id"],
                started_at=g["started_at"],
                tool=g["tool"] or "",
            )
            for g in groups
        ],
        batch_size=2000,
    )
    PostureResult.objects.update(run_id=F("legacy_run_id"))


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="postureresult",
            name="unique_posture_result_per_run",
        ),
        migrations.RemoveIndex(
            model_name="postureresult",
            name="automation__posture_2f96c5_idx",
        ),
        migrations.RenameField(
            model_name="postureresult",
            old_name="run_id",
            new_name="legacy_run_id",
        ),
        migrations.CreateModel(
            name="PostureRun",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                ("started_at", models.DateTimeField()),
                ("tool", models.CharField(blank=True, max_length=100)),
                (
                    "posture_assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="runs",
                        to="automation.postureassessment",
                    ),
                ),
            ],
            options={
                "verbose_name": "Posture run",
                "verbose_name_plural": "Posture runs",
                "indexes": [
                    models.Index(
                        fields=["posture_assessment", "started_at"],
                        name="automation__posture_run_idx",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="postureresult",
            name="run",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="results",
                to="automation.posturerun",
            ),
        ),
        migrations.RunPython(create_runs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="postureresult",
            name="run",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="results",
                to="automation.posturerun",
            ),
        ),
        migrations.RemoveField(
            model_name="postureresult",
            name="legacy_run_id",
        ),
        migrations.RemoveField(
            model_name="postureresult",
            name="tool",
        ),
        migrations.AddIndex(
            model_name="postureresult",
            index=models.Index(
                fields=["posture_assessment", "run"],
                name="automation__posture_runfk_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="postureresult",
            constraint=models.UniqueConstraint(
                fields=("run", "asset", "requirement"),
                name="unique_posture_result_per_run",
            ),
        ),
    ]
