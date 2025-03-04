from .models import AuditLog
from django.contrib.contenttypes.models import ContentType


def log_custom_event(user, model_class, object_id, operation, event_data=None):
    """
    Utility function to manually log events when needed.

    Args:
        user: The user performing the action
        model_class: The model class of the object
        object_id: The primary key of the object
        operation: One of 'C', 'U', 'D'
        event_data: Dictionary with additional event data
    """
    content_type = ContentType.objects.get_for_model(model_class)
    return AuditLog.objects.create(
        user=user,
        operation=operation,
        content_type=content_type,
        object_id=str(object_id),
        event_data=event_data,
    )
