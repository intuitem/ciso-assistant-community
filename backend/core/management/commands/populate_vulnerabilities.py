import random
from django.core.management.base import BaseCommand
from core.models import Vulnerability, Severity
from iam.models import Folder


class Command(BaseCommand):
    help = "Populates random vulnerability data across domains for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domains",
            type=int,
            default=10,
            help="Number of domains to create (default: 10)",
        )
        parser.add_argument(
            "--vulns",
            type=int,
            default=2000,
            help="Number of vulnerabilities to create (default: 2000)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all test vulnerabilities and domains (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        num_domains = options["domains"]
        num_vulns = options["vulns"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self.stdout.write("Cleaning existing test data...")
            # Deleting folders will cascade delete vulnerabilities due to foreign key
            deleted_vulns = Vulnerability.objects.filter(
                name__startswith="[TEST]"
            ).count()
            Vulnerability.objects.filter(name__startswith="[TEST]").delete()
            deleted_folders = Folder.objects.filter(
                name__startswith="Test Domain"
            ).count()
            Folder.objects.filter(name__startswith="Test Domain").delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleaned {deleted_vulns} vulnerabilities and {deleted_folders} domains"
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

        # Get or create domains
        existing_domains = list(
            Folder.objects.filter(name__startswith="Test Domain ").order_by("name")
        )

        if existing_domains:
            self.stdout.write(f"Found {len(existing_domains)} existing test domains")

        domains = []

        # Reuse existing domains first
        if len(existing_domains) >= num_domains:
            # We have enough existing domains, use the first N
            domains = existing_domains[:num_domains]
            self.stdout.write(
                self.style.SUCCESS(f"Using {num_domains} existing test domains")
            )
        else:
            # Use all existing domains and create more
            domains = existing_domains.copy()
            domains_to_create = num_domains - len(existing_domains)

            if existing_domains:
                self.stdout.write(f"Using {len(existing_domains)} existing domains")

            if domains_to_create > 0:
                self.stdout.write(
                    f"Creating {domains_to_create} additional test domains..."
                )

                # Get the next available domain number
                start_number = len(existing_domains) + 1

                for i in range(domains_to_create):
                    domain_name = f"Test Domain {start_number + i}"
                    domain = Folder.objects.create(
                        name=domain_name,
                        description=f"Automatically generated test domain {start_number + i}",
                        parent_folder=root_folder,
                        content_type=Folder.ContentType.DOMAIN,
                    )
                    domains.append(domain)

                self.stdout.write(
                    self.style.SUCCESS(f"Created {domains_to_create} new domains")
                )

        # Vulnerability name templates
        vuln_templates = [
            "SQL Injection in {} module",
            "Cross-Site Scripting (XSS) in {}",
            "Authentication Bypass in {}",
            "Remote Code Execution in {}",
            "Path Traversal in {}",
            "Insecure Direct Object Reference in {}",
            "XML External Entity (XXE) in {}",
            "Server-Side Request Forgery in {}",
            "Broken Access Control in {}",
            "Security Misconfiguration in {}",
            "Sensitive Data Exposure in {}",
            "Missing Authentication in {}",
            "Insufficient Logging in {}",
            "Weak Cryptography in {}",
            "Buffer Overflow in {}",
            "Command Injection in {}",
            "LDAP Injection in {}",
            "Clickjacking in {}",
            "Session Fixation in {}",
            "Insecure Deserialization in {}",
        ]

        module_names = [
            "Login System",
            "User Management",
            "Payment Gateway",
            "API Endpoint",
            "File Upload",
            "Search Function",
            "Admin Panel",
            "Dashboard",
            "Reporting Module",
            "Data Export",
            "Configuration Panel",
            "Email Service",
            "Authentication Service",
            "Database Layer",
            "Web Interface",
            "Mobile API",
            "Third-party Integration",
            "Content Management",
            "Notification System",
            "Backup Service",
        ]

        # Severity choices (using the actual model values)
        severity_choices = [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
            Severity.INFO,
            Severity.UNDEFINED,
        ]

        # Status choices (using the actual model values)
        status_choices = [
            Vulnerability.Status.POTENTIAL,
            Vulnerability.Status.EXPLOITABLE,
            Vulnerability.Status.MITIGATED,
            Vulnerability.Status.FIXED,
            Vulnerability.Status.NOTEXPLOITABLE,
            Vulnerability.Status.UNAFFECTED,
            Vulnerability.Status.UNDEFINED,
        ]

        # Create vulnerabilities
        self.stdout.write(f"Creating {num_vulns} test vulnerabilities...")
        vulnerabilities = []

        for i in range(num_vulns):
            # Randomly select domain
            domain = random.choice(domains)

            # Generate vulnerability name with unique ID
            template = random.choice(vuln_templates)
            module = random.choice(module_names)
            name = f"[TEST] {template.format(module)} #{i + 1}"

            # Generate description
            description = (
                f"This is a test vulnerability created for demonstration purposes. "
            )
            description += (
                f"Severity: {random.choice(['Critical', 'High', 'Medium', 'Low'])}. "
            )
            description += f"This vulnerability was automatically generated and should be used for testing only."

            # Create vulnerability
            vuln = Vulnerability.objects.create(
                name=name,
                description=description,
                folder=domain,
                severity=random.choice(severity_choices),
                status=random.choice(status_choices),
                ref_id=f"TEST-VULN-{i + 1:04d}",
            )
            vulnerabilities.append(vuln)

            # Progress indicator
            if (i + 1) % 100 == 0:
                self.stdout.write(f"  Created {i + 1}/{num_vulns} vulnerabilities...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {num_vulns} vulnerabilities across {num_domains} domains"
            )
        )

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        for domain in domains:
            count = Vulnerability.objects.filter(folder=domain).count()
            self.stdout.write(f"  {domain.name}: {count} vulnerabilities")

        self.stdout.write("\nBy Severity:")
        for severity_val, severity_label in Severity.choices:
            count = Vulnerability.objects.filter(
                severity=severity_val, name__startswith="[TEST]"
            ).count()
            self.stdout.write(f"  {severity_label.capitalize()}: {count}")

        self.stdout.write("\nBy Status:")
        for status_val, status_label in Vulnerability.Status.choices:
            count = Vulnerability.objects.filter(
                status=status_val, name__startswith="[TEST]"
            ).count()
            self.stdout.write(f"  {status_label}: {count}")

        self.stdout.write("=" * 60)
