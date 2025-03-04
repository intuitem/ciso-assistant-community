from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog
from .registry import audit_registry


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    """Signal handler to log model creation and updates."""
    # Skip logging for AuditLog model itself to avoid infinite recursion
    if sender == AuditLog:
        return

    # Check if this model should be monitored
    operation = "C" if created else "U"
    if not audit_registry.should_log(sender, operation):
        return

    try:
        # Get the content type
        content_type = ContentType.objects.get_for_model(sender)

        # Extract changed fields for updates
        event_data = {}
        if not created:
            # For updates, we might want to track what changed
            if hasattr(instance, "_changed_fields"):
                event_data["changed_fields"] = instance._changed_fields

                # Include previous and current values if available
                if hasattr(instance, "_changed_data"):
                    event_data["changes"] = instance._changed_data

        # Store model name for better display
        event_data["model_name"] = sender.__name__

        # Get the current user from thread local storage
        # Note: This requires adding user to local thread in middleware or request processor
        from threading import local

        _thread_locals = local()
        user = getattr(_thread_locals, "user", None)

        # Create the audit log entry
        AuditLog.objects.create(
            user=user,
            operation=operation,
            content_type=content_type,
            object_id=str(instance.pk),
            event_data=event_data,
        )
    except Exception as e:
        # Log the error but don't interrupt the save operation
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create audit log: {e}")


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    """Signal handler to log model deletion."""
    # Skip logging for AuditLog model itself
    if sender == AuditLog:
        return

    # Check if this model should be monitored for deletion
    if not audit_registry.should_log(sender, "D"):
        return

    try:
        # Get the content type
        content_type = ContentType.objects.get_for_model(sender)

        # Get the current user from thread local storage
        from threading import local

        _thread_locals = local()
        user = getattr(_thread_locals, "user", None)

        # Create the audit log entry
        AuditLog.objects.create(
            user=user,
            operation="D",
            content_type=content_type,
            object_id=str(instance.pk),
            event_data={"model_name": sender.__name__, "model_str": str(instance)},
        )
    except Exception as e:
        # Log the error but don't interrupt the delete operation
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create audit log: {e}")
