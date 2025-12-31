from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iam"

    def ready(self):
        #  Register m2m invalidation hooks
        from django.db.models.signals import m2m_changed

        from iam.cache_builders import (
            invalidate_groups_cache,
            invalidate_assignments_cache,
        )

        # Import models only inside ready() to avoid import-time circular deps
        from iam.models import User  # or use apps.get_model if you prefer

        def _user_groups_changed(sender, instance, action, **kwargs):
            # Only after DB has changed
            if action in {"post_add", "post_remove", "post_clear"}:
                invalidate_groups_cache()
                # effective permissions depend on group membership
                invalidate_assignments_cache()

        m2m_changed.connect(
            _user_groups_changed,
            sender=User.user_groups.through,
            dispatch_uid="iam.user_groups.m2m.invalidate_caches",
            weak=False,
        )
