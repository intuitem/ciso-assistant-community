from django.apps import apps
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import pre_delete
from structlog import get_logger

logger = get_logger(__name__)


def _referenced_elsewhere(instance, name, using):
    """Another row of this model still points at the same stored name.

    Runs after commit, when the deleted row is already gone. Excluding its pk
    would hide a replacement that reused that pk and the same file.
    """
    query = Q()
    for field in instance._meta.concrete_fields:
        if isinstance(field, models.FileField):
            query |= Q(**{field.name: name})
    if not query:
        return False
    return instance._meta.model._base_manager.using(using).filter(query).exists()


def _delete_field_file(instance, field_file, using):
    name = field_file.name if field_file else None
    if not name:
        return
    storage = field_file.storage
    pk = instance.pk
    label = instance._meta.label
    field_name = field_file.field.name

    def cleanup():
        if _referenced_elsewhere(instance, name, using):
            return
        try:
            storage.delete(name)
        except Exception as e:
            logger.warning(
                "Failed to delete stored file",
                model=label,
                pk=pk,
                field=field_name,
                error=str(e),
            )

    transaction.on_commit(cleanup, using=using)


def _delete_stored_files(sender, instance, using, **kwargs):
    for field in instance._meta.concrete_fields:
        if isinstance(field, models.FileField):
            _delete_field_file(instance, getattr(instance, field.name), using)


def _delete_indexed_document_file(sender, instance, using, **kwargs):
    # Often the source path (evidence attachment, uploaded revision). Only a
    # copy under this field's upload_to belongs to the index row.
    file = instance.file
    upload_to = file.field.upload_to
    if file.name and isinstance(upload_to, str) and file.name.startswith(upload_to):
        _delete_field_file(instance, file, using)


def _connect_file_cleanup():
    for model in apps.get_models():
        if not any(
            isinstance(field, models.FileField) for field in model._meta.concrete_fields
        ):
            continue
        handler = (
            _delete_indexed_document_file
            if model._meta.label == "chat.IndexedDocument"
            else _delete_stored_files
        )
        pre_delete.connect(
            handler,
            sender=model,
            dispatch_uid=f"delete-stored-files-{model._meta.label_lower}",
        )


_connect_file_cleanup()
