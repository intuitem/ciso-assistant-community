from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import uuid
import logging

from core.models import ComplianceAssessment, RequirementAssessment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reset requirements associated with a given UUID"

    def add_arguments(self, parser):
        parser.add_argument(
            "uuid",
            type=str,
            help="UUID of the entity whose requirements should be reset",
        )

    def handle(self, *args, **options):
        target_uuid = options["uuid"]

        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(target_uuid)
        except ValueError:
            raise CommandError(f"Invalid UUID format: {target_uuid}")

        self.stdout.write(f"Processing UUID: {target_uuid}")

        try:
            audit = ComplianceAssessment.objects.get(id=uuid_obj)
            requirements = RequirementAssessment.objects.filter(
                compliance_assessment=audit
            )

            with transaction.atomic():
                requirements.update(result="not_assessed", observation="")

        except (
            ComplianceAssessment.DoesNotExist
        ):  # Replace with your specific model's DoesNotExist
            raise CommandError(f"Object with UUID {target_uuid} not found") from None
