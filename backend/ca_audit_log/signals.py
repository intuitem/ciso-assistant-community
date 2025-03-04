# signals.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog
from .registry import audit_registry

logger = logging.getLogger(__name__)


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    """Signal handler to log model creation and updates."""
    # Skip logging for AuditLog model itself to avoid infinite recursion
    if sender == AuditLog:
        return

    # Debug logging to see if signal is received
    logger.debug(f"post_save signal received for {sender.__name__} (created={created})")

    # Check if this model should be monitored
    operation = "C" if created else "U"
    if not audit_registry.should_log(sender, operation):
        logger.debug(f"Model {sender.__name__} not registered for {operation}")
        return

    try:
        # Get the content type
        content_type = ContentType.objects.get_for_model(sender)

        # Extract changed fields for updates
        event_data = {}
        if not created:
            # For updates, we might want to track what changed
            # This is a simple implementation - you might want to customize
            event_data["changed_fields"] = []
            if hasattr(instance, "_changed_fields"):
                event_data["changed_fields"] = instance._changed_fields
                logger.debug(f"Changed fields: {instance._changed_fields}")
            else:
                logger.debug("No _changed_fields attribute found on instance")

        # Get the current user from thread local storage
        from threading import local

        _thread_locals = local()
        user = getattr(_thread_locals, "user", None)
        logger.debug(f"Current user from thread locals: {user}")

        # Create the audit log entry
        audit_log = AuditLog.objects.create(
            user=user,
            operation=operation,
            content_type=content_type,
            object_id=str(instance.pk),
            event_data=event_data,
        )
        logger.debug(f"Created audit log entry: {audit_log.id}")
    except Exception as e:
        # Log the error but don't interrupt the save operation
        logger.error(f"Failed to create audit log: {e}", exc_info=True)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    """Signal handler to log model deletion."""
    # Skip logging for AuditLog model itself
    if sender == AuditLog:
        return

    # Debug logging
    logger.debug(f"post_delete signal received for {sender.__name__}")

    # Check if this model should be monitored for deletion
    if not audit_registry.should_log(sender, "D"):
        logger.debug(f"Model {sender.__name__} not registered for D")
        return

    try:
        # Get the content type
        content_type = ContentType.objects.get_for_model(sender)

        # Get the current user from thread local storage
        from threading import local

        _thread_locals = local()
        user = getattr(_thread_locals, "user", None)
        logger.debug(f"Current user from thread locals: {user}")

        # Create the audit log entry
        audit_log = AuditLog.objects.create(
            user=user,
            operation="D",
            content_type=content_type,
            object_id=str(instance.pk),
            event_data={"model_str": str(instance)},
        )
        logger.warn(f"Created audit log entry: {audit_log.id}")
    except Exception as e:
        # Log the error but don't interrupt the delete operation
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
