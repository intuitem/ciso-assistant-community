import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import (
    Actor,
    FindingsAssessment,
    Finding,
    Severity,
    AppliedControl,
    ReferenceControl,
    Vulnerability,
    Perimeter,
)
from iam.models import Folder


class Command(BaseCommand):
    help = "Populates random findings assessments and findings data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of findings assessments to create (default: 10)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST- prefixed findings data (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        num_assessments = options["count"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self.stdout.write("Cleaning existing test data...")

            deleted_assessments = FindingsAssessment.objects.filter(
                name__startswith="TEST-"
            ).count()
            deleted_findings = Finding.objects.filter(name__startswith="TEST-").count()
            deleted_perimeters = Perimeter.objects.filter(
                name__startswith="TEST-"
            ).count()

            FindingsAssessment.objects.filter(name__startswith="TEST-").delete()
            Finding.objects.filter(name__startswith="TEST-").delete()
            Perimeter.objects.filter(name__startswith="TEST-").delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleaned {deleted_assessments} findings assessments, "
                    f"{deleted_findings} findings, "
                    f"{deleted_perimeters} perimeters, "
                    f"and all associated data"
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

        # Get actors (users, teams, entities) for assignment
        actors = list(Actor.objects.filter(user__is_active=True)[:10])
        if not actors:
            self.stdout.write(
                self.style.WARNING(
                    "No actors found. Skipping owner/author assignments."
                )
            )

        # Get or create a test perimeter
        perimeter, created = Perimeter.objects.get_or_create(
            name="TEST-Default Perimeter",
            defaults={
                "description": "Default perimeter for test findings assessments",
                "folder": root_folder,
                "ref_id": "TEST-PER-001",
                "lc_status": "in_prod",
            },
        )
        if created:
            self.stdout.write("Created default test perimeter")

        # Get applied controls for linking
        applied_controls = list(AppliedControl.objects.all()[:50])
        reference_controls = list(ReferenceControl.objects.all()[:50])
        vulnerabilities = list(Vulnerability.objects.all()[:50])

        # Assessment templates by category
        assessment_templates = {
            "pentest": [
                "Web Application Penetration Test",
                "Network Infrastructure Pentest",
                "Mobile Application Security Assessment",
                "API Security Testing",
                "Wireless Network Penetration Test",
                "Cloud Infrastructure Security Assessment",
                "IoT Device Security Testing",
                "Red Team Engagement",
            ],
            "audit": [
                "ISO 27001 Internal Audit",
                "SOC 2 Type II Audit",
                "PCI DSS Compliance Audit",
                "GDPR Compliance Audit",
                "HIPAA Security Audit",
                "Access Control Audit",
                "Configuration Management Audit",
                "Third-Party Security Audit",
            ],
            "self_identified": [
                "Quarterly Security Review",
                "Code Review Findings",
                "Vulnerability Scan Analysis",
                "Security Posture Assessment",
                "Risk Assessment Review",
                "Configuration Baseline Review",
                "Security Monitoring Review",
                "Incident Post-Mortem Analysis",
            ],
        }

        # Finding templates by assessment category
        finding_templates = {
            "pentest": [
                "SQL Injection vulnerability in login form",
                "Cross-Site Scripting (XSS) in user profile",
                "Insecure Direct Object Reference in API",
                "Broken authentication mechanism",
                "Sensitive data exposure in API responses",
                "Missing security headers",
                "Weak password policy implementation",
                "Session fixation vulnerability",
                "CSRF token validation bypass",
                "Server-side request forgery (SSRF)",
                "XML External Entity (XXE) injection",
                "Insufficient input validation",
                "Privilege escalation vulnerability",
                "Hardcoded credentials in source code",
                "Outdated software components with known vulnerabilities",
            ],
            "audit": [
                "Insufficient access control documentation",
                "Missing encryption for data at rest",
                "Incomplete asset inventory",
                "Lack of security awareness training records",
                "Inadequate incident response procedures",
                "Missing multi-factor authentication",
                "Insufficient log retention policy",
                "Incomplete business continuity plan",
                "Missing data classification policy",
                "Inadequate vendor risk assessment",
                "Insufficient change management controls",
                "Missing security baselines",
                "Incomplete vulnerability management process",
                "Inadequate physical security controls",
                "Missing data backup verification",
            ],
            "self_identified": [
                "Deprecated TLS version in use",
                "Unused administrative accounts",
                "Missing security patches on production servers",
                "Excessive user permissions identified",
                "Unencrypted database backup files",
                "Weak cipher suites enabled",
                "Missing endpoint protection on workstations",
                "Incomplete security logging",
                "Overly permissive firewall rules",
                "Insufficient monitoring coverage",
                "Missing file integrity monitoring",
                "Inadequate network segmentation",
                "Weak encryption algorithm in use",
                "Missing security updates for third-party libraries",
                "Insecure default configurations",
            ],
        }

        # Status distribution weights
        status_choices = [
            Finding.Status.IDENTIFIED,
            Finding.Status.CONFIRMED,
            Finding.Status.ASSIGNED,
            Finding.Status.IN_PROGRESS,
            Finding.Status.MITIGATED,
            Finding.Status.RESOLVED,
            Finding.Status.CLOSED,
            Finding.Status.DISMISSED,
        ]
        status_weights = [0.15, 0.15, 0.15, 0.20, 0.15, 0.10, 0.05, 0.05]

        # Severity distribution weights
        severity_choices = [
            Severity.INFO,
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
            Severity.CRITICAL,
        ]
        severity_weights = [0.10, 0.25, 0.35, 0.20, 0.10]

        # Create findings assessments
        self.stdout.write(f"Creating {num_assessments} test findings assessments...")
        assessments_created = []

        for i in range(num_assessments):
            # Select category
            category = random.choice(
                [
                    FindingsAssessment.Category.PENTEST,
                    FindingsAssessment.Category.AUDIT,
                    FindingsAssessment.Category.SELF_IDENTIFIED,
                ]
            )

            # Generate assessment name
            category_key = category.lower()
            activity = random.choice(assessment_templates[category_key])
            name = f"TEST-{activity} #{i + 1}"

            # Generate dates
            due_date = timezone.now().date() + timedelta(days=random.randint(14, 60))
            eta = (
                timezone.now().date() + timedelta(days=random.randint(7, 30))
                if random.random() < 0.6
                else None
            )

            # Determine status
            status = random.choice(
                [
                    FindingsAssessment.Status.PLANNED,
                    FindingsAssessment.Status.IN_PROGRESS,
                    FindingsAssessment.Status.IN_REVIEW,
                    FindingsAssessment.Status.DONE,
                ]
            )

            # Create assessment
            assessment = FindingsAssessment.objects.create(
                name=name,
                description=f"Test findings assessment for {activity.lower()}. "
                f"This is automatically generated test data for demonstration purposes.",
                perimeter=perimeter,
                ref_id=f"TEST-FA-{i + 1:04d}",
                category=category,
                due_date=due_date,
                eta=eta,
                status=status,
                version="1.0" if category_key == "audit" else "",
            )

            # Assign authors (1-2)
            if actors:
                num_authors = random.randint(1, min(2, len(actors)))
                assessment.authors.set(random.sample(actors, num_authors))

            assessments_created.append((assessment, category_key))

            # Progress indicator
            if (i + 1) % 5 == 0:
                self.stdout.write(f"  Created {i + 1}/{num_assessments} assessments...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {num_assessments} findings assessments"
            )
        )

        # Create findings for each assessment
        total_findings = 0
        self.stdout.write("\nCreating findings for each assessment...")

        for assessment, category_key in assessments_created:
            # Create 3-12 findings per assessment
            num_findings = random.randint(3, 12)

            for j in range(num_findings):
                # Select finding template
                finding_title = random.choice(finding_templates[category_key])
                name = f"TEST-{finding_title}"

                # Generate severity and status
                severity = random.choices(severity_choices, weights=severity_weights)[0]
                status = random.choices(status_choices, weights=status_weights)[0]

                # Generate dates based on severity
                due_date = timezone.now().date() + timedelta(
                    days=random.randint(14, 45)
                    if severity >= Severity.HIGH
                    else random.randint(30, 90)
                )
                eta = (
                    timezone.now().date() + timedelta(days=random.randint(7, 30))
                    if status in [Finding.Status.ASSIGNED, Finding.Status.IN_PROGRESS]
                    else None
                )

                # Create finding
                finding = Finding.objects.create(
                    name=name,
                    description=f"Test finding: {finding_title}. "
                    f"This is a test record created for demonstration purposes. "
                    f"Found during {assessment.name}.",
                    folder=root_folder,
                    findings_assessment=assessment,
                    ref_id=f"TEST-F-{assessment.id}-{j + 1:03d}",
                    severity=severity,
                    status=status,
                    due_date=due_date,
                    eta=eta,
                )

                # Assign owners (0-2)
                if actors:
                    num_owners = random.randint(0, min(2, len(actors)))
                    if num_owners > 0:
                        finding.owner.set(random.sample(actors, num_owners))

                # Link to controls (0-3 applied controls)
                if applied_controls:
                    num_controls = random.randint(0, min(3, len(applied_controls)))
                    if num_controls > 0:
                        finding.applied_controls.set(
                            random.sample(applied_controls, num_controls)
                        )

                # Link to reference controls (0-2)
                if reference_controls:
                    num_ref_controls = random.randint(
                        0, min(2, len(reference_controls))
                    )
                    if num_ref_controls > 0:
                        finding.reference_controls.set(
                            random.sample(reference_controls, num_ref_controls)
                        )

                # Link to vulnerabilities (0-2) for pentests
                if category_key == "pentest" and vulnerabilities:
                    num_vulns = random.randint(0, min(2, len(vulnerabilities)))
                    if num_vulns > 0:
                        finding.vulnerabilities.set(
                            random.sample(vulnerabilities, num_vulns)
                        )

                total_findings += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {total_findings} findings")
        )

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        self.stdout.write(
            f"\nTotal Findings Assessments Created: {len(assessments_created)}"
        )

        self.stdout.write(f"\nAssessments by Category:")
        for category_val, category_label in FindingsAssessment.Category.choices:
            count = FindingsAssessment.objects.filter(
                name__startswith="TEST-", category=category_val
            ).count()
            if count > 0:
                self.stdout.write(f"  {category_label}: {count}")

        self.stdout.write(f"\nTotal Findings Created: {total_findings}")

        self.stdout.write(f"\nFindings by Severity:")
        for severity_val, severity_label in Severity.choices:
            count = Finding.objects.filter(
                name__startswith="TEST-", severity=severity_val
            ).count()
            if count > 0:
                self.stdout.write(f"  {severity_label}: {count}")

        self.stdout.write(f"\nFindings by Status:")
        for status_val, status_label in Finding.Status.choices:
            count = Finding.objects.filter(
                name__startswith="TEST-", status=status_val
            ).count()
            if count > 0:
                self.stdout.write(f"  {status_label}: {count}")

        # Critical statistics
        critical_unresolved = (
            Finding.objects.filter(name__startswith="TEST-", severity=Severity.CRITICAL)
            .exclude(
                status__in=[
                    Finding.Status.MITIGATED,
                    Finding.Status.RESOLVED,
                    Finding.Status.CLOSED,
                ]
            )
            .count()
        )
        high_unresolved = (
            Finding.objects.filter(name__startswith="TEST-", severity=Severity.HIGH)
            .exclude(
                status__in=[
                    Finding.Status.MITIGATED,
                    Finding.Status.RESOLVED,
                    Finding.Status.CLOSED,
                ]
            )
            .count()
        )

        self.stdout.write(f"\nUnresolved Important Findings:")
        self.stdout.write(f"  Critical: {critical_unresolved}")
        self.stdout.write(f"  High: {high_unresolved}")

        self.stdout.write("=" * 60)
