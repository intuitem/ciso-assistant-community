import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Actor, Incident, Terminology
from iam.models import Folder


class Command(BaseCommand):
    help = "Populates random incident data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of incidents to create (default: 50)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST- prefixed incidents (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        num_incidents = options["count"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self.stdout.write("Cleaning existing test data...")
            deleted_incidents = Incident.objects.filter(
                name__startswith="TEST-"
            ).count()
            Incident.objects.filter(name__startswith="TEST-").delete()

            self.stdout.write(
                self.style.SUCCESS(f"Cleaned {deleted_incidents} incidents")
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
        if not actors:
            self.stdout.write(
                self.style.WARNING("No actors found. Incidents will be unassigned.")
            )

        # Get available qualifications
        qualifications = list(
            Terminology.objects.filter(
                field_path=Terminology.FieldPath.QUALIFICATIONS,
                is_visible=True,
            )
        )
        if not qualifications:
            self.stdout.write(
                self.style.WARNING(
                    "No qualifications found. Incidents will have no qualifications."
                )
            )

        # Incident name templates
        incident_types = [
            "Data Breach",
            "Ransomware Attack",
            "Phishing Campaign",
            "DDoS Attack",
            "Unauthorized Access",
            "Malware Infection",
            "Insider Threat",
            "SQL Injection Attack",
            "Account Compromise",
            "System Outage",
            "Data Loss",
            "Social Engineering",
            "Zero-Day Exploit",
            "Brute Force Attack",
            "Man-in-the-Middle Attack",
            "Credential Theft",
            "Business Email Compromise",
            "Cryptojacking",
            "API Abuse",
            "Supply Chain Attack",
        ]

        target_systems = [
            "Production Database",
            "Web Application",
            "Email Server",
            "Cloud Infrastructure",
            "Mobile Application",
            "API Gateway",
            "Authentication System",
            "Payment Processing",
            "File Storage",
            "Customer Portal",
            "Admin Dashboard",
            "Network Infrastructure",
            "VPN Gateway",
            "Remote Desktop",
            "DNS Server",
            "Load Balancer",
            "Backup System",
            "Monitoring Platform",
            "Development Environment",
            "Third-Party Integration",
        ]

        # Get current year date range for reported_at
        current_year = timezone.now().year
        year_start = datetime(
            current_year, 1, 1, tzinfo=timezone.get_current_timezone()
        )
        year_end = datetime(
            current_year, 12, 31, 23, 59, 59, tzinfo=timezone.get_current_timezone()
        )
        total_seconds = int((year_end - year_start).total_seconds())

        # Status and severity choices
        status_choices = [
            Incident.Status.NEW,
            Incident.Status.ONGOING,
            Incident.Status.RESOLVED,
            Incident.Status.CLOSED,
            Incident.Status.DISMISSED,
        ]
        # Weight distribution: more new/ongoing than closed
        status_weights = [0.3, 0.35, 0.2, 0.1, 0.05]

        severity_choices = [
            Incident.Severity.SEV1,
            Incident.Severity.SEV2,
            Incident.Severity.SEV3,
            Incident.Severity.SEV4,
            Incident.Severity.SEV5,
            Incident.Severity.UNDEFINED,
        ]
        # Weight distribution: fewer critical incidents
        severity_weights = [0.1, 0.2, 0.3, 0.25, 0.1, 0.05]

        detection_choices = [
            Incident.Detection.INTERNAL,
            Incident.Detection.EXTERNAL,
        ]

        # Create incidents
        self.stdout.write(f"Creating {num_incidents} test incidents...")
        incidents_created = []

        for i in range(num_incidents):
            # Generate unique incident name
            incident_type = random.choice(incident_types)
            target = random.choice(target_systems)
            name = f"TEST-{incident_type} on {target} #{i + 1}"

            # Generate description
            description = (
                f"This is a test incident created for demonstration purposes. "
                f"Incident involves {incident_type.lower()} affecting {target.lower()}. "
                f"Automatically generated and should be used for testing only."
            )

            # Generate random reported_at timestamp in current year
            random_seconds = random.randint(0, total_seconds)
            reported_at = year_start + timedelta(seconds=random_seconds)

            # Determine status and severity based on weights
            status = random.choices(status_choices, weights=status_weights)[0]
            severity = random.choices(severity_choices, weights=severity_weights)[0]
            detection = random.choice(detection_choices)

            # Create incident
            incident = Incident.objects.create(
                name=name,
                description=description,
                folder=root_folder,
                ref_id=f"TEST-INC-{i + 1:04d}",
                status=status,
                severity=severity,
                detection=detection,
                reported_at=reported_at,
                is_published=True,
            )

            # Randomly assign owners (0-3 actors)
            if actors:
                num_owners = random.randint(0, min(3, len(actors)))
                if num_owners > 0:
                    owners = random.sample(actors, num_owners)
                    incident.owners.set(owners)

            # Randomly assign qualifications (1-4 qualifications)
            if qualifications:
                num_qualifications = random.randint(1, min(4, len(qualifications)))
                selected_qualifications = random.sample(
                    qualifications, num_qualifications
                )
                incident.qualifications.set(selected_qualifications)

            incidents_created.append(incident)

            # Progress indicator
            if (i + 1) % 25 == 0:
                self.stdout.write(f"  Created {i + 1}/{num_incidents} incidents...")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {num_incidents} incidents")
        )

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        self.stdout.write(f"\nTotal Incidents Created: {len(incidents_created)}")

        self.stdout.write(f"\nIncidents by Status:")
        for status_val, status_label in Incident.Status.choices:
            count = Incident.objects.filter(
                status=status_val, name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {status_label}: {count}")

        self.stdout.write(f"\nIncidents by Severity:")
        for severity_val, severity_label in Incident.Severity.choices:
            count = Incident.objects.filter(
                severity=severity_val, name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {severity_label}: {count}")

        self.stdout.write(f"\nIncidents by Detection:")
        for detection_val, detection_label in Incident.Detection.choices:
            count = Incident.objects.filter(
                detection=detection_val, name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {detection_label}: {count}")

        self.stdout.write(f"\nIncidents by Quarter:")
        for quarter in range(1, 5):
            if quarter == 1:
                start_month, end_month = 1, 3
            elif quarter == 2:
                start_month, end_month = 4, 6
            elif quarter == 3:
                start_month, end_month = 7, 9
            else:
                start_month, end_month = 10, 12

            quarter_start = datetime(
                current_year, start_month, 1, tzinfo=timezone.get_current_timezone()
            )
            if end_month == 12:
                quarter_end = datetime(
                    current_year,
                    12,
                    31,
                    23,
                    59,
                    59,
                    tzinfo=timezone.get_current_timezone(),
                )
            else:
                quarter_end = datetime(
                    current_year,
                    end_month + 1,
                    1,
                    tzinfo=timezone.get_current_timezone(),
                ) - timedelta(seconds=1)

            count = Incident.objects.filter(
                name__startswith="TEST-",
                reported_at__gte=quarter_start,
                reported_at__lte=quarter_end,
            ).count()
            self.stdout.write(
                f"  Q{quarter} ({quarter_start.date()} to {quarter_end.date()}): {count}"
            )

        # Show qualification distribution
        if qualifications:
            self.stdout.write(f"\nTop Qualifications Used:")
            for qual in qualifications[:5]:  # Show top 5
                count = Incident.objects.filter(
                    name__startswith="TEST-", qualifications=qual
                ).count()
                self.stdout.write(f"  {qual.name.capitalize()}: {count}")

        self.stdout.write("=" * 60)
