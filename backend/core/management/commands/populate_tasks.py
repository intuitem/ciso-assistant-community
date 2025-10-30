import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import TaskTemplate, TaskNode
from iam.models import Folder, User


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

        # Get active users for random assignment (limit to reasonable number)
        users = list(User.objects.filter(is_active=True)[:10])
        if not users:
            self.stdout.write(
                self.style.WARNING("No active users found. Tasks will be unassigned.")
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

            # Randomly assign users (0-3 users)
            if users:
                num_assignees = random.randint(0, min(3, len(users)))
                if num_assignees > 0:
                    assignees = random.sample(users, num_assignees)
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

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        self.stdout.write(f"\nTotal Tasks Created: {len(tasks_created)}")

        self.stdout.write(f"\nTasks by Status:")
        for status_val, status_label in TaskNode.TASK_STATUS_CHOICES:
            count = TaskNode.objects.filter(
                status=status_val, task_template__name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {status_label}: {count}")

        self.stdout.write(f"\nTasks by Quarter:")
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

        self.stdout.write("=" * 60)
