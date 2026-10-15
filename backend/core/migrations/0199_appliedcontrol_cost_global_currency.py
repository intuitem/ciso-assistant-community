from django.db import migrations

BATCH_SIZE = 500


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

    # Flush in bounded batches so memory stays flat on large installations.
    to_update = []
    controls = AppliedControl.objects.filter(cost__isnull=False).only("cost")
    for control in controls.iterator(chunk_size=BATCH_SIZE):
        if isinstance(control.cost, dict) and control.cost.get("currency") in (
            None,
            "",
            "€",
        ):
            control.cost["currency"] = currency
            to_update.append(control)
        if len(to_update) >= BATCH_SIZE:
            AppliedControl.objects.bulk_update(to_update, ["cost"])
            to_update = []
    if to_update:
        AppliedControl.objects.bulk_update(to_update, ["cost"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0198_quick_form_scales_facts_review"),
        ("global_settings", "0007_remove_globalsettings_is_published"),
    ]

    operations = [
        migrations.RunPython(align_cost_currency, migrations.RunPython.noop),
    ]
