import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Actor, TaskTemplate, TaskNode
from iam.models import Folder


class Command(BaseCommand):
    help = "Populates random one-time task data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of one-time tasks to create (default: 50)",
        )
        parser.add_argument(
            "--periodic",
            type=int,
            default=20,
            help="Number of periodic tasks to create (default: 20)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST- prefixed tasks (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        num_tasks = options["count"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self.stdout.write("Cleaning existing test data...")
            deleted_nodes = TaskNode.objects.filter(
                task_template__name__startswith="TEST-"
            ).count()
            TaskNode.objects.filter(task_template__name__startswith="TEST-").delete()

            deleted_templates = TaskTemplate.objects.filter(
                name__startswith="TEST-"
            ).count()
            TaskTemplate.objects.filter(name__startswith="TEST-").delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleaned {deleted_nodes} task nodes and {deleted_templates} task templates"
                )
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
                self.style.WARNING("No actors found. Tasks will be unassigned.")
            )

        # Task name templates
        task_name_templates = [
            "Security Review",
            "Compliance Audit",
            "Risk Assessment",
            "Vulnerability Scan",
            "Policy Update",
            "Access Control Review",
            "Incident Response Drill",
            "Backup Verification",
            "Patch Management",
            "Security Training",
            "Network Monitoring",
            "Data Classification",
            "Penetration Testing",
            "Security Architecture Review",
            "Third-Party Assessment",
            "Business Continuity Test",
            "Disaster Recovery Drill",
            "Privacy Impact Assessment",
            "Threat Intelligence Review",
            "Log Analysis",
        ]

        context_suffixes = [
            "Production Environment",
            "Development Infrastructure",
            "Cloud Services",
            "Database Systems",
            "Web Applications",
            "Mobile Platform",
            "API Gateway",
            "Authentication Services",
            "Payment Systems",
            "Customer Data",
            "Internal Networks",
            "Remote Access",
            "Email Services",
            "File Storage",
            "Backup Systems",
            "Monitoring Tools",
            "CI/CD Pipeline",
            "Container Platform",
            "Identity Management",
            "Encryption Systems",
        ]

        # Get current year date range
        current_year = timezone.now().year
        year_start = date(current_year, 1, 1)
        year_end = date(current_year, 12, 31)
        total_days = (year_end - year_start).days

        status_choices = ["pending", "in_progress", "completed", "cancelled"]
        # Weight distribution: more pending and in_progress than completed
        status_weights = [0.4, 0.3, 0.2, 0.1]

        # Create one-time tasks (each task template gets one task node)
        self.stdout.write(f"Creating {num_tasks} test one-time tasks...")
        tasks_created = []

        for i in range(num_tasks):
            # Generate unique task name
            task_type = random.choice(task_name_templates)
            context = random.choice(context_suffixes)
            name = f"TEST-{task_type} - {context} #{i + 1}"

            # Generate description
            description = (
                f"This is a test task created for demonstration purposes. "
                f"This task involves {task_type.lower()} for {context.lower()}. "
                f"Automatically generated and should be used for testing only."
            )

            # Generate random date in current year
            random_days = random.randint(0, total_days)
            due_date = year_start + timedelta(days=random_days)

            # Determine status based on weights
            status = random.choices(status_choices, weights=status_weights)[0]

            # Generate observation for some tasks (30% chance)
            observation = ""
            if random.random() < 0.3:
                observation_templates = [
                    "Task progressing as planned.",
                    "Waiting for dependencies to be resolved.",
                    "Blocked by external team review.",
                    "Completed ahead of schedule.",
                    "Requires additional resources.",
                    "Risk identified and mitigated.",
                    "Stakeholder approval pending.",
                    "Technical challenges encountered.",
                ]
                observation = random.choice(observation_templates)

            # Create task template (non-recurrent)
            template = TaskTemplate.objects.create(
                name=name,
                description=description,
                folder=root_folder,
                ref_id=f"TEST-TASK-{i + 1:04d}",
                is_recurrent=False,
                enabled=True,
            )

            # Randomly assign actors (0-3)
            if actors:
                num_assignees = random.randint(0, min(3, len(actors)))
                if num_assignees > 0:
                    assignees = random.sample(actors, num_assignees)
                    template.assigned_to.set(assignees)

            # Create task node (occurrence)
            node = TaskNode.objects.create(
                task_template=template,
                folder=root_folder,
                due_date=due_date,
                status=status,
                observation=observation,
            )

            tasks_created.append((template, node))

            # Progress indicator
            if (i + 1) % 25 == 0:
                self.stdout.write(f"  Created {i + 1}/{num_tasks} tasks...")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {num_tasks} one-time tasks")
        )

        # Create periodic tasks (recurrent tasks with multiple occurrences)
        num_periodic = options["periodic"]
        self.stdout.write(f"\nCreating {num_periodic} test periodic tasks...")
        periodic_tasks_created = []

        # Frequency options with their configurations
        frequency_configs = [
            {
                "frequency": "DAILY",
                "interval": 1,
                "days_interval": 1,
            },
            {
                "frequency": "WEEKLY",
                "interval": 1,
                "days_of_week": [1, 3, 5],  # Monday, Wednesday, Friday
                "days_interval": 7,
            },
            {
                "frequency": "WEEKLY",
                "interval": 2,
                "days_of_week": [2],  # Every other Tuesday
                "days_interval": 14,
            },
            {
                "frequency": "MONTHLY",
                "interval": 1,
                "days_interval": 30,  # Approximate for scheduling
            },
            {
                "frequency": "MONTHLY",
                "interval": 3,
                "days_interval": 90,  # Quarterly
            },
            {
                "frequency": "YEARLY",
                "interval": 1,
                "months_of_year": [1, 7],  # January and July
                "days_interval": 180,
            },
        ]

        for i in range(num_periodic):
            # Generate unique task name
            task_type = random.choice(task_name_templates)
            context = random.choice(context_suffixes)
            name = f"TEST-{task_type} - {context} (Periodic #{i + 1})"

            # Generate description
            description = (
                f"This is a periodic test task created for demonstration purposes. "
                f"This task involves recurring {task_type.lower()} for {context.lower()}. "
                f"Automatically generated and should be used for testing only."
            )

            # Select a random frequency configuration
            config = random.choice(frequency_configs)

            # Build schedule JSON
            schedule = {
                "interval": config["interval"],
                "frequency": config["frequency"],
            }

            # Add optional fields based on frequency type
            if "days_of_week" in config:
                schedule["days_of_week"] = config["days_of_week"]
            if "months_of_year" in config:
                schedule["months_of_year"] = config["months_of_year"]

            # Create task template (recurrent)
            template = TaskTemplate.objects.create(
                name=name,
                description=description,
                folder=root_folder,
                ref_id=f"TEST-PERIODIC-{i + 1:04d}",
                is_recurrent=True,
                enabled=True,
                schedule=schedule,
            )

            # Randomly assign actors (0-3)
            if actors:
                num_assignees = random.randint(0, min(3, len(actors)))
                if num_assignees > 0:
                    assignees = random.sample(actors, num_assignees)
                    template.assigned_to.set(assignees)

            # Generate TaskNode occurrences for the current year
            days_interval = config.get("days_interval", 30)
            current_date = year_start
            nodes_created = 0

            while (
                current_date <= year_end and nodes_created < 50
            ):  # Limit to 50 nodes max
                # Determine status based on weights
                status = random.choices(status_choices, weights=status_weights)[0]

                # Generate observation for some nodes (20% chance)
                observation = ""
                if random.random() < 0.2:
                    observation_templates = [
                        "Task progressing as planned.",
                        "Waiting for dependencies to be resolved.",
                        "Completed ahead of schedule.",
                        "Requires additional resources.",
                        "Risk identified and mitigated.",
                    ]
                    observation = random.choice(observation_templates)

                # Create task node (occurrence)
                node = TaskNode.objects.create(
                    task_template=template,
                    folder=root_folder,
                    due_date=current_date,
                    status=status,
                    observation=observation,
                )

                nodes_created += 1

                # Move to next occurrence based on interval
                current_date = current_date + timedelta(days=days_interval)

            periodic_tasks_created.append((template, nodes_created))

            # Progress indicator
            if (i + 1) % 10 == 0:
                self.stdout.write(f"  Created {i + 1}/{num_periodic} periodic tasks...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {num_periodic} periodic tasks with "
                f"{sum(count for _, count in periodic_tasks_created)} total occurrences"
            )
        )

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        total_templates = len(tasks_created) + len(periodic_tasks_created)
        total_nodes = len(tasks_created) + sum(
            count for _, count in periodic_tasks_created
        )

        self.stdout.write(f"\nTotal Task Templates Created: {total_templates}")
        self.stdout.write(f"  - One-time tasks: {len(tasks_created)}")
        self.stdout.write(f"  - Periodic tasks: {len(periodic_tasks_created)}")
        self.stdout.write(f"\nTotal Task Nodes (occurrences): {total_nodes}")

        self.stdout.write(f"\nTask Nodes by Status:")
        for status_val, status_label in TaskNode.TASK_STATUS_CHOICES:
            count = TaskNode.objects.filter(
                status=status_val, task_template__name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {status_label}: {count}")

        self.stdout.write(f"\nTask Nodes by Quarter:")
        for quarter in range(1, 5):
            if quarter == 1:
                start_month, end_month = 1, 3
            elif quarter == 2:
                start_month, end_month = 4, 6
            elif quarter == 3:
                start_month, end_month = 7, 9
            else:
                start_month, end_month = 10, 12

            quarter_start = date(current_year, start_month, 1)
            if end_month == 12:
                quarter_end = date(current_year, 12, 31)
            else:
                quarter_end = date(current_year, end_month + 1, 1) - timedelta(days=1)

            count = TaskNode.objects.filter(
                task_template__name__startswith="TEST-",
                due_date__gte=quarter_start,
                due_date__lte=quarter_end,
            ).count()
            self.stdout.write(
                f"  Q{quarter} ({quarter_start} to {quarter_end}): {count}"
            )

        # Show frequency breakdown for periodic tasks
        self.stdout.write(f"\nPeriodic Tasks by Frequency:")
        for freq in ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]:
            count = TaskTemplate.objects.filter(
                name__startswith="TEST-",
                is_recurrent=True,
                schedule__frequency=freq,
            ).count()
            if count > 0:
                self.stdout.write(f"  {freq}: {count}")

        self.stdout.write("=" * 60)
