from django.contrib.contenttypes.models import ContentType
import structlog
import uuid
from django.core.management.base import BaseCommand, CommandError

# Import the AppliedControl model from its 'core' app
try:
    from core.models import AppliedControl
except ImportError:
    AppliedControl = None  # We will check this later

from integrations.models import IntegrationConfiguration, SyncMapping

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    """
    Manually creates or updates a SyncMapping to link a local AppliedControl
    to a remote Jira task.
    
    This is useful for associating existing objects that were not created
    via the sync process.
    
    Example:
    python manage.py create_sync_mapping \
        --control-id "a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
        --jira-key "ENG-123" \
        --update
    """

    help = "Manually links a local AppliedControl to a remote Jira issue key."

    def add_arguments(self, parser):
        """
        Register command-line arguments required by the management command.
        
        Parameters:
            parser (argparse.ArgumentParser): The argument parser to which the command-line options are added.
        
        Adds the following CLI options:
            --control-id (UUID): The UUID of the local AppliedControl object to link.
            --jira-key (str): The remote Jira issue key to associate (e.g., "PROJ-123").
            --update (flag): If present, update an existing mapping's remote_id to the provided Jira key.
        """
        parser.add_argument(
            "--control-id",
            type=uuid.UUID,  # Use UUID type for built-in validation
            required=True,
            help="The UUID of the local AppliedControl object.",
        )
        parser.add_argument(
            "--jira-key",
            type=str,
            required=True,
            help="The remote Jira issue key (e.g., 'PROJ-123').",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update the remote_id if a mapping for this control already exists.",
        )

    def handle(self, *args, **options):
        """
        Create or update a SyncMapping that links a local AppliedControl to a remote Jira issue.
        
        This command:
        - Looks up the AppliedControl by the provided `control_id`.
        - Finds the Jira IntegrationConfiguration for the control's folder.
        - If no SyncMapping exists for that control+configuration, creates one pointing to `jira_key`.
        - If a SyncMapping exists and `update` is true, updates the mapping's `remote_id` to `jira_key`, clears any error message, and marks it synced.
        - If a SyncMapping exists and `update` is false, raises a CommandError.
        
        Parameters:
            control_id (uuid.UUID): The UUID of the local AppliedControl to link.
            jira_key (str): The Jira issue key to associate with the local object.
            update (bool): When true, overwrite an existing mapping to point to `jira_key`.
        
        Raises:
            CommandError: If the core AppliedControl model cannot be imported, the specified AppliedControl does not exist,
                          no Jira IntegrationConfiguration exists for the control's folder, or a mapping already exists and
                          `update` was not provided.
        """
        if AppliedControl is None:
            raise CommandError(
                "Could not import 'core.models.AppliedControl'. "
                "Is the 'core' app correctly installed and configured?"
            )

        control_id = options["control_id"]
        jira_key = options["jira_key"]
        provider_name = "jira"

        # 1. Fetch the local AppliedControl
        self.stdout.write(f"Looking for AppliedControl with ID: {control_id}...")
        try:
            control = AppliedControl.objects.get(pk=control_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Found local object: '{control.name}' ({control.id})"
                )
            )
        except AppliedControl.DoesNotExist:
            raise CommandError(f"AppliedControl with ID '{control_id}' does not exist.")

        # 2. Find the 'jira' IntegrationConfiguration for this control's folder
        self.stdout.write(
            f"Looking for '{provider_name}' configuration in folder: '{control.folder.name}'..."
        )
        try:
            config = IntegrationConfiguration.objects.get(
                folder=control.folder, provider__name=provider_name
            )
            self.stdout.write(
                self.style.SUCCESS(f"Found Jira configuration (ID: {config.id}).")
            )
        except IntegrationConfiguration.DoesNotExist:
            raise CommandError(
                f"No active '{provider_name}' integration found for folder {control.folder.id} "
                f"('{control.folder.name}').\nRun 'setup_jira_integration' first for this folder."
            )

        # 3. Create or Update the SyncMapping

        # Get the model's "app.Model" label, e.g., "core.AppliedControl"
        # This is what the orchestrator framework uses to retrieve the model.
        model_label = control._meta.label

        identifying_fields = {
            "configuration": config,
            "content_type": ContentType.objects.get_for_model(control),
            "local_object_id": control.id,
        }

        try:
            # Check if a mapping already exists
            mapping = SyncMapping.objects.get(**identifying_fields)
            created = False
        except SyncMapping.DoesNotExist:
            mapping = None
            created = True

        if created:
            self.stdout.write("No existing mapping found. Creating new one...")
            SyncMapping.objects.create(
                **identifying_fields,
                remote_id=jira_key,
                sync_status=SyncMapping.SyncStatus.SYNCED,
                last_sync_direction=SyncMapping.SyncDirection.PUSH,  # Represents manual link
                remote_data={},  # Start with an empty cache
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully mapped {model_label} {control.id} to Jira task {jira_key}."
                )
            )

        else:
            # Mapping already exists
            if options["update"]:
                if mapping.remote_id == jira_key:
                    self.stdout.write(
                        self.style.NOTICE(
                            f"Mapping already exists and correctly points to {jira_key}. "
                            "No update needed."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Existing mapping points to '{mapping.remote_id}'. "
                            f"Updating to point to '{jira_key}'..."
                        )
                    )
                    mapping.remote_id = jira_key
                    mapping.sync_status = SyncMapping.SyncStatus.SYNCED
                    mapping.error_message = ""  # Clear any old errors
                    mapping.save()
                    self.stdout.write(
                        self.style.SUCCESS("Successfully updated mapping.")
                    )
            else:
                raise CommandError(
                    f"A mapping already exists for this control (points to {mapping.remote_id}).\n"
                    "Use the --update flag to overwrite it."
                )