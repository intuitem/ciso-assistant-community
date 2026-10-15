from django.db import migrations


def align_cost_currency(apps, schema_editor):
    """Realign applied control costs saved with the hardcoded € default.

    Controls created after the global currency was changed were stored in €
    regardless of the setting. Amounts were entered in the global currency,
    so only the currency label is updated, without any conversion.
    """
    GlobalSettings = apps.get_model("global_settings", "GlobalSettings")
    AppliedControl = apps.get_model("core", "AppliedControl")

    settings = GlobalSettings.objects.filter(name="general").first()
    currency = (settings.value or {}).get("currency") if settings else None
    if not currency or currency == "€":
        return

    to_update = []
    for control in AppliedControl.objects.filter(cost__isnull=False).only("cost"):
        if isinstance(control.cost, dict) and control.cost.get("currency") in (
            None,
            "",
            "€",
        ):
            control.cost["currency"] = currency
            to_update.append(control)
    AppliedControl.objects.bulk_update(to_update, ["cost"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0198_quick_form_scales_facts_review"),
        ("global_settings", "0007_remove_globalsettings_is_published"),
    ]

    operations = [
        migrations.RunPython(align_cost_currency, migrations.RunPython.noop),
    ]
