import structlog
from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string

# Assuming 'Folder' model exists in an 'iam' app as implied by FolderMixin
# If this import is incorrect, please adjust it to your project structure.
try:
    from iam.models import Folder
except ImportError:
    print(
        "Warning: Could not import 'iam.models.Folder'. "
        "The command will fail if the --folder-id argument is used."
    )
    Folder = None

from integrations.base import BaseIntegrationClient
from integrations.models import IntegrationConfiguration, IntegrationProvider
from integrations.registry import IntegrationRegistry, init_registry

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    """
    Manages a Jira IntegrationConfiguration instance.
    
    This command creates or updates an IntegrationConfiguration for Jira
    for a specific folder and then tests the connection.
    
    Example:
    python manage.py setup_jira_integration \
        --folder-id "your-folder-uuid" \
        --server-url "https://your-company.atlassian.net" \
        --email "your-service-account@example.com" \
        --api-token "your-api-token" \
        --project-key "PROJ" \
        --issue-type "Task"
    """

    help = (
        "Creates or updates a Jira integration configuration and tests the connection."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder-id",
            type=str,
            required=True,
            help="The UUID of the Folder to associate this integration with.",
        )
        parser.add_argument(
            "--server-url",
            type=str,
            required=True,
            help="The base URL of the Jira server (e.g., https://my-company.atlassian.net).",
        )
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="The email address used for Jira authentication.",
        )
        parser.add_argument(
            "--api-token",
            type=str,
            required=True,
            help="The Jira API token for the service account.",
        )
        parser.add_argument(
            "--project-key",
            type=str,
            required=True,
            help="The default Jira Project Key (e.g., 'PROJ').",
        )
        parser.add_argument(
            "--issue-type",
            type=str,
            default="Task",
            help="The default Jira Issue Type (e.g., 'Task', 'Bug').",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update the existing configuration for this folder if it exists.",
        )

    def handle(self, *args, **options):
        # 1. Ensure registry is initialized
        self.stdout.write("Initializing integration registry...")
        init_registry()

        provider_name = "jira"

        # Check if the Jira provider code is even registered
        if not IntegrationRegistry.get_provider(provider_name):
            raise CommandError(
                f"The '{provider_name}' provider is not registered in the IntegrationRegistry. "
                "Make sure the Jira integration module (e.g., integrations.itsm.jira.integration) "
                "is being loaded and calls IntegrationRegistry.register()."
            )

        # 2. Get or create the IntegrationProvider DB entry
        self.stdout.write(f"Looking for '{provider_name}' integration provider...")
        provider, provider_created = IntegrationProvider.objects.get_or_create(
            name=provider_name,
            defaults={"provider_type": IntegrationProvider.ProviderType.ITSM},
        )
        if provider_created:
            self.stdout.write(
                self.style.SUCCESS(f"Created '{provider_name}' provider DB entry.")
            )

        # 3. Get the Folder
        if Folder is None:
            raise CommandError("iam.models.Folder could not be imported. Aborting.")

        folder_id = options["folder_id"]
        try:
            folder = Folder.objects.get(pk=folder_id)
            self.stdout.write(f"Found folder: {folder.name} (ID: {folder.id})")
        except Folder.DoesNotExist:
            raise CommandError(f"Folder with ID '{folder_id}' does not exist.")

        # 4. Prepare credentials and settings
        credentials = {
            "server_url": options["server_url"],
            "email": options["email"],
            "api_token": options["api_token"],
        }
        settings = {
            "project_key": options["project_key"],
            "issue_type": options["issue_type"],
            "field_mappings": {
                # Add any default field mappings here if desired
                # "local_field": "remote_jira_field"
            },
        }

        # 5. Create or update the IntegrationConfiguration
        defaults = {
            "credentials": credentials,
            "settings": settings,
            "is_active": True,
            # Generate a secret if creating
            "webhook_secret": get_random_string(50),
        }

        try:
            if options["update"]:
                self.stdout.write(
                    f"Updating configuration for folder '{folder.name}'..."
                )
                config, created = IntegrationConfiguration.objects.update_or_create(
                    provider=provider, folder=folder, defaults=defaults
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "No existing config found. Created a new Jira configuration."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Successfully updated existing Jira configuration."
                        )
                    )
            else:
                self.stdout.write(
                    f"Creating new configuration for folder '{folder.name}'..."
                )
                config = IntegrationConfiguration.objects.create(
                    provider=provider, folder=folder, **defaults
                )
                self.stdout.write(
                    self.style.SUCCESS("Successfully created new Jira configuration.")
                )

        except Exception as e:
            raise CommandError(
                f"Failed to create/update configuration. An integration for this "
                f"provider and folder might already exist. Use --update. Error: {e}"
            )

        # 6. Test the connection
        self.stdout.write(self.style.NOTICE("\nTesting connection to Jira..."))
        try:
            # Get the specific client (e.g., JiraClient) via the registry
            client: BaseIntegrationClient = IntegrationRegistry.get_client(config)

            # Call the test_connection method
            is_connected = client.test_connection()

            if is_connected:
                self.stdout.write(self.style.SUCCESS("Connection test successful! ✅"))
            else:
                # This case assumes test_connection() returns False on auth errors
                self.stdout.write(
                    self.style.WARNING(
                        "Connection test failed. The credentials are likely incorrect."
                    )
                )

        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to import client. Is the JiraClient implementation missing? Error: {e}"
                )
            )
        except NotImplementedError:
            self.stdout.write(
                self.style.ERROR(
                    "The 'test_connection' method is not implemented in the JiraClient. "
                    "Cannot test the connection."
                )
            )
        except Exception as e:
            # This case catches network errors, timeouts, or exceptions raised by the client
            self.stdout.write(
                self.style.ERROR(f"Connection test raised an exception: {e}")
            )
            logger.error("Jira connection test failed", exc_info=True)
            self.stdout.write(
                self.style.WARNING(
                    "Connection test failed. Check server URL, network access, and API token permissions."
                )
            )
