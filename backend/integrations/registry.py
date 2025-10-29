from typing import Type, Optional
from django.utils.module_loading import import_string
import logging

from integrations.models import IntegrationConfiguration

from .base import (
    BaseIntegrationClient,
    BaseFieldMapper,
    BaseSyncOrchestrator,
)

logger = logging.getLogger(__name__)


class IntegrationProvider:
    """Represents a registered integration provider"""

    def __init__(
        self,
        name: str,
        provider_type: str,
        client_class: Type[BaseIntegrationClient],
        mapper_class: Type[BaseFieldMapper],
        orchestrator_class: Type[BaseSyncOrchestrator],
        display_name: str = "",
        description: str = "",
        config_schema: dict = {},
    ):
        """
        Create a registry entry describing an integration provider and its component classes.
        
        Parameters:
            name (str): Unique provider identifier used for lookup and registration.
            provider_type (str): Category or type of the provider (e.g., "crm", "email").
            client_class (Type[BaseIntegrationClient]): Client implementation used to communicate with the external service.
            mapper_class (Type[BaseFieldMapper]): Field mapper implementation for mapping external to internal fields.
            orchestrator_class (Type[BaseSyncOrchestrator]): Orchestrator implementation that coordinates sync operations.
            display_name (str): Human-facing name shown in UIs; defaults to a title-cased `name` when empty.
            description (str): Short description of the provider.
            config_schema (dict): Configuration schema describing required fields and credential structure (may include keys like `"required"` and `"credentials"`).
        """
        self.name = name
        self.provider_type = provider_type
        self.client_class = client_class
        self.mapper_class = mapper_class
        self.orchestrator_class = orchestrator_class
        self.display_name = display_name or name.title()
        self.description = description
        self.config_schema = config_schema or {}

    def create_orchestrator(
        self, configuration: IntegrationConfiguration
    ) -> BaseSyncOrchestrator:
        """
        Create an orchestrator for this provider using the given configuration.
        
        Parameters:
            configuration (IntegrationConfiguration): Configuration used to initialize the orchestrator.
        
        Returns:
            BaseSyncOrchestrator: An instance of the provider's orchestrator initialized with `configuration`.
        """
        return self.orchestrator_class(configuration)

    def create_client(
        self, configuration: IntegrationConfiguration
    ) -> BaseIntegrationClient:
        """
        Create a client instance for this provider using the given integration configuration.
        
        Parameters:
            configuration (IntegrationConfiguration): Configuration for the integration, including provider identification and credentials used to initialize the client.
        
        Returns:
            BaseIntegrationClient: An instance of the provider's client class initialized with the provided configuration.
        """
        return self.client_class(configuration)

    def create_mapper(self, configuration: IntegrationConfiguration) -> BaseFieldMapper:
        """
        Create a mapper instance for the provider using the given configuration.
        
        Parameters:
            configuration (IntegrationConfiguration): Configuration used to initialize the mapper.
        
        Returns:
            BaseFieldMapper: An instance of the provider's field mapper initialized with the configuration.
        """
        return self.mapper_class(configuration)

    def validate_configuration(self, config: dict) -> tuple[bool, list[str]]:
        """
        Validate a provider configuration against this provider's config schema.
        
        Checks for required top-level fields declared in the provider's `config_schema` and for required credential fields under `config_schema["credentials"]` when present.
        
        Parameters:
            config (dict): The configuration to validate.
        
        Returns:
            tuple[bool, list[str]]: `True` if the configuration satisfies the schema, `False` otherwise; a list of human-readable error messages for any missing fields.
        """
        errors = []

        # Check required fields from schema
        required_fields = self.config_schema.get("required", [])
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Check credentials structure
        if "credentials" in self.config_schema:
            required_creds = self.config_schema["credentials"].get("required", [])
            credentials = config.get("credentials", {})
            for cred in required_creds:
                if cred not in credentials:
                    errors.append(f"Missing required credential: {cred}")

        return len(errors) == 0, errors


