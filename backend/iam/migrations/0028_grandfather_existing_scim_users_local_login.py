from django.db import migrations


def grandfather_existing_scim_users(apps, schema_editor):
    User = apps.get_model("iam", "User")
    User.objects.filter(is_scim_managed=True, keep_local_login=False).update(
        keep_local_login=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0027_cleanup_stray_domain_iam_groups"),
    ]
    operations = [
        migrations.RunPython(
            grandfather_existing_scim_users,
            migrations.RunPython.noop,
        ),
    ]
