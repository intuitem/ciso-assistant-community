import django.db.models.deletion
from django.db import migrations, models


def mark_seeded_classes_builtin(apps, schema_editor):
    """Pre-existing classes all came from AssetClass.create_default_values()."""
    AssetClass = apps.get_model("core", "AssetClass")
    AssetClass.objects.update(builtin=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0180_securityexception_evidences"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetclass",
            name="builtin",
            field=models.BooleanField(default=False, verbose_name="Built-in"),
        ),
        migrations.AddField(
            model_name="assetclass",
            name="is_visible",
            field=models.BooleanField(default=True, verbose_name="Is Visible"),
        ),
        migrations.AddField(
            model_name="assetclass",
            name="translations",
            field=models.JSONField(
                blank=True, default=dict, null=True, verbose_name="Translations"
            ),
        ),
        migrations.AlterField(
            model_name="assetclass",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="core.assetclass",
            ),
        ),
        migrations.RunPython(
            mark_seeded_classes_builtin,
            migrations.RunPython.noop,
        ),
    ]
