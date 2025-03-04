import logging
from django.db import models
from django.db.models.signals import post_init
from django.dispatch import receiver

logger = logging.getLogger(__name__)


class TrackFieldChanges:
    """
    Mixin to track which fields have changed in a model instance.
    Add this to models you want to track the changed fields for.
    Compatible with Django 5.
    """

    def __init__(self, *args, **kwargs):
        logger.debug(f"Initializing TrackFieldChanges for {self.__class__.__name__}")
        super().__init__(*args, **kwargs)
        # Initialize tracking after the instance is fully formed
        self._changed_fields = []
        # Use a post_init signal-like approach for Django 5 compatibility
        self._setup_original_state()

    def _setup_original_state(self):
        """Setup the original state after the instance is fully initialized."""
        self._original_state = self._get_field_values()
        logger.debug(f"Set up original state: {self._original_state}")

    def _get_field_values(self):
        """Get current values of all model fields."""
        try:
            values = {f.name: getattr(self, f.name) for f in self._meta.fields}
            return values
        except Exception as e:
            logger.error(f"Error getting field values: {e}")
            return {}

    def save(self, *args, **kwargs):
        """
        Override save to track changes before saving.
        Compatible with Django 5's transaction management.
        """
        logger.debug(f"save() called on {self.__class__.__name__} instance")
        if self.pk:
            # If this is an update, determine what changed
            current_state = self._get_field_values()
            self._changed_fields = [
                field
                for field, value in current_state.items()
                if field in self._original_state
                and self._original_state[field] != value
            ]
            logger.debug(f"Detected changed fields: {self._changed_fields}")

        # Call the parent save method
        super().save(*args, **kwargs)

        # Update original state after save to prepare for the next change detection
        self._original_state = self._get_field_values()
        logger.debug(f"Updated original state after save")

    def refresh_from_db(self, *args, **kwargs):
        """
        Override refresh_from_db to update the original state after refresh.
        This ensures we don't detect phantom changes after a refresh.
        """
        logger.debug(f"refresh_from_db() called on {self.__class__.__name__} instance")
        super().refresh_from_db(*args, **kwargs)
        self._original_state = self._get_field_values()
        self._changed_fields = []
