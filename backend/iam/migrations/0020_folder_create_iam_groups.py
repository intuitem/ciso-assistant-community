from django.db import migrations, models


def bootstrap_domain_group_settings(apps, schema_editor):
    Folder = apps.get_model("iam", "Folder")
    UserGroup = apps.get_model("iam", "UserGroup")
    RoleAssignment = apps.get_model("iam", "RoleAssignment")
    User = apps.get_model("iam", "User")

    domain_qs = Folder.objects.filter(content_type="DO")
    domain_ids = list(domain_qs.values_list("id", flat=True))
    if domain_ids:
        domain_qs.update(create_iam_groups=True)

    root_folder = Folder.objects.filter(content_type="GL").first()
    if root_folder:
        Folder.objects.filter(id=root_folder.id).update(create_iam_groups=True)
    else:
        return

    managed_folder_ids = [root_folder.id, *domain_ids]

    for folder_id in managed_folder_ids:
        role_assignment_group_ids = list(
            RoleAssignment.objects.filter(
                folder_id=root_folder.id,
                is_recursive=True,
                user_group__folder_id=folder_id,
                perimeter_folders__id=folder_id,
            ).values_list("user_group_id", flat=True)
        )
        if role_assignment_group_ids:
            UserGroup.objects.filter(id__in=role_assignment_group_ids).update(
                builtin=True
            )

    for folder_id in domain_ids:
        builtin_group_ids = list(
            UserGroup.objects.filter(folder_id=folder_id, builtin=True).values_list(
                "id", flat=True
            )
        )
        if not builtin_group_ids:
            Folder.objects.filter(id=folder_id).update(create_iam_groups=False)
            continue
        has_members = User.objects.filter(
            user_groups__id__in=builtin_group_ids
        ).exists()
        if has_members:
            continue
        RoleAssignment.objects.filter(user_group_id__in=builtin_group_ids).delete()
        UserGroup.objects.filter(id__in=builtin_group_ids).delete()
        Folder.objects.filter(id=folder_id).update(create_iam_groups=False)


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0019_add_view_globalsettings_in_custom_roles"),
    ]
    operations = [
        migrations.AddField(
            model_name="folder",
            name="create_iam_groups",
            field=models.BooleanField(
                default=False,
                help_text="Automatically provision IAM groups for domain folders.",
            ),
        ),
        migrations.RunPython(
            bootstrap_domain_group_settings,
            migrations.RunPython.noop,
        ),
    ]
