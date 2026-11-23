"""Introduce the ``view_user_full`` permission and grant it to existing custom roles.

A user's sign-in and administration details are now served only with the full view
of that user (see the full-view-permissions ADR): to the user themself, and to
holders of ``view_user_full`` or ``change_user`` on the user's folder.

This migration does two things:
  1. Declares the permission on ``User`` (Meta options).
  2. Grants it to every custom role holding ``view_user``, so those roles keep
     serving what they serve today. Global's default role is left out: it is held
     by every domain member, which is the exposure this change removes. Builtin
     roles are re-synced by ``startup`` on each migrate.

The permission row is created explicitly in the data step: custom permissions
declared via ``Meta.permissions`` are materialised by Django's ``create_permissions``
post_migrate signal, which has not run yet while this migration executes.
"""

from django.db import migrations

PERM_CODENAME = "view_user_full"
PERM_NAME = "Can view users' full record"
ROOT_FOLDER_CONTENT_TYPE = "GL"


def grant_view_user_full(apps, schema_editor):
    Folder = apps.get_model("iam", "Folder")
    Role = apps.get_model("iam", "Role")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    ct, _ = ContentType.objects.get_or_create(app_label="iam", model="user")
    perm, _ = Permission.objects.get_or_create(
        codename=PERM_CODENAME,
        content_type=ct,
        defaults={"name": PERM_NAME},
    )

    global_default_roles = Folder.objects.filter(
        content_type=ROOT_FOLDER_CONTENT_TYPE, default_role__isnull=False
    ).values("default_role")
    for role in Role.objects.filter(
        builtin=False,
        permissions__content_type=ct,
        permissions__codename="view_user",
    ).exclude(id__in=global_default_roles):
        role.permissions.add(perm)


def noop(apps, schema_editor):
    # Irreversible-by-design: we don't strip the grant on downgrade.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0032_folder_ref_id"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={
                "permissions": (
                    ("backup", "backup"),
                    ("restore", "restore"),
                    ("view_user_full", "Can view users' full record"),
                ),
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
        migrations.RunPython(grant_view_user_full, noop),
    ]
