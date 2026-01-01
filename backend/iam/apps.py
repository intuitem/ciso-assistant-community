from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iam"


from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iam"

    def ready(self):
        from django.apps import apps
        from django.db.models.signals import m2m_changed, post_migrate

        from iam.cache_builders import (
            invalidate_groups_cache,
            invalidate_assignments_cache,
            invalidate_roles_cache,
            set_cache_ready,
        )

        User = apps.get_model("iam", "User")
        RoleAssignment = apps.get_model("iam", "RoleAssignment")
        Role = apps.get_model("iam", "Role")

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

        m2m_changed.connect(
            _user_groups_changed,
            sender=User.user_groups.through,
            dispatch_uid="iam.user_groups.m2m.invalidate_caches",
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

        def _set_cache_ready(sender, app_config, **kwargs):
            if app_config.label == self.label:
                set_cache_ready()

        post_migrate.connect(
            _set_cache_ready,
            dispatch_uid="iam.post_migrate.set_cache_ready",
            weak=False,
        )
