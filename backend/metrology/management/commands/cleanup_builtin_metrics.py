"""
Management command to cleanup BuiltinMetricSample history.

This command provides options to:
- Delete samples older than the retention period
- Delete all samples for a specific model type
- Delete orphaned samples (where the target object no longer exists)
- Regenerate all samples with fresh data

Usage:
    python manage.py cleanup_builtin_metrics --apply-retention    # Delete old samples based on retention setting
    python manage.py cleanup_builtin_metrics --delete-orphans     # Delete samples for deleted objects
    python manage.py cleanup_builtin_metrics --model RiskAssessment --purge  # Delete all samples for a model
    python manage.py cleanup_builtin_metrics --model RiskAssessment --regenerate  # Purge and regenerate
    python manage.py cleanup_builtin_metrics --dry-run            # Preview without making changes
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from core.models import (
    ComplianceAssessment,
    RiskAssessment,
    FindingsAssessment,
)
from iam.models import Folder
from metrology.models import BuiltinMetricSample, get_builtin_metrics_retention_days


class Command(BaseCommand):
    help = "Cleanup BuiltinMetricSample history"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply-retention",
            action="store_true",
            help="Delete samples older than the configured retention period",
        )
        parser.add_argument(
            "--delete-orphans",
            action="store_true",
            help="Delete samples where the target object no longer exists",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Delete all samples (use with --model to target a specific model)",
        )
        parser.add_argument(
            "--regenerate",
            action="store_true",
            help="Regenerate today's snapshots after cleanup (use with --purge)",
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
        parser.add_argument(
            "--older-than-days",
            type=int,
            help="Custom retention period in days (overrides global setting)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        model_filter = options.get("model")
        apply_retention = options["apply_retention"]
        delete_orphans = options["delete_orphans"]
        purge = options["purge"]
        regenerate = options["regenerate"]
        older_than_days = options.get("older_than_days")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Show current stats
        self.show_stats(model_filter)

        total_deleted = 0

        # Apply retention policy
        if apply_retention:
            deleted = self.apply_retention(dry_run, model_filter, older_than_days)
            total_deleted += deleted

        # Delete orphaned samples
        if delete_orphans:
            deleted = self.delete_orphans(dry_run, model_filter)
            total_deleted += deleted

        # Purge all samples
        if purge:
            deleted = self.purge_samples(dry_run, model_filter)
            total_deleted += deleted

        # Regenerate snapshots
        if regenerate:
            self.regenerate_snapshots(dry_run, model_filter)

        if total_deleted > 0 or regenerate:
            self.stdout.write("")
            self.show_stats(model_filter)

        self.stdout.write(self.style.SUCCESS("Cleanup completed!"))

    def show_stats(self, model_filter):
        """Show current statistics."""
        self.stdout.write("\nCurrent statistics:")

        models = [
            "complianceassessment",
            "riskassessment",
            "findingsassessment",
            "folder",
        ]

        if model_filter:
            models = [model_filter.lower()]

        for model_name in models:
            try:
                ct = ContentType.objects.get(model=model_name)
                count = BuiltinMetricSample.objects.filter(content_type=ct).count()
                oldest = (
                    BuiltinMetricSample.objects.filter(content_type=ct)
                    .order_by("date")
                    .first()
                )
                newest = (
                    BuiltinMetricSample.objects.filter(content_type=ct)
                    .order_by("-date")
                    .first()
                )

                date_range = ""
                if oldest and newest:
                    date_range = f" ({oldest.date} to {newest.date})"

                self.stdout.write(f"  {model_name}: {count} samples{date_range}")
            except ContentType.DoesNotExist:
                pass

        total = BuiltinMetricSample.objects.count()
        self.stdout.write(f"  Total: {total} samples")

    def apply_retention(self, dry_run, model_filter, custom_days=None):
        """Delete samples older than the retention period."""
        if custom_days is not None:
            retention_days = max(1, custom_days)
        else:
            retention_days = get_builtin_metrics_retention_days()

        cutoff_date = date.today() - timedelta(days=retention_days)

        self.stdout.write(
            f"\nApplying retention policy ({retention_days} days, cutoff: {cutoff_date})..."
        )

        queryset = BuiltinMetricSample.objects.filter(date__lt=cutoff_date)

        if model_filter:
            try:
                ct = ContentType.objects.get(model=model_filter.lower())
                queryset = queryset.filter(content_type=ct)
            except ContentType.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"  ContentType not found for {model_filter}")
                )
                return 0

        count = queryset.count()

        if count == 0:
            self.stdout.write("  No samples to delete")
            return 0

        if dry_run:
            self.stdout.write(f"  Would delete {count} samples")
        else:
            queryset.delete()
            self.stdout.write(self.style.SUCCESS(f"  Deleted {count} samples"))

        return count

    def delete_orphans(self, dry_run, model_filter):
        """Delete samples where the target object no longer exists."""
        self.stdout.write("\nDeleting orphaned samples...")

        model_classes = {
            "complianceassessment": ComplianceAssessment,
            "riskassessment": RiskAssessment,
            "findingsassessment": FindingsAssessment,
            "folder": Folder,
        }

        if model_filter:
            model_classes = {model_filter.lower(): model_classes[model_filter.lower()]}

        total_deleted = 0

        for model_name, model_class in model_classes.items():
            try:
                ct = ContentType.objects.get(model=model_name)
            except ContentType.DoesNotExist:
                continue

            # Get all object IDs that have samples
            sample_object_ids = set(
                BuiltinMetricSample.objects.filter(content_type=ct).values_list(
                    "object_id", flat=True
                )
            )

            # Get all existing object IDs
            existing_ids = set(model_class.objects.values_list("id", flat=True))

            # Find orphaned IDs
            orphaned_ids = sample_object_ids - existing_ids

            if not orphaned_ids:
                self.stdout.write(f"  {model_name}: no orphans found")
                continue

            # Delete orphaned samples
            queryset = BuiltinMetricSample.objects.filter(
                content_type=ct, object_id__in=orphaned_ids
            )
            count = queryset.count()

            if dry_run:
                self.stdout.write(
                    f"  {model_name}: would delete {count} samples for {len(orphaned_ids)} deleted objects"
                )
            else:
                queryset.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {model_name}: deleted {count} samples for {len(orphaned_ids)} deleted objects"
                    )
                )

            total_deleted += count

        return total_deleted

    def purge_samples(self, dry_run, model_filter):
        """Delete all samples (optionally for a specific model)."""
        self.stdout.write("\nPurging samples...")

        if model_filter:
            try:
                ct = ContentType.objects.get(model=model_filter.lower())
                queryset = BuiltinMetricSample.objects.filter(content_type=ct)
            except ContentType.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"  ContentType not found for {model_filter}")
                )
                return 0
        else:
            queryset = BuiltinMetricSample.objects.all()

        count = queryset.count()

        if count == 0:
            self.stdout.write("  No samples to delete")
            return 0

        if dry_run:
            self.stdout.write(f"  Would delete {count} samples")
        else:
            queryset.delete()
            self.stdout.write(self.style.SUCCESS(f"  Deleted {count} samples"))

        return count

    def regenerate_snapshots(self, dry_run, model_filter):
        """Regenerate today's snapshots for all objects."""
        self.stdout.write("\nRegenerating today's snapshots...")

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

        for model_name, model_class in models_to_process:
            # For Folder, only process domain folders
            if model_name == "Folder":
                objects = model_class.objects.filter(content_type="DO")
            else:
                objects = model_class.objects.all()

            count = objects.count()

            if count == 0:
                self.stdout.write(f"  {model_name}: no objects to process")
                continue

            if dry_run:
                self.stdout.write(f"  {model_name}: would create {count} snapshots")
                total_created += count
                continue

            created = 0
            for obj in objects:
                BuiltinMetricSample.update_or_create_snapshot(obj, date=today)
                created += 1

            self.stdout.write(
                self.style.SUCCESS(f"  {model_name}: created {created} snapshots")
            )
            total_created += created

        return total_created
