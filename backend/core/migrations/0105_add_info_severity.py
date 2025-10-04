# Generated manually

from django.db import migrations


def shift_severity_values(apps, schema_editor):
    """
    Shift existing severity values up by 1 to make room for INFO level.
    OLD -> NEW mapping:
    0 (LOW) -> 1
    1 (MEDIUM) -> 2
    2 (HIGH) -> 3
    3 (CRITICAL) -> 4
    -1 (UNDEFINED) stays -1
    """
    SecurityException = apps.get_model("core", "SecurityException")
    Finding = apps.get_model("core", "Finding")
    Vulnerability = apps.get_model("core", "Vulnerability")

    # Update in reverse order to avoid conflicts
    for model in [SecurityException, Finding, Vulnerability]:
        model.objects.filter(severity=3).update(severity=4)  # CRITICAL: 3 -> 4
        model.objects.filter(severity=2).update(severity=3)  # HIGH: 2 -> 3
        model.objects.filter(severity=1).update(severity=2)  # MEDIUM: 1 -> 2
        model.objects.filter(severity=0).update(severity=1)  # LOW: 0 -> 1


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0104_alter_finding_status"),
    ]

    operations = [
        migrations.RunPython(shift_severity_values, migrations.RunPython.noop),
    ]
