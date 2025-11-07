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
                updated_count = 0

                if mode == "reset":
                    # Reset all to not_assessed
                    for req_assessment in requirement_assessments:
                        req_assessment.result = (
                            RequirementAssessment.Result.NOT_ASSESSED
                        )
                        req_assessment.save()
                        updated_count += 1
                    action = "reset to not_assessed"

                elif mode == "compliant":
                    # Set all to compliant
                    for req_assessment in requirement_assessments:
                        req_assessment.result = RequirementAssessment.Result.COMPLIANT
                        req_assessment.save()
                        updated_count += 1
                    action = "set to compliant"

                else:  # random
                    # Randomize results
                    for req_assessment in requirement_assessments:
                        random_result = random.choice(result_choices)
                        req_assessment.result = random_result
                        req_assessment.save()
                        updated_count += 1
                        logger.debug(
                            f"Updated RequirementAssessment {req_assessment.id} with result: {random_result}"
                        )
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
