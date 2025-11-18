class WebhookRegistry:
    def __init__(self):
        self._registry = {}  # {ModelClass: ConfigClass}

    def register(self, model_class):
        """
        A decorator for registering a model with the webhook system.

        Example:
            @webhook_registry.register(AppliedControl)
            class AppliedControlWebhookConfig(WebhookConfigBase):
                ...
        """

        def decorator(config_class):
            if model_class in self._registry:
                # This check prevents duplicate registrations on app reloads
                return config_class
            self._registry[model_class] = config_class()
            return config_class

        return decorator

    def get_config(self, instance):
        """
        Gets the config instance for a given model instance.
        """
        return self._registry.get(instance.__class__)

    def get_all_event_types(self):
        """
        Helper method to get all possible event types for the UI.
        """
        all_types = set()
        for config in self._registry.values():
            all_types.update(config.get_event_types())
        return sorted(list(all_types))


webhook_registry = WebhookRegistry()
