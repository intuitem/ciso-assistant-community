from .config import WebhookConfigBase


class WebhookRegistry:
    def __init__(self):
        self._registry = {}  # {ModelClass: ConfigClass}

    def register(self, model_class, events=None):
        """
        A method for registering a model with the webhook system.

        Example:
            webhook_registry.register(AppliedControl)
        """
        if model_class in self._registry:
            # This check prevents duplicate registrations on app reloads
            return

        class GenericWebhookConfig(WebhookConfigBase):
            def __init__(self, model_class, events):
                self.model_class = model_class
                self.model_name = model_class._meta.model_name.lower()
                self.events = events or ["created", "updated", "deleted"]

            def get_event_type(self, instance, action):
                return f"{self.model_name}.{action}"

            def get_payload(self, instance):
                return {"id": str(instance.id)}

            def get_event_types(self):
                return [f"{self.model_name}.{event}" for event in self.events]

        self._registry[model_class] = GenericWebhookConfig(model_class, events)

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
