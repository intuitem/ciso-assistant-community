# Generated by Django 5.1.8 on 2025-05-02 23:02

from django.db import migrations


def fix_finding_folder(apps, schema_editor):
    Finding = apps.get_model("core", "Finding")
    findings = Finding.objects.select_related("findings_assessment").all()

    for finding in findings:
        assessment = finding.findings_assessment
        if assessment and assessment.folder:
            finding.folder = assessment.folder
            finding.save()
        else:
            print(f"[WARN] Finding {finding.id} has no assessment or no folder.")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0069_auto_20250414_2023"),
    ]

    operations = [
        migrations.RunPython(fix_finding_folder),
    ]
