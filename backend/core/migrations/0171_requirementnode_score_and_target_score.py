from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0170_alter_terminology_field_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="requirementnode",
            name="max_score",
            field=models.IntegerField(
                blank=True, null=True, verbose_name="Maximum score"
            ),
        ),
        migrations.AddField(
            model_name="requirementnode",
            name="min_score",
            field=models.IntegerField(
                blank=True, null=True, verbose_name="Minimum score"
            ),
        ),
        migrations.AddField(
            model_name="requirementnode",
            name="scores_definition_ref",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="Scores definition reference",
            ),
        ),
        migrations.AddField(
            model_name="requirementnode",
            name="target_score",
            field=models.FloatField(blank=True, null=True, verbose_name="Target score"),
        ),
        migrations.AddField(
            model_name="requirementassessment",
            name="target_score",
            field=models.FloatField(blank=True, null=True, verbose_name="Target score"),
        ),
    ]
