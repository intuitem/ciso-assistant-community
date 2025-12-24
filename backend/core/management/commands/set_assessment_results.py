from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import uuid
import random
import logging

from core.models import ComplianceAssessment, RequirementAssessment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set results for assessable requirement assessments associated with a compliance assessment UUID"

    def add_arguments(self, parser):
        parser.add_argument(
            "uuid",
            type=str,
            help="UUID of the compliance assessment whose requirement assessments should be updated",
        )
        parser.add_argument(
            "--mode",
            type=str,
            choices=["reset", "compliant", "random"],
            default="random",
            help="Mode: 'reset' (not_assessed), 'compliant' (all compliant), or 'random' (randomize)",
        )

    def handle(self, *args, **options):
        target_uuid = options["uuid"]
        mode = options["mode"]

        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(target_uuid)
        except ValueError:
            raise CommandError(f"Invalid UUID format: {target_uuid}")

        self.stdout.write(
            f"Processing compliance assessment UUID: {target_uuid} with mode: {mode}"
        )

        try:
            compliance_assessment = ComplianceAssessment.objects.get(id=uuid_obj)
            requirement_assessments = RequirementAssessment.objects.filter(
                compliance_assessment=compliance_assessment,
                requirement__assessable=True,
            )

            count = requirement_assessments.count()
            if count == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"No assessable requirement assessments found for compliance assessment {target_uuid}"
                    )
                )
                return

            # Get all available result choices
            result_choices = [
                choice[0] for choice in RequirementAssessment.Result.choices
            ]

            with transaction.atomic():
                if mode == "reset":
                    # Reset all to not_assessed using a single UPDATE query
                    updated_count = requirement_assessments.update(
                        result=RequirementAssessment.Result.NOT_ASSESSED
                    )
                    action = "reset to not_assessed"

                elif mode == "compliant":
                    # Set all to compliant using a single UPDATE query
                    updated_count = requirement_assessments.update(
                        result=RequirementAssessment.Result.COMPLIANT
                    )
                    action = "set to compliant"

                else:  # random
                    # Randomize results using bulk_update
                    assessments_to_update = list(requirement_assessments)
                    for req_assessment in assessments_to_update:
                        req_assessment.result = random.choice(result_choices)
                        logger.debug(
                            f"Will update RequirementAssessment {req_assessment.id} with result: {req_assessment.result}"
                        )
                    RequirementAssessment.objects.bulk_update(
                        assessments_to_update, ["result"], batch_size=1000
                    )
                    updated_count = len(assessments_to_update)
                    action = "randomized"

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully {action} results for {updated_count} requirement assessments"
                )
            )

        except ComplianceAssessment.DoesNotExist:
            raise CommandError(
                f"ComplianceAssessment with UUID {target_uuid} not found"
            ) from None
