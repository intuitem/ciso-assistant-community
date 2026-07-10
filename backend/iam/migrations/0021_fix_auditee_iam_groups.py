from django.db import migrations


def fix_auditee_iam_groups(apps, schema_editor):
    Folder = apps.get_model("iam", "Folder")
    UserGroup = apps.get_model("iam", "UserGroup")
    RoleAssignment = apps.get_model("iam", "RoleAssignment")
    Role = apps.get_model("iam", "Role")
    User = apps.get_model("iam", "User")

    AUDITEE_UG_CODENAME = "BI-UG-ADE"
    AUDITEE_ROLE_CODENAME = "BI-RL-ADE"

    root_folder = Folder.objects.filter(content_type="GL").first()
    if not root_folder:
        return

    auditee_role = Role.objects.filter(name=AUDITEE_ROLE_CODENAME).first()
    if not auditee_role:
        return

    def ensure_auditee_group(folder):
        auditee_group = UserGroup.objects.filter(
            name=AUDITEE_UG_CODENAME, folder=folder
        ).first()
        if not auditee_group:
            auditee_group = UserGroup.objects.create(
                name=AUDITEE_UG_CODENAME,
                folder=folder,
                builtin=True,
            )
            ra = RoleAssignment.objects.create(
                user_group=auditee_group,
                role=auditee_role,
                builtin=True,
                folder=root_folder,
                is_recursive=True,
            )
            ra.perimeter_folders.add(folder)
        elif not auditee_group.builtin:
            auditee_group.builtin = True
            auditee_group.save(update_fields=["builtin"])

    for folder in Folder.objects.filter(content_type="DO"):
        builtin_groups = UserGroup.objects.filter(folder=folder, builtin=True)

        if folder.create_iam_groups:
            ensure_auditee_group(folder)
        else:
            has_members = User.objects.filter(user_groups__in=builtin_groups).exists()

            if has_members:
                Folder.objects.filter(id=folder.id).update(create_iam_groups=True)
                ensure_auditee_group(folder)
            else:
                group_ids = list(builtin_groups.values_list("id", flat=True))
                RoleAssignment.objects.filter(user_group_id__in=group_ids).delete()
                UserGroup.objects.filter(id__in=group_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0020_folder_create_iam_groups"),
    ]
    operations = [
        migrations.RunPython(
            fix_auditee_iam_groups,
            migrations.RunPython.noop,
        ),
    ]
