"""Mixin that makes a Django model syncable with remote ITSM integrations.

A model opts in by inheriting ``IntegrationSyncableMixin``, declaring
``INTEGRATION_MODEL_KEY`` (a key registered in ``integrations.syncable``) and
``INTEGRATION_SYNCABLE_FIELDS`` (the fields whose change triggers a sync), and
calling the helpers from its ``save()``.

This module imports nothing from ``core`` or ``integrations.models`` at import
time (only lazily, inside methods) so it is safe to import from model modules.
"""

from __future__ import annotations


class IntegrationSyncableMixin:
    # Overridden per model.
    INTEGRATION_MODEL_KEY: str = ""
    INTEGRATION_SYNCABLE_FIELDS: set[str] = set()

    def _get_changed_fields(self, old_instance) -> list[str]:
        """Names of syncable fields that differ from ``old_instance``."""
        changed = []
        for field in self.INTEGRATION_SYNCABLE_FIELDS:
            if getattr(old_instance, field) != getattr(self, field):
                changed.append(field)
        return changed

    def _capture_sync_changed_fields(self) -> list[str]:
        """Changed syncable fields vs the persisted row ([] when new)."""
        if self.pk is None:
            return []
        old = type(self).objects.filter(pk=self.pk).first()
        return self._get_changed_fields(old) if old else []

    def _trigger_sync(self, is_new: bool, changed_fields: list[str]) -> None:
        """Queue an outbound sync for every active ITSM integration that has a
        mapping configured for this model. No-op when nothing relevant changed
        or no configured integration applies."""
        if not (is_new or changed_fields):
            return

        from django.contrib.contenttypes.models import ContentType
        from django.db import transaction

        from iam.models import Folder
        from integrations.models import IntegrationConfiguration
        from integrations.settings_access import is_model_configured
        from integrations.tasks import sync_object_to_integrations

        configurations = IntegrationConfiguration.objects.filter(
            folder=Folder.get_root_folder(),
            provider__provider_type="itsm",
            is_active=True,
        )
        config_ids = [
            c.id
            for c in configurations
            if is_model_configured(c.settings, self.INTEGRATION_MODEL_KEY)
        ]
        if not config_ids:
            return

        content_type = ContentType.objects.get_for_model(self)
        pk = self.pk
        transaction.on_commit(
            lambda: sync_object_to_integrations.schedule(
                args=(content_type, pk, config_ids, changed_fields),
                delay=1,
            )
        )
