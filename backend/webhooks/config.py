class WebhookConfigBase:
    """
    Base class for a model's webhook configuration.
    This defines the interface for the registry.
    """

    def get_event_type(self, instance, action):
        """
        Returns the event type string (e.g., "appliedcontrol.created").
        'action' is a string like "created", "updated", "deleted".
        """
        raise NotImplementedError

    def get_payload(self, instance):
        """
        Returns the "thin" payload data (e.g., {"id": "..."}).
        """
        raise NotImplementedError

    def get_event_types(self):
        """
        Returns a list of all possible event types for this model.
        Used to populate the UI for event selection.
        """
        raise NotImplementedError
