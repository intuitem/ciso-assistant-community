from django.db import models
from django.db.models.signals import post_init
from django.dispatch import receiver


class TrackFieldChanges:
    """
    Mixin to track which fields have changed in a model instance.
    Add this to models you want to track the changed fields for.
    Compatible with Django 5.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize tracking after the instance is fully formed
        self._changed_fields = []
        self._changed_data = {}  # New attribute to store old and new values
        # Use a post_init signal-like approach for Django 5 compatibility
        self._setup_original_state()

    def _setup_original_state(self):
        """Setup the original state after the instance is fully initialized."""
        self._original_state = self._get_field_values()

    def _get_field_values(self):
        """Get current values of all model fields."""
        return {f.name: getattr(self, f.name) for f in self._meta.fields}

    def save(self, *args, **kwargs):
        """
        Override save to track changes before saving.
        Compatible with Django 5's transaction management.
        """
        if self.pk:
            # If this is an update, determine what changed
            current_state = self._get_field_values()
            changed_fields = []
            changed_data = {}

            for field, current_value in current_state.items():
                if field in self._original_state:
                    original_value = self._original_state[field]
                    if original_value != current_value:
                        changed_fields.append(field)
                        # Store both old and new values
                        changed_data[field] = {
                            "old": original_value,
                            "new": current_value,
                        }

            self._changed_fields = changed_fields
            self._changed_data = changed_data

        # Call the parent save method
        super().save(*args, **kwargs)

        # Update original state after save to prepare for the next change detection
        self._original_state = self._get_field_values()
        self._changed_fields = []
        self._changed_data = {}

    def refresh_from_db(self, *args, **kwargs):
        """
        Override refresh_from_db to update the original state after refresh.
        This ensures we don't detect phantom changes after a refresh.
        """
        super().refresh_from_db(*args, **kwargs)
        self._original_state = self._get_field_values()
        self._changed_fields = []
        self._changed_data = {}
