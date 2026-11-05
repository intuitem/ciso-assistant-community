import django.db.models.deletion
from django.db import migrations, models


def forward(apps, schema_editor):
    from privacy.terminology_seeds import (
        DEFAULT_PROCESSING_NATURES,
        DEFAULT_PERSONAL_DATA_CATEGORIES,
    )

    Terminology = apps.get_model("core", "Terminology")
    Processing = apps.get_model("privacy", "Processing")
    PersonalData = apps.get_model("privacy", "PersonalData")

    def seed(items):
        for item in items:
            Terminology.objects.update_or_create(
                name=item["name"],
                field_path=item["field_path"],
                defaults={k: v for k, v in item.items() if k != "is_visible"},
                create_defaults=item,
            )

    seed(DEFAULT_PROCESSING_NATURES)
    seed(DEFAULT_PERSONAL_DATA_CATEGORIES)

    def term_for(name, field_path):
        term = Terminology.objects.filter(name=name, field_path=field_path).first()
        if term is None:
            term = Terminology.objects.create(
                name=name,
                field_path=field_path,
                builtin=False,
                is_visible=True,
                is_published=True,
            )
        return term

    nature_cache = {}
    for processing in Processing.objects.all():
        term_ids = []
        for old in processing.nature_old.all():
            if old.name not in nature_cache:
                nature_cache[old.name] = term_for(old.name, "processing.nature")
            term_ids.append(nature_cache[old.name].id)
        processing.nature.set(term_ids)

    category_cache = {}
    for pd in PersonalData.objects.all():
        code = pd.category_old
        if code not in category_cache:
            category_cache[code] = term_for(code, "personal_data.category")
        pd.category = category_cache[code]
        pd.save(update_fields=["category"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("core", "0174_alter_terminology_field_path"),
        ("privacy", "0019_databreach_evidences"),
    ]

    operations = [
        migrations.RenameField(
            model_name="processing", old_name="nature", new_name="nature_old"
        ),
        migrations.AddField(
            model_name="processing",
            name="nature",
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={
                    "field_path": "processing.nature",
                    "is_visible": True,
                },
                related_name="processing_natures",
                to="core.terminology",
            ),
        ),
        migrations.RenameField(
            model_name="personaldata", old_name="category", new_name="category_old"
        ),
        migrations.AddField(
            model_name="personaldata",
            name="category",
            field=models.ForeignKey(
                null=True,
                limit_choices_to={
                    "field_path": "personal_data.category",
                    "is_visible": True,
                },
                on_delete=django.db.models.deletion.PROTECT,
                related_name="personal_data_categories",
                to="core.terminology",
            ),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="personaldata",
            name="category",
            field=models.ForeignKey(
                limit_choices_to={
                    "field_path": "personal_data.category",
                    "is_visible": True,
                },
                on_delete=django.db.models.deletion.PROTECT,
                related_name="personal_data_categories",
                to="core.terminology",
            ),
        ),
        migrations.RemoveField(model_name="processing", name="nature_old"),
        migrations.RemoveField(model_name="personaldata", name="category_old"),
        migrations.DeleteModel(name="ProcessingNature"),
    ]
