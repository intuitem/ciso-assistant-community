from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0202_custom_word_template_typst"),
    ]

    operations = [
        migrations.AddField(
            model_name="requirementnode",
            name="evidence_required",
            field=models.BooleanField(
                default=False,
                help_text="When set, the requirement cannot be submitted without at least one evidence attached.",
                verbose_name="Evidence required",
            ),
        ),
    ]
