from django.apps import apps
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import pre_delete
from structlog import get_logger

logger = get_logger(__name__)

# File fields that share a storage object. Built once; models do not appear later.
_fields_by_storage = {}


def _fields_on_storage(storage):
    cached = _fields_by_storage.get(id(storage))
    if cached is not None:
        return cached
    found = {}
    for model in apps.get_models():
        if not model._meta.managed:
            continue
        names = [
            field.name
            for field in model._meta.local_concrete_fields
            if isinstance(field, models.FileField) and field.storage is storage
        ]
        if names:
            found[model] = names
    _fields_by_storage[id(storage)] = found
    return found


def _referenced_elsewhere(name, storage, using):
    """Some row still points at this stored name.

    Locks those rows, in model order, until the surrounding transaction ends.
    A writer that holds the same rows (promotion locks the source attachment)
    cannot commit a new reference between this check and the storage delete.
    """
    referenced = False
    for model, field_names in _fields_on_storage(storage).items():
        query = Q()
        for field_name in field_names:
            query |= Q(**{field_name: name})
        rows = list(
            model._base_manager.using(using)
            .select_for_update()
            .filter(query)
            .order_by("pk")
        )
        referenced = referenced or bool(rows)
    return referenced


def _delete_field_file(instance, field_file, using):
    name = field_file.name if field_file else None
    if not name:
        return
    storage = field_file.storage
    pk = instance.pk
    label = instance._meta.label
    field_name = field_file.field.name

    def cleanup():
        try:
            with transaction.atomic(using=using):
                if _referenced_elsewhere(name, storage, using):
                    return
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
