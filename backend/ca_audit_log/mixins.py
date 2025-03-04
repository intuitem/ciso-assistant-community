class TrackFieldChanges:
    """
    Mixin to track which fields have changed in a model instance.
    Add this to models you want to track the changed fields for.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_state = self._get_field_values()
        self._changed_fields = []

    def _get_field_values(self):
        return {f.name: getattr(self, f.name) for f in self._meta.fields}

    def save(self, *args, **kwargs):
        if self.pk:
            # If this is an update, determine what changed
            current_state = self._get_field_values()
            self._changed_fields = [
                field
                for field, value in current_state.items()
                if field in self._original_state
                and self._original_state[field] != value
            ]
        super().save(*args, **kwargs)
        # Update original state after save
        self._original_state = self._get_field_values()
        self._changed_fields = []