class IntegrationRegistry:
    """Central registry for all integration providers"""

    _providers: dict[str, IntegrationProvider] = {}
    _initialized = False

    @classmethod
    def register(
        cls,
        name: str,
        provider_type: str,
        client_class: Type[BaseIntegrationClient],
        mapper_class: Type[BaseFieldMapper],
        orchestrator_class: Type[BaseSyncOrchestrator],
        display_name: str = "",
        description: str = "",
        config_schema: dict = {},
    ) -> None:
        """
        Register a new integration provider in the central registry.
        
        Parameters:
            name (str): Unique provider identifier (e.g., "jira", "servicenow").
            provider_type (str): Category of provider (e.g., "itsm", "directory", "hr").
            client_class (Type[BaseIntegrationClient]): Implementation class for the integration client.
            mapper_class (Type[BaseFieldMapper]): Implementation class for field mapping.
            orchestrator_class (Type[BaseSyncOrchestrator]): Implementation class for sync orchestration.
            display_name (str): Optional human-readable name; if empty, a default display name will be used.
            description (str): Optional provider description.
            config_schema (dict): Optional configuration schema used to validate provider configurations (may include required fields and credential structure).
        """
        if name in cls._providers:
            logger.warning(f"Provider {name} is already registered. Overwriting.")

        provider = IntegrationProvider(
            name=name,
            provider_type=provider_type,
            client_class=client_class,
            mapper_class=mapper_class,
            orchestrator_class=orchestrator_class,
            display_name=display_name,
            description=description,
            config_schema=config_schema,
        )

        cls._providers[name] = provider
        logger.info(f"Registered integration provider: {name} ({provider_type})")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Remove a registered integration provider by name.
        
        Returns:
            `True` if the provider was unregistered, `False` otherwise.
        """
        if name in cls._providers:
            del cls._providers[name]
            logger.info(f"Unregistered integration provider: {name}")
            return True
        return False

    @classmethod
    def get_provider(cls, name: str) -> Optional[IntegrationProvider]:
        """
        Retrieve the registered integration provider with the given name.
        
        Returns:
            IntegrationProvider | None: The provider instance if registered, `None` otherwise.
        """
        return cls._providers.get(name)

    @classmethod
    def get_providers_by_type(cls, provider_type: str) -> list[IntegrationProvider]:
        """
        Retrieve all registered IntegrationProvider instances with the specified provider type.
        
        Returns:
            list[IntegrationProvider]: Matching providers; empty list if none.
        """
        return [
            provider
            for provider in cls._providers.values()
            if provider.provider_type == provider_type
        ]

    @classmethod
    def list_providers(cls) -> list[IntegrationProvider]:
        """
        Return a list of all registered integration providers.
        
        Returns:
            providers (list[IntegrationProvider]): A list of registered IntegrationProvider instances.
        """
        return list(cls._providers.values())

    @classmethod
    def list_provider_names(cls) -> list[str]:
        """
        Return the names of all registered integration providers.
        
        Returns:
            list[str]: A list of provider names currently registered in the registry.
        """
        return list(cls._providers.keys())

    @classmethod
    def get_orchestrator(
        cls, configuration: "IntegrationConfiguration"
    ) -> BaseSyncOrchestrator:
        """
        Return an orchestrator instance for the given integration configuration.
        
        Parameters:
            configuration (IntegrationConfiguration): Configuration whose provider determines which orchestrator to create; must have a `provider` attribute with a `name`.
        
        Returns:
            BaseSyncOrchestrator: Orchestrator instance created for the provided configuration.
        
        Raises:
            ValueError: If the configuration has no provider or the provider is not registered.
        """
        # Get provider name from configuration
        if hasattr(configuration, "provider"):
            provider_name = configuration.provider.name
        else:
            raise ValueError("Configuration must have a provider")

        provider = cls.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} is not registered")

        return provider.create_orchestrator(configuration)

    @classmethod
    def get_client(
        cls, configuration: IntegrationConfiguration
    ) -> BaseIntegrationClient:
        """
        Obtain a client instance for the integration specified by the configuration.
        
        Parameters:
            configuration (IntegrationConfiguration): Configuration object that must include a `provider` attribute with a `name` identifying the registered provider.
        
        Returns:
            BaseIntegrationClient: A client instance created for the provider in the configuration.
        
        Raises:
            ValueError: If `configuration` has no `provider` attribute or if the referenced provider is not registered.
        """
        if hasattr(configuration, "provider"):
            provider_name = configuration.provider.name
        else:
            raise ValueError("Configuration must have a provider")

        provider = cls.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} is not registered")

        return provider.create_client(configuration)

    @classmethod
    def get_mapper(cls, configuration: IntegrationConfiguration) -> BaseFieldMapper:
        """
        Retrieve a field mapper instance appropriate for the configuration's provider.
        
        Parameters:
        	configuration (IntegrationConfiguration): Integration configuration object that must have a `provider` attribute with a `name` matching a registered provider.
        
        Returns:
        	BaseFieldMapper: A mapper instance created for the configuration's provider.
        
        Raises:
        	ValueError: If the configuration lacks a `provider` attribute or if the specified provider is not registered.
        """
        if hasattr(configuration, "provider"):
            provider_name = configuration.provider.name
        else:
            raise ValueError("Configuration must have a provider")

        provider = cls.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} is not registered")

        return provider.create_mapper(configuration)

    @classmethod
    def validate_configuration(
        cls, provider_name: str, config: dict
    ) -> tuple[bool, list[str]]:
        """
        Validate a configuration dictionary for the named provider.
        
        Parameters:
            provider_name (str): Name of the registered provider to validate against.
            config (dict): Configuration data to validate.
        
        Returns:
            tuple[bool, list[str]]: First element is `True` if the configuration satisfies the provider's config schema, `False` otherwise. Second element is a list of human-readable error messages describing validation failures (empty if valid).
        """
        provider = cls.get_provider(provider_name)
        if not provider:
            return False, [f"Provider {provider_name} is not registered"]

        return provider.validate_configuration(config)

    @classmethod
    def autodiscover(cls) -> None:
        """
        Discover and register available integration modules and mark the registry initialized.
        
        Scans installed Django apps for an `integrations` module and traverses the local `integrations/<type>/<provider>/integration.py` directory structure; imports any found integration modules (which are expected to register themselves with the IntegrationRegistry), records import failures as warnings, and sets the registry's `_initialized` flag to True.
        """
        if cls._initialized:
            return

        from django.apps import apps
        import importlib

        # Look for integration modules in installed apps
        for app_config in apps.get_app_configs():
            # Try to import integrations module from each app
            try:
                module_name = f"{app_config.name}.integrations"
                importlib.import_module(module_name)
                logger.debug(f"Loaded integrations from {module_name}")
            except ImportError:
                # No integrations module in this app
                pass

        # Also try to import from integrations package directly
        try:
            # Import all integration modules
            from pathlib import Path

            integrations_path = Path(__file__).parent

            # Walk through integration directories
            for provider_type_dir in integrations_path.iterdir():
                if not provider_type_dir.is_dir() or provider_type_dir.name.startswith(
                    "_"
                ):
                    continue

                # Look for provider directories
                for provider_dir in provider_type_dir.iterdir():
                    if not provider_dir.is_dir() or provider_dir.name.startswith("_"):
                        continue

                    # Try to import integration.py
                    integration_file = provider_dir / "integration.py"
                    if integration_file.exists():
                        module_path = f"integrations.{provider_type_dir.name}.{provider_dir.name}.integration"
                        try:
                            importlib.import_module(module_path)
                            logger.debug(f"Loaded integration from {module_path}")
                        except ImportError as e:
                            logger.warning(
                                f"Failed to load integration {module_path}: {e}"
                            )
        except Exception as e:
            logger.warning(f"Error during integration autodiscovery: {e}")

        cls._initialized = True
        logger.info(
            f"Integration registry initialized with {len(cls._providers)} providers"
        )

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers (mainly for testing)"""
        cls._providers.clear()
        cls._initialized = False
        logger.info("Integration registry cleared")


# Initialize registry when module is imported
def init_registry():
    """
    Trigger integration provider autodiscovery and registration.
    
    Calls IntegrationRegistry.autodiscover() to import and register available integration providers. Safe to call multiple times.
    """
    IntegrationRegistry.autodiscover()