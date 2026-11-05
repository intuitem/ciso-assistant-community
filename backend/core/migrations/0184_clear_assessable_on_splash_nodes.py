"""Splash screen nodes are never assessable. The framework builder used to
leave `assessable=True` behind when an existing requirement node was switched
to splash display mode; the loader now normalizes this on import, and this
migration heals frameworks already loaded with the stale flag."""

from django.db import migrations


def clear_assessable_on_splash_nodes(apps, schema_editor):
    RequirementNode = apps.get_model("core", "RequirementNode")
    RequirementNode.objects.filter(display_mode="splash", assessable=True).update(
        assessable=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0183_cleanup_stale_permissions_from_model_renamed"),
    ]

    operations = [
        migrations.RunPython(
            clear_assessable_on_splash_nodes, migrations.RunPython.noop
        ),
    ]
