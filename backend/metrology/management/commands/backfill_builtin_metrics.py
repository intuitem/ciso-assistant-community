"""
Management command to backfill BuiltinMetricSample data from HistoricalMetric.

This command migrates existing historical metric data to the new BuiltinMetricSample model
and optionally generates current snapshots for all supported objects.

Usage:
    python manage.py backfill_builtin_metrics
    python manage.py backfill_builtin_metrics --skip-historical  # Only generate today's snapshots
    python manage.py backfill_builtin_metrics --dry-run  # Preview without making changes
"""

from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from core.models import (
    HistoricalMetric,
    ComplianceAssessment,
    RiskAssessment,
    FindingsAssessment,
)
from iam.models import Folder
from metrology.models import BuiltinMetricSample


class Command(BaseCommand):
    help = "Backfill BuiltinMetricSample data from HistoricalMetric and generate current snapshots"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-historical",
            action="store_true",
            help="Skip migrating historical data, only generate today's snapshots",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be done without making changes",
        )
        parser.add_argument(
            "--model",
            type=str,
            choices=[
                "ComplianceAssessment",
                "RiskAssessment",
                "FindingsAssessment",
                "Folder",
            ],
            help="Only process a specific model type",
        )

    def handle(self, *args, **options):
        skip_historical = options["skip_historical"]
        dry_run = options["dry_run"]
        model_filter = options.get("model")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Step 1: Migrate historical data
        if not skip_historical:
            self.migrate_historical_data(dry_run, model_filter)

        # Step 2: Generate current snapshots
        self.generate_current_snapshots(dry_run, model_filter)

        self.stdout.write(self.style.SUCCESS("Backfill completed!"))

    def migrate_historical_data(self, dry_run, model_filter):
        """Migrate data from HistoricalMetric to BuiltinMetricSample."""
        self.stdout.write("Migrating historical data from HistoricalMetric...")

        # Map model names to their transform functions
        model_transforms = {
            "ComplianceAssessment": self._transform_compliance_assessment_metrics,
            "RiskAssessment": self._transform_risk_assessment_metrics,
        }

        if model_filter:
            if model_filter in model_transforms:
                model_transforms = {model_filter: model_transforms[model_filter]}
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"No historical data migration for {model_filter}"
                    )
                )
                return

        total_migrated = 0
        total_skipped = 0

        for model_name, transform_func in model_transforms.items():
            historical_metrics = HistoricalMetric.objects.filter(model=model_name)
            count = historical_metrics.count()

            if count == 0:
                self.stdout.write(f"  No historical data for {model_name}")
                continue

            self.stdout.write(f"  Processing {count} {model_name} records...")

            try:
                content_type = ContentType.objects.get(model=model_name.lower())
            except ContentType.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"  ContentType not found for {model_name}")
                )
                continue

            for hm in historical_metrics:
                # Check if already exists
                exists = BuiltinMetricSample.objects.filter(
                    content_type=content_type,
                    object_id=hm.object_id,
                    date=hm.date,
                ).exists()

                if exists:
                    total_skipped += 1
                    continue

                # Transform the metrics data
                metrics = transform_func(hm.data)

                if not dry_run:
                    BuiltinMetricSample.objects.create(
                        content_type=content_type,
                        object_id=hm.object_id,
                        date=hm.date,
                        metrics=metrics,
                    )

                total_migrated += 1

        self.stdout.write(
            f"  Migrated: {total_migrated}, Skipped (already exists): {total_skipped}"
        )

    def _transform_compliance_assessment_metrics(self, data):
        """Transform HistoricalMetric data to BuiltinMetricSample format for ComplianceAssessment."""
        reqs = data.get("reqs", {})
        return {
            "progress": reqs.get("progress_perc"),
            "score": reqs.get("score"),
            "total_requirements": reqs.get("total"),
            "status_breakdown": reqs.get("per_status", {}),
            "result_breakdown": reqs.get("per_result", {}),
        }

    def _transform_risk_assessment_metrics(self, data):
        """Transform HistoricalMetric data to BuiltinMetricSample format for RiskAssessment."""
        scenarios = data.get("scenarios", {})
        return {
            "total_scenarios": scenarios.get("total"),
            "treatment_breakdown": scenarios.get("per_treatment", {}),
            # These weren't tracked in HistoricalMetric, will be empty
            "current_level_breakdown": {},
            "residual_level_breakdown": {},
        }

    def generate_current_snapshots(self, dry_run, model_filter):
        """Generate current snapshots for all supported objects."""
        self.stdout.write("Generating current snapshots...")

        models_to_process = [
            ("ComplianceAssessment", ComplianceAssessment),
            ("RiskAssessment", RiskAssessment),
            ("FindingsAssessment", FindingsAssessment),
            ("Folder", Folder),
        ]

        if model_filter:
            models_to_process = [
                (name, cls) for name, cls in models_to_process if name == model_filter
            ]

        today = date.today()
        total_created = 0
        total_updated = 0

        for model_name, model_class in models_to_process:
            objects = model_class.objects.all()
            count = objects.count()

            if count == 0:
                self.stdout.write(f"  No {model_name} objects to process")
                continue

            self.stdout.write(f"  Processing {count} {model_name} objects...")

            for obj in objects:
                if dry_run:
                    total_created += 1
                    continue

                sample, created = BuiltinMetricSample.update_or_create_snapshot(
                    obj, date=today
                )

                if created:
                    total_created += 1
                else:
                    total_updated += 1

        self.stdout.write(f"  Created: {total_created}, Updated: {total_updated}")
