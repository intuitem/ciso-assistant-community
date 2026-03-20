import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from core.models import Actor, AppliedControl
from iam.models import Folder

PREFIX = "TEST-"


class Command(BaseCommand):
    help = "Populates random applied control data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of applied controls to create (default: 100)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST- prefixed applied controls (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        count = options["count"]
        clean = options["clean"]
        fresh = options["fresh"]

        if clean or fresh:
            self.stdout.write("Cleaning existing test applied controls...")
            deleted_count = AppliedControl.objects.filter(
                name__startswith=PREFIX
            ).count()
            AppliedControl.objects.filter(name__startswith=PREFIX).delete()
            self.stdout.write(
                self.style.SUCCESS(f"Cleaned {deleted_count} test applied controls")
            )

        if clean and not fresh:
            self.stdout.write(
                self.style.SUCCESS("Clean completed. No new data created.")
            )
            return

        root_folder = Folder.get_root_folder()
        actors = list(Actor.objects.filter(user__is_active=True)[:10])
        if not actors:
            self.stdout.write(
                self.style.WARNING(
                    "No actors found. Applied controls will be unassigned."
                )
            )

        # --- name pools ---
        control_names = [
            "Access Control Policy",
            "Password Management",
            "Multi-Factor Authentication",
            "Network Segmentation",
            "Firewall Configuration",
            "Intrusion Detection System",
            "Data Encryption at Rest",
            "Data Encryption in Transit",
            "Vulnerability Scanning",
            "Patch Management Process",
            "Security Awareness Training",
            "Incident Response Plan",
            "Backup and Recovery Procedure",
            "Change Management Process",
            "Physical Access Control",
            "Endpoint Protection",
            "Log Monitoring and Review",
            "Secure Software Development",
            "Third-Party Risk Assessment",
            "Business Continuity Plan",
            "Disaster Recovery Plan",
            "Data Classification Policy",
            "Acceptable Use Policy",
            "Mobile Device Management",
            "Cloud Security Configuration",
            "API Security Gateway",
            "Identity Governance",
            "Privileged Access Management",
            "Data Loss Prevention",
            "Security Information and Event Management",
        ]

        context_suffixes = [
            "Production Systems",
            "Cloud Infrastructure",
            "Corporate Network",
            "Remote Workers",
            "Customer Portal",
            "Internal Applications",
            "Database Systems",
            "Development Environment",
            "Payment Processing",
            "Healthcare Records",
            "IoT Devices",
            "Mobile Applications",
            "Email Systems",
            "File Sharing Platform",
            "SaaS Applications",
        ]

        category_choices = ["policy", "process", "technical", "physical", "procedure"]
        category_weights = [25, 25, 30, 10, 10]

        csf_function_choices = [
            "govern",
            "identify",
            "protect",
            "detect",
            "respond",
            "recover",
        ]
        csf_function_weights = [10, 15, 30, 20, 15, 10]

        status_choices = [
            "to_do",
            "in_progress",
            "on_hold",
            "active",
            "deprecated",
            "--",
        ]
        status_weights = [15, 20, 10, 35, 10, 10]

        effort_choices = ["XS", "S", "M", "L", "XL"]
        effort_weights = [10, 25, 35, 20, 10]

        currencies = ["USD", "EUR", "GBP", "CHF"]

        observation_templates = [
            "Control operating as expected.",
            "Pending review by security team.",
            "Needs additional resources for full implementation.",
            "Partially implemented, awaiting infrastructure changes.",
            "Successfully tested during last audit.",
            "Requires update to align with new regulation.",
            "Dependent on vendor support contract renewal.",
            "Documentation needs to be updated.",
            "Training materials being developed.",
            "Effectiveness verified through penetration testing.",
        ]

        # --- date helpers ---
        current_year = date.today().year
        year_start = date(current_year, 1, 1)
        year_end = date(current_year, 12, 31)
        total_days = (year_end - year_start).days

        self.stdout.write(f"Creating {count} test applied controls...")
        created = 0

        for i in range(count):
            control_name = random.choice(control_names)
            context = random.choice(context_suffixes)
            name = f"{PREFIX}{control_name} - {context} #{i + 1}"

            description = (
                f"Test applied control for {control_name.lower()} "
                f"covering {context.lower()}. "
                f"Automatically generated for testing purposes."
            )

            category = random.choices(category_choices, weights=category_weights)[0]
            csf_function = random.choices(
                csf_function_choices, weights=csf_function_weights
            )[0]
            status = random.choices(status_choices, weights=status_weights)[0]
            priority = random.choice([1, 2, 3, 4, None])
            effort = random.choices(
                [None] + effort_choices, weights=[15] + effort_weights
            )[0]
            control_impact = random.choice([None, 1, 2, 3, 4, 5])
            progress = random.randint(0, 100) if status != "--" else 0

            # Dates
            start_offset = random.randint(0, total_days)
            start_date = year_start + timedelta(days=start_offset)
            eta = start_date + timedelta(days=random.randint(30, 365))
            expiry_date = (
                eta + timedelta(days=random.randint(180, 730))
                if random.random() < 0.4
                else None
            )

            # Cost (70% chance of having cost data)
            cost = None
            if random.random() < 0.7:
                currency = random.choice(currencies)
                cost = {
                    "currency": currency,
                    "amortization_period": random.choice([1, 2, 3, 5]),
                    "build": {
                        "fixed_cost": round(random.uniform(1000, 100000), 2),
                        "people_days": round(random.uniform(1, 120), 1),
                    },
                    "run": {
                        "fixed_cost": round(random.uniform(500, 50000), 2),
                        "people_days": round(random.uniform(1, 60), 1),
                    },
                }

            # Observation (30% chance)
            observation = (
                random.choice(observation_templates) if random.random() < 0.3 else ""
            )

            # Link (20% chance)
            link = (
                f"https://jira.example.com/browse/SEC-{random.randint(1000, 9999)}"
                if random.random() < 0.2
                else None
            )

            ac = AppliedControl.objects.create(
                name=name,
                description=description,
                folder=root_folder,
                ref_id=f"TEST-AC-{i + 1:04d}",
                category=category,
                csf_function=csf_function,
                status=status,
                priority=priority,
                effort=effort,
                control_impact=control_impact,
                progress_field=progress,
                start_date=start_date,
                eta=eta,
                expiry_date=expiry_date,
                cost=cost,
                observation=observation,
                link=link,
            )

            # Assign owners (0-3)
            if actors:
                num_owners = random.randint(0, min(3, len(actors)))
                if num_owners > 0:
                    ac.owner.set(random.sample(actors, num_owners))

            created += 1
            if created % 25 == 0:
                self.stdout.write(f"  Created {created}/{count} applied controls...")

        self.stdout.write(
            self.style.SUCCESS(f"\nSuccessfully created {count} test applied controls")
        )

        # --- summary ---
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        self.stdout.write(
            f"\nTotal: {AppliedControl.objects.filter(name__startswith=PREFIX).count()}"
        )

        self.stdout.write("\nBy Status:")
        for val, label in AppliedControl.Status.choices:
            c = AppliedControl.objects.filter(
                name__startswith=PREFIX, status=val
            ).count()
            if c:
                self.stdout.write(f"  {label}: {c}")

        self.stdout.write("\nBy Category:")
        for val, label in AppliedControl.CATEGORY:
            c = AppliedControl.objects.filter(
                name__startswith=PREFIX, category=val
            ).count()
            if c:
                self.stdout.write(f"  {label}: {c}")

        self.stdout.write("\nBy CSF Function:")
        for val, label in AppliedControl.CSF_FUNCTION:
            c = AppliedControl.objects.filter(
                name__startswith=PREFIX, csf_function=val
            ).count()
            if c:
                self.stdout.write(f"  {label}: {c}")

        self.stdout.write("\nBy Effort:")
        for val, label in AppliedControl.EFFORT:
            c = AppliedControl.objects.filter(
                name__startswith=PREFIX, effort=val
            ).count()
            if c:
                self.stdout.write(f"  {label}: {c}")

        self.stdout.write("=" * 60)
