from django.db import migrations
import json

def fix_libraries_objects_meta(apps, schema_editor) :
    StoredLibrary = apps.get_model("core", "StoredLibrary")
    LoadedLibrary = apps.get_model("core", "LoadedLibrary")

    for library in StoredLibrary.objects.all() :
        objects = json.loads(library.content)
        library.objects_meta = {
            key: (1 if key in ["framework", "requirement_mapping_set"] else len(value))
            for key, value in objects.items()
        }
        library.save()

    for library in LoadedLibrary.objects.all():
        objects_meta = {}
        for object_name, object_set in [
            ("frameworks", library.frameworks),
            ("threats", library.threats),
            ("reference_controls", library.reference_controls),
            ("risk_matrix", library.risk_matrices)
        ] :
            count = object_set.count()
            if count > 0 :
                objects_meta[object_name] = count

        library.objects_meta = objects_meta
        library.save()

class Migration(migrations.Migration):
    dependencies = [
      ("core", "0019_merge_20240726_2156"),
    ]

    operations = [
      migrations.RunPython(fix_libraries_objects_meta)
    ]

