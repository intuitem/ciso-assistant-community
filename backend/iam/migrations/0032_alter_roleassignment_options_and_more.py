from collections import defaultdict
import random
import itertools

from django.db import migrations, models
from django.db.models import Exists, OuterRef
from core.utils import UserGroupCodename
from iam.models import Folder as AppFolder

USER_GROUP_CODENAMES = [
    UserGroupCodename.READER,
    UserGroupCodename.APPROVER,
    UserGroupCodename.ANALYST,
    UserGroupCodename.DOMAIN_MANAGER,
    UserGroupCodename.AUDITEE,
    UserGroupCodename.TECHNICAL_TESTER,
]

USER_GROUP_NAMES = [
    str(user_group_codename) for user_group_codename in USER_GROUP_CODENAMES
]


def delete_unused_user_groups(apps, schema_editor):
    UserGroup = apps.get_model("iam", "UserGroup")
    User = apps.get_model("iam", "User")
    Folder = apps.get_model("iam", "Folder")

    root_folder_id = Folder.objects.filter(
        content_type=AppFolder.ContentType.ROOT
    ).first()

    user_groups = UserGroup.objects.filter(
        builtin=True,
        name__in=USER_GROUP_NAMES,
        idp_groups__isnull=True,
    ).exclude(
        # We don't want to remove user groups inside the root folder.
        folder_id=root_folder_id,
    )

    is_unused_query = ~Exists(User.objects.filter(user_groups=OuterRef("pk")))
    unused_iam_user_groups = user_groups.filter(is_unused_query)
    unused_iam_user_groups.delete()


MAX_NAME_LENGTH = 200


def get_random_string() -> str:
    return "".join(random.choices("0123456789abcdef", k=16))


def adapt_to_constraints(apps, schema_editor):
    RoleAssignment = apps.get_model("iam", "RoleAssignment")
    UserGroup = apps.get_model("iam", "UserGroup")

    RoleAssignment.objects.filter(user_group__isnull=False, user__isnull=False).update(
        user=None
    )
    RoleAssignment.objects.filter(user_group__isnull=True, user__isnull=True).delete()

    user_group_map = defaultdict(list)
    for folder_id, name, id, builtin in UserGroup.objects.values_list(
        "folder_id", "name", "id", "builtin"
    ):
        user_group_map[(folder_id, name)].append((id, builtin))

    duplicated_user_group_id_lists = list(
        itertools.chain.from_iterable(
            [
                # Exclude the builtin group from the list (by sorting from builtin to non-builtin (sorting on the `builin` boolean))?
                id
                for id, _ in sorted(id_list, key=lambda val: val[1], reverse=True)[1:]
            ]
            for id_list in user_group_map.values()
            if len(id_list) > 1
        )
    )

    user_group_to_updates = UserGroup.objects.filter(
        id__in=duplicated_user_group_id_lists
    )

    for user_group_to_update in user_group_to_updates:
        suffix = get_random_string()
        new_name = user_group_to_update.name[: MAX_NAME_LENGTH - len(suffix)] + suffix

        user_group_to_update.name = new_name

    UserGroup.objects.bulk_update(user_group_to_updates, ["name"], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0031_remove_iam_is_published_fields"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="roleassignment",
            options={},
        ),
        migrations.RemoveField(
            model_name="folder",
            name="create_iam_groups",
        ),
        migrations.AlterField(
            model_name="user",
            name="user_groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="The user groups this user belongs to. A user will get all permissions granted to each of their user groups.",
                related_name="users",
                to="iam.usergroup",
                verbose_name="user groups",
            ),
        ),
        migrations.RunPython(
            adapt_to_constraints, reverse_code=migrations.RunPython.noop
        ),
        migrations.AddConstraint(
            model_name="roleassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("user__isnull", True), ("user_group__isnull", False)),
                    models.Q(("user__isnull", False), ("user_group__isnull", True)),
                    _connector="OR",
                ),
                name="role_assignment_is_either_for_user_or_user_group",
            ),
        ),
        migrations.AddConstraint(
            model_name="usergroup",
            constraint=models.UniqueConstraint(
                fields=("name", "folder"), name="unique_name_per_folder"
            ),
        ),
        migrations.RunPython(
            delete_unused_user_groups, reverse_code=migrations.RunPython.noop
        ),
    ]
