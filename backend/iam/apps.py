from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iam"

    def ready(self):
        from django.apps import apps
        from django.db.models.signals import m2m_changed

        from iam.cache_builders import (
            invalidate_groups_cache,
            invalidate_assignments_cache,
            invalidate_roles_cache,
        )

        User = apps.get_model("iam", "User")
        RoleAssignment = apps.get_model("iam", "RoleAssignment")
        Role = apps.get_model("iam", "Role")
        GroupMembershipSource = apps.get_model("iam", "GroupMembershipSource")

        def _user_groups_changed(sender, instance, action, **kwargs):
            if action in {"post_add", "post_remove", "post_clear"}:
                invalidate_groups_cache()
                invalidate_assignments_cache()

        def _ra_perimeters_changed(sender, instance, action, **kwargs):
            if action in {"post_add", "post_remove", "post_clear"}:
                invalidate_assignments_cache()

        def _role_permissions_changed(sender, instance, action, **kwargs):
            if action in {"post_add", "post_remove", "post_clear"}:
                invalidate_roles_cache()

        def _membership_pairs(instance, pk_set, reverse):
            # m2m_changed: reverse=True means instance is a UserGroup and
            # pk_set holds user ids; otherwise instance is a User and pk_set
            # holds user_group ids.
            pks = pk_set or set()
            if reverse:
                return [(uid, instance.pk) for uid in pks]
            return [(instance.pk, gid) for gid in pks]

        def _maintain_membership_sources(
            sender, instance, action, reverse, pk_set, **kwargs
        ):
            # Keep GroupMembershipSource in sync with *manual* user_groups
            # edits. Federation helpers (iam.group_membership) create their
            # source row before .add(), so a manual add is one where nothing
            # yet explains the edge -> stamp a channel="manual" row. A manual
            # removal drops every source for that pair (federation re-asserts
            # on next sync if still claimed).
            if action == "post_add":
                for user_id, group_id in _membership_pairs(
                    instance, pk_set, reverse
                ):
                    if not GroupMembershipSource.objects.filter(
                        user_id=user_id, user_group_id=group_id
                    ).exists():
                        GroupMembershipSource.objects.create(
                            user_id=user_id,
                            user_group_id=group_id,
                            source=None,
                            channel="manual",
                        )
            elif action == "post_remove":
                for user_id, group_id in _membership_pairs(
                    instance, pk_set, reverse
                ):
                    GroupMembershipSource.objects.filter(
                        user_id=user_id, user_group_id=group_id
                    ).delete()
            elif action == "post_clear":
                if reverse:
                    GroupMembershipSource.objects.filter(
                        user_group_id=instance.pk
                    ).delete()
                else:
                    GroupMembershipSource.objects.filter(
                        user_id=instance.pk
                    ).delete()

        m2m_changed.connect(
            _user_groups_changed,
            sender=User.user_groups.through,
            dispatch_uid="iam.user_groups.m2m.invalidate_caches",
            weak=False,
        )
        m2m_changed.connect(
            _maintain_membership_sources,
            sender=User.user_groups.through,
            dispatch_uid="iam.user_groups.m2m.membership_sources",
            weak=False,
        )
        m2m_changed.connect(
            _ra_perimeters_changed,
            sender=RoleAssignment.perimeter_folders.through,
            dispatch_uid="iam.roleassignment.perimeter_folders.m2m.invalidate_assignments_cache",
            weak=False,
        )
        m2m_changed.connect(
            _role_permissions_changed,
            sender=Role.permissions.through,
            dispatch_uid="iam.role.permissions.m2m.invalidate_roles_cache",
            weak=False,
        )
