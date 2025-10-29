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
        """Create an orchestrator instance for this provider"""
        return self.orchestrator_class(configuration)

    def create_client(
        self, configuration: IntegrationConfiguration
    ) -> BaseIntegrationClient:
        """Create a client instance for this provider"""
        return self.client_class(configuration)

    def create_mapper(self, configuration: IntegrationConfiguration) -> BaseFieldMapper:
        """Create a mapper instance for this provider"""
        return self.mapper_class(configuration)

    def validate_configuration(self, config: dict) -> tuple[bool, list[str]]:
        """Validate configuration against schema

        Returns:
            (is_valid, list_of_errors)
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
        """Register a new integration provider

        Args:
            name: Unique identifier (e.g., 'jira', 'servicenow')
            provider_type: Category (e.g., 'itsm', 'directory', 'hr')
            client_class: Client implementation class
            mapper_class: Field mapper implementation class
            orchestrator_class: Orchestrator implementation class
            display_name: Human-readable name
            description: Provider description
            config_schema: JSON schema for configuration validation
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
        """Unregister an integration provider

        Returns:
            True if provider was unregistered, False if not found
        """
        if name in cls._providers:
            del cls._providers[name]
            logger.info(f"Unregistered integration provider: {name}")
            return True
        return False

    @classmethod
    def get_provider(cls, name: str) -> Optional[IntegrationProvider]:
        """Get a registered provider by name"""
        return cls._providers.get(name)

    @classmethod
    def get_providers_by_type(cls, provider_type: str) -> list[IntegrationProvider]:
        """Get all providers of a specific type"""
        return [
            provider
            for provider in cls._providers.values()
            if provider.provider_type == provider_type
        ]

    @classmethod
    def list_providers(cls) -> list[IntegrationProvider]:
        """Get all registered providers"""
        return list(cls._providers.values())

    @classmethod
    def list_provider_names(cls) -> list[str]:
        """Get all registered provider names"""
        return list(cls._providers.keys())

    @classmethod
    def get_orchestrator(
        cls, configuration: "IntegrationConfiguration"
    ) -> BaseSyncOrchestrator:
        """Get an orchestrator instance for a configuration

        Args:
            configuration: IntegrationConfiguration instance

        Returns:
            Orchestrator instance

        Raises:
            ValueError: If provider not found
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
        """Get a client instance for a configuration"""
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
        """Get a mapper instance for a configuration"""
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
        """Validate a configuration for a specific provider

        Returns:
            (is_valid, list_of_errors)
        """
        provider = cls.get_provider(provider_name)
        if not provider:
            return False, [f"Provider {provider_name} is not registered"]

        return provider.validate_configuration(config)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers (mainly for testing)"""
        cls._providers.clear()
        cls._initialized = False
        logger.info("Integration registry cleared")
