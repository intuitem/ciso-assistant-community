from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iam"

    def ready(self):
        from django.apps import apps
        from django.db.models.signals import m2m_changed, post_delete

        from iam.cache_builders import (
            invalidate_groups_cache,
            invalidate_assignments_cache,
            invalidate_roles_cache,
        )

        User = apps.get_model("iam", "User")
        RoleAssignment = apps.get_model("iam", "RoleAssignment")
        Role = apps.get_model("iam", "Role")
        IdPGroup = apps.get_model("iam", "IdPGroup")
        ServiceAccount = apps.get_model("iam", "ServiceAccount")

        self._patch_client_check_secret(ServiceAccount)

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

        def _idp_group_membership_changed(sender, instance, action, **kwargs):
            if action in {"post_add", "post_remove", "post_clear"}:
                invalidate_groups_cache()
                invalidate_assignments_cache()

        def _idp_group_deleted(sender, instance, **kwargs):
            invalidate_groups_cache()
            invalidate_assignments_cache()

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
        m2m_changed.connect(
            _idp_group_membership_changed,
            sender=User.idp_groups.through,
            dispatch_uid="iam.user.idp_groups.m2m.invalidate_caches",
            weak=False,
        )
        m2m_changed.connect(
            _idp_group_membership_changed,
            sender=IdPGroup.user_groups.through,
            dispatch_uid="iam.idpgroup.user_groups.m2m.invalidate_caches",
            weak=False,
        )
        post_delete.connect(
            _idp_group_deleted,
            sender=IdPGroup,
            dispatch_uid="iam.idpgroup.post_delete.invalidate_caches",
            weak=False,
        )

    def _patch_client_check_secret(self, ServiceAccount):
        """Give service accounts a grace-period secret during rotation.

        allauth's Client.check_secret is the single call site oauthlib uses
        to authenticate the client_credentials grant — there's no adapter
        hook or multi-secret support upstream, so the fallback to a
        previous, not-yet-expired secret has to be patched in here.
        """
        from allauth.idp.oidc.models import Client
        from django.contrib.auth.hashers import check_password
        from django.utils import timezone

        original_check_secret = Client.check_secret

        def check_secret_with_grace_period(self, secret):
            if original_check_secret(self, secret):
                return True
            service_account = ServiceAccount.objects.filter(client=self).first()
            if not service_account or not service_account.previous_secret_hash:
                return False
            if (
                not service_account.previous_secret_expires_at
                or service_account.previous_secret_expires_at < timezone.now()
            ):
                return False
            return check_password(secret, service_account.previous_secret_hash)

        Client.check_secret = check_secret_with_grace_period
