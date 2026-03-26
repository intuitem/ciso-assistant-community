from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0150_add_editable_mixin_to_riskmatrix"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="localisation",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="Localisation",
            ),
        ),
    ]
