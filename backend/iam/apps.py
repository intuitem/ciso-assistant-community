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

        _patch_allauth_auth_error_logging()


def _patch_allauth_auth_error_logging():
    """Wrap allauth's render_authentication_error to log every silent SSO failure.

    allauth's OAuth2CallbackView swallows OAuth2Error / RequestException /
    ProviderException and converts them into a redirect via
    render_authentication_error. Without this patch, the exception details are
    lost and we only observe "user is anonymous after callback".
    """
    import functools
    import sys

    import structlog
    from allauth.socialaccount import helpers

    if getattr(helpers.render_authentication_error, "_ciso_patched", False):
        return

    logger = structlog.get_logger("iam.sso.allauth")
    original = helpers.render_authentication_error

    @functools.wraps(original)
    def render_authentication_error(
        request, provider, error="unknown", exception=None, extra_context=None
    ):
        provider_id = (
            getattr(provider, "id", None)
            or getattr(provider, "provider_id", None)
            or (provider if isinstance(provider, str) else None)
        )
        logger.error(
            "allauth auth error",
            provider=provider_id,
            error=str(error) if error else None,
            exception_type=type(exception).__name__ if exception else None,
            has_socialaccount_state=bool(request.session.get("socialaccount_state")),
            path=request.path,
            query_error=request.GET.get("error"),
        )
        logger.debug(
            "allauth auth error for debugging",
            provider=provider_id,
            exception_msg=str(exception) if exception else None,
            query_error_description=request.GET.get("error_description"),
            extra_context_keys=sorted((extra_context or {}).keys()),
            session_keys=sorted(request.session.keys()),
            cookie_names=sorted(request.COOKIES.keys()),
            exc_info=exception is not None,
        )
        return original(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )

    render_authentication_error._ciso_patched = True

    for module in list(sys.modules.values()):
        if module is None:
            continue
        if getattr(module, "render_authentication_error", None) is original:
            module.render_authentication_error = render_authentication_error
