from django.db import migrations


def trust_existing_oidc_configurations(apps, schema_editor):
    """OIDC logins now require the IdP to vouch for the email (`email_verified`
    or `xms_edov`) unless the operator enabled "trust email without
    verification claim". Deployments configured before this rule kept working
    on silence, so keep them working: turn the switch on where OIDC is already
    configured. New configurations start strict."""
    GlobalSettings = apps.get_model("global_settings", "GlobalSettings")
    for row in GlobalSettings.objects.filter(name="sso"):
        value = row.value or {}
        if value.get("provider") != "openid_connect":
            continue
        settings = value.get("settings") or {}
        if "trust_email_without_verified_claim" in settings:
            continue
        settings["trust_email_without_verified_claim"] = True
        value["settings"] = settings
        row.value = value
        row.save(update_fields=["value"])


class Migration(migrations.Migration):
    dependencies = [
        ("global_settings", "0007_remove_globalsettings_is_published"),
    ]

    operations = [
        migrations.RunPython(
            trust_existing_oidc_configurations, migrations.RunPython.noop
        ),
    ]
