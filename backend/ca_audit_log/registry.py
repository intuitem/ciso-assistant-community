class AuditRegistry:
    """
    Registry to manage which models and operations should be audited.
    """

    def __init__(self):
        self._registry = {}

    def register(self, model_class, operations=None):
        """
        Register a model for auditing with specified operations.

        Args:
            model_class: The Django model class to monitor
            operations: List of operations to log ('C', 'U', 'D').
                       If None, all operations except 'R' will be logged.
        """
        if operations is None:
            operations = ["C", "U", "D"]  # Default to all except READ

        self._registry[model_class] = operations

    def unregister(self, model_class):
        """Remove a model from the audit registry."""
        if model_class in self._registry:
            del self._registry[model_class]

    def should_log(self, model_class, operation):
        """Check if a model operation should be logged."""
        return (
            model_class in self._registry and operation in self._registry[model_class]
        )


# Create a global registry instance
audit_registry = AuditRegistry()
