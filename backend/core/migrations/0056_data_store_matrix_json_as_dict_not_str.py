from django.db import migrations

import json


def make_matrix_json_definition_dict(apps, schema_editor):
    RiskMatrix = apps.get_model("core", "RiskMatrix")

    for matrix in RiskMatrix.objects.all():
        matrix.json_definition = json.loads(matrix.json_definition)
        matrix.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0055_alter_storedlibrary_content"),
    ]

    operations = [migrations.RunPython(make_matrix_json_definition_dict)]
