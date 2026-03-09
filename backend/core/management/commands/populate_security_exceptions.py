import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Actor, SecurityException, Severity
from iam.models import Folder, User


class Command(BaseCommand):
    help = "Populates random security exception data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=30,
            help="Number of security exceptions to create (default: 30)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST- prefixed security exceptions (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        num_exceptions = options["count"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self.stdout.write("Cleaning existing test data...")
            deleted_exceptions = SecurityException.objects.filter(
                name__startswith="TEST-"
            ).count()
            SecurityException.objects.filter(name__startswith="TEST-").delete()

            self.stdout.write(
                self.style.SUCCESS(f"Cleaned {deleted_exceptions} security exceptions")
            )

        # If only clean (not fresh), exit without creating new data
        if clean and not fresh:
            self.stdout.write(
                self.style.SUCCESS("Clean completed. No new data created.")
            )
            return

        # Get root folder
        root_folder = Folder.get_root_folder()

        # Get actors for random assignment (limit to reasonable number)
        actors = list(Actor.objects.filter(user__is_active=True)[:10])
        # Also get users for the approver FK (which is still a User FK)
        users = list(User.objects.filter(is_active=True)[:10])
        if not actors:
            self.stdout.write(
                self.style.WARNING(
                    "No actors found. Security exceptions will be unassigned."
                )
            )

        # Security exception reason templates
        exception_reasons = [
            "Legacy System",
            "Technical Limitation",
            "Business Requirement",
            "Third-Party Dependency",
            "Cost Constraint",
            "Resource Limitation",
            "Operational Necessity",
            "Vendor Limitation",
            "Compliance Waiver",
            "Temporary Configuration",
            "Development Environment",
            "Testing Infrastructure",
            "Migration in Progress",
            "Architectural Constraint",
            "Performance Optimization",
            "Compatibility Issue",
            "Emergency Access",
            "Maintenance Window",
            "Integration Requirement",
            "Platform Limitation",
        ]

        control_areas = [
            "Authentication",
            "Authorization",
            "Encryption",
            "Network Segmentation",
            "Logging and Monitoring",
            "Patch Management",
            "Access Control",
            "Data Protection",
            "Backup and Recovery",
            "Vulnerability Management",
            "Password Policy",
            "Multi-Factor Authentication",
            "Firewall Rules",
            "API Security",
            "Database Security",
            "Cloud Security",
            "Endpoint Protection",
            "Security Training",
            "Incident Response",
            "Change Management",
        ]

        # Get current date for expiration calculations
        today = timezone.now().date()
        current_year = today.year

        # Status choices
        status_choices = [
            SecurityException.Status.DRAFT,
            SecurityException.Status.IN_REVIEW,
            SecurityException.Status.APPROVED,
            SecurityException.Status.RESOLVED,
            SecurityException.Status.EXPIRED,
            SecurityException.Status.DEPRECATED,
        ]
        # Weight distribution: more draft/in_review/approved than resolved
        status_weights = [0.25, 0.25, 0.30, 0.1, 0.05, 0.05]

        # Severity choices
        severity_choices = [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
            Severity.INFO,
            Severity.UNDEFINED,
        ]
        # Weight distribution: fewer critical exceptions
        severity_weights = [0.05, 0.15, 0.35, 0.3, 0.1, 0.05]

        # Create security exceptions
        self.stdout.write(f"Creating {num_exceptions} test security exceptions...")
        exceptions_created = []

        for i in range(num_exceptions):
            # Generate unique exception name
            reason = random.choice(exception_reasons)
            control_area = random.choice(control_areas)
            name = f"TEST-{reason} for {control_area} #{i + 1}"

            # Generate description
            description = (
                f"This is a test security exception created for demonstration purposes. "
                f"Exception granted for {control_area.lower()} due to {reason.lower()}. "
                f"This exception should be reviewed and updated according to organizational policy. "
                f"Automatically generated and should be used for testing only."
            )

            # Determine status and severity based on weights
            status = random.choices(status_choices, weights=status_weights)[0]
            severity = random.choices(severity_choices, weights=severity_weights)[0]

            # Generate expiration date (between 30 days and 2 years from today)
            # Note: Model validation requires dates to be in the future
            expiration_date = None
            if status == SecurityException.Status.EXPIRED:
                # For expired exceptions, set date in near future (1-7 days)
                # to simulate exceptions that need urgent attention
                days_until_expiration = random.randint(1, 7)
                expiration_date = today + timedelta(days=days_until_expiration)
            elif status not in [SecurityException.Status.DEPRECATED]:
                # For active exceptions, set date between 30 days and 2 years
                days_until_expiration = random.randint(30, 730)
                expiration_date = today + timedelta(days=days_until_expiration)

            # Select approver (if approved or resolved)
            approver = None
            if (
                status
                in [
                    SecurityException.Status.APPROVED,
                    SecurityException.Status.RESOLVED,
                ]
                and users
            ):
                approver = random.choice(users)

            # Create security exception
            exception = SecurityException.objects.create(
                name=name,
                description=description,
                folder=root_folder,
                ref_id=f"TEST-SEC-EXC-{i + 1:04d}",
                status=status,
                severity=severity,
                expiration_date=expiration_date,
                approver=approver,
                is_published=True,
            )

            # Randomly assign owners (1-3 actors)
            if actors:
                num_owners = random.randint(1, min(3, len(actors)))
                owners = random.sample(actors, num_owners)
                exception.owners.set(owners)

            exceptions_created.append(exception)

            # Progress indicator
            if (i + 1) % 15 == 0:
                self.stdout.write(f"  Created {i + 1}/{num_exceptions} exceptions...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {num_exceptions} security exceptions"
            )
        )

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        self.stdout.write(
            f"\nTotal Security Exceptions Created: {len(exceptions_created)}"
        )

        self.stdout.write(f"\nExceptions by Status:")
        for status_val, status_label in SecurityException.Status.choices:
            count = SecurityException.objects.filter(
                status=status_val, name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {status_label.capitalize()}: {count}")

        self.stdout.write(f"\nExceptions by Severity:")
        for severity_val, severity_label in Severity.choices:
            count = SecurityException.objects.filter(
                severity=severity_val, name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {severity_label.capitalize()}: {count}")

        # Expiration analysis
        self.stdout.write(f"\nExpiration Analysis:")
        expiring_urgent_count = SecurityException.objects.filter(
            name__startswith="TEST-",
            expiration_date__gte=today,
            expiration_date__lte=today + timedelta(days=7),
        ).count()
        expiring_soon_count = SecurityException.objects.filter(
            name__startswith="TEST-",
            expiration_date__gt=today + timedelta(days=7),
            expiration_date__lte=today + timedelta(days=90),
        ).count()
        long_term_count = SecurityException.objects.filter(
            name__startswith="TEST-",
            expiration_date__gt=today + timedelta(days=90),
        ).count()
        no_expiration_count = SecurityException.objects.filter(
            name__startswith="TEST-",
            expiration_date__isnull=True,
        ).count()

        self.stdout.write(f"  Expiring within 7 days (urgent): {expiring_urgent_count}")
        self.stdout.write(f"  Expiring within 8-90 days: {expiring_soon_count}")
        self.stdout.write(f"  Long-term (>90 days): {long_term_count}")
        self.stdout.write(f"  No expiration date: {no_expiration_count}")

        # Approval analysis
        with_approver_count = SecurityException.objects.filter(
            name__startswith="TEST-",
            approver__isnull=False,
        ).count()
        self.stdout.write(f"\nWith Approver: {with_approver_count}")

        self.stdout.write("=" * 60)
