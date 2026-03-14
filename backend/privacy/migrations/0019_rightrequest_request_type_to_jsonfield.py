from django.db import migrations, models


def copy_request_type_to_json(apps, schema_editor):
    """Copy existing single string values into the new JSONField as lists."""
    RightRequest = apps.get_model("privacy", "RightRequest")
    for rr in RightRequest.objects.all():
        old_value = rr.request_type
        if old_value:
            rr.request_type_new = [old_value]
        else:
            rr.request_type_new = []
        rr.save(update_fields=["request_type_new"])


def copy_json_to_request_type(apps, schema_editor):
    """Reverse: copy list back to single string."""
    RightRequest = apps.get_model("privacy", "RightRequest")
    for rr in RightRequest.objects.all():
        val = rr.request_type_new
        if isinstance(val, list) and val:
            rr.request_type = val[0]
        else:
            rr.request_type = "other"
        rr.save(update_fields=["request_type"])


class Migration(migrations.Migration):
    dependencies = [
        ("privacy", "0018_alter_datatransfer_transfer_mechanism"),
    ]

    operations = [
        # Step 1: Add a new temporary JSONField
        migrations.AddField(
            model_name="rightrequest",
            name="request_type_new",
            field=models.JSONField(blank=True, default=list),
        ),
        # Step 2: Copy data from old CharField into new JSONField as lists
        migrations.RunPython(
            copy_request_type_to_json,
            copy_json_to_request_type,
        ),
        # Step 3: Remove old CharField
        migrations.RemoveField(
            model_name="rightrequest",
            name="request_type",
        ),
        # Step 4: Rename new field to original name
        migrations.RenameField(
            model_name="rightrequest",
            old_name="request_type_new",
            new_name="request_type",
        ),
    ]
