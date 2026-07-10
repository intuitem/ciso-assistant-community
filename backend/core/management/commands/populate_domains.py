import random
from django.core.management.base import BaseCommand
from core.models import Perimeter
from iam.models import Folder


# Realistic organizational unit names for building a deep hierarchy
TOP_LEVEL_DEPARTMENTS = [
    "Corporate HQ",
    "Information Technology",
    "Finance & Accounting",
    "Human Resources",
    "Operations",
    "Sales & Marketing",
    "Research & Development",
    "Legal & Compliance",
    "Customer Support",
    "Supply Chain",
    "Manufacturing",
    "Quality Assurance",
    "Product Management",
    "Data & Analytics",
    "Security Operations",
    "Infrastructure",
    "Business Development",
    "Facilities Management",
    "Internal Audit",
    "Strategic Planning",
]

SECOND_LEVEL_UNITS = [
    "EMEA Region",
    "North America",
    "APAC Region",
    "LATAM Region",
    "Cloud Services",
    "On-Premise Systems",
    "Network Team",
    "Application Team",
    "DevOps",
    "Platform Engineering",
    "Data Engineering",
    "Machine Learning",
    "Mobile Development",
    "Web Development",
    "QA Automation",
    "Release Management",
    "Service Desk",
    "Incident Management",
    "Change Management",
    "Access Management",
    "Vendor Management",
    "Contract Management",
    "Budget Planning",
    "Payroll",
    "Recruitment",
    "Training & Development",
    "Employee Relations",
    "Benefits Administration",
    "Field Operations",
    "Logistics",
    "Procurement",
    "Warehouse",
    "Fleet Management",
    "Digital Marketing",
    "Brand Management",
    "Partner Relations",
    "Inside Sales",
    "Enterprise Sales",
    "Customer Success",
    "Technical Support",
]

THIRD_LEVEL_TEAMS = [
    "Team Alpha",
    "Team Beta",
    "Team Gamma",
    "Team Delta",
    "Team Epsilon",
    "Core Platform",
    "Integration Hub",
    "Analytics Engine",
    "Monitoring",
    "Automation",
    "Compliance Tooling",
    "Identity Services",
    "API Gateway",
    "Data Pipeline",
    "Reporting",
    "Billing Module",
    "Notification Service",
    "Search Platform",
    "Content Delivery",
    "Edge Computing",
    "Database Administration",
    "Storage Management",
    "Backup & Recovery",
    "Disaster Recovery",
    "Performance Tuning",
    "Capacity Planning",
    "Architecture Review",
    "Security Testing",
    "Penetration Testing",
    "Vulnerability Mgmt",
]

FOURTH_LEVEL_PROJECTS = [
    "Project Phoenix",
    "Project Atlas",
    "Project Mercury",
    "Project Neptune",
    "Project Orion",
    "Project Vega",
    "Project Titan",
    "Project Nova",
    "Project Aurora",
    "Project Zenith",
    "Migration v2",
    "Legacy Modernization",
    "Cloud Migration",
    "Zero Trust Initiative",
    "SOC Enhancement",
    "SIEM Upgrade",
    "IAM Rollout",
    "CMDB Refresh",
    "DR Site Build",
    "PCI Remediation",
]

PERIMETER_NAMES = [
    "Production Environment",
    "Staging Environment",
    "Development Environment",
    "DMZ Network",
    "Internal Network",
    "Cloud AWS",
    "Cloud Azure",
    "Cloud GCP",
    "SaaS Applications",
    "On-Premise Datacenter",
    "Remote Access",
    "IoT Devices",
    "OT/SCADA Network",
    "PCI Zone",
    "Guest WiFi",
    "Corporate WiFi",
    "VPN Gateway",
    "Backup Infrastructure",
    "CI/CD Pipeline",
    "Container Platform",
    "Data Warehouse",
    "Email Gateway",
    "Web Application Firewall",
    "Load Balancer Tier",
    "Database Cluster",
    "File Storage",
    "Monitoring Stack",
    "Log Aggregation",
    "Identity Provider",
    "API Management",
]

LC_STATUSES = ["undefined", "in_design", "in_dev", "in_prod", "eol", "dropped"]

# Prefix used for all test data (for cleanup)
TEST_PREFIX = "TEST-TREE-"


class Command(BaseCommand):
    help = "Populates a deep hierarchy of domains (folders) and perimeters for stress-testing the tree view"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domains",
            type=int,
            default=500,
            help="Approximate number of domains to create (default: 500)",
        )
        parser.add_argument(
            "--max-depth",
            type=int,
            default=4,
            help="Maximum depth of the folder hierarchy (default: 4)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all test domains and perimeters (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        target_domains = options["domains"]
        max_depth = options["max_depth"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self._clean(options)

        # If only clean (not fresh), exit without creating new data
        if clean and not fresh:
            self.stdout.write(
                self.style.SUCCESS("Clean completed. No new data created.")
            )
            return

        root_folder = Folder.get_root_folder()

        # Build the hierarchy
        all_domains = []
        domain_counter = [0]  # mutable counter for closures

        def make_name(depth, label):
            domain_counter[0] += 1
            return f"{TEST_PREFIX}{label} #{domain_counter[0]:04d}"

        def create_children(parent, depth, names_pool, budget):
            """Recursively create child folders, returning how many were created."""
            if depth > max_depth or budget <= 0:
                return 0

            # Decide how many children at this level
            if budget <= 5:
                num_children = budget
            else:
                num_children = min(
                    random.randint(3, max(5, budget // 4)), budget, len(names_pool)
                )

            used_names = random.sample(names_pool, min(num_children, len(names_pool)))
            created = 0
            remaining = budget - num_children  # budget left for grandchildren

            for name_label in used_names[:num_children]:
                folder = Folder.objects.create(
                    name=make_name(depth, name_label),
                    description=f"Test domain at depth {depth}: {name_label}",
                    parent_folder=parent,
                    content_type=Folder.ContentType.DOMAIN,
                )
                all_domains.append((folder, depth))
                created += 1

                # Decide how many children this node gets
                if depth < max_depth and remaining > 0:
                    # Give a portion of the remaining budget to children
                    child_budget = random.randint(0, min(remaining, 15))
                    remaining -= child_budget
                    next_pool = self._get_names_pool(depth + 1)
                    sub_created = create_children(
                        folder, depth + 1, next_pool, child_budget
                    )
                    created += sub_created

                if domain_counter[0] >= target_domains:
                    break

            return created

        self.stdout.write(
            f"Creating ~{target_domains} domains with max depth {max_depth}..."
        )

        # Determine how many top-level domains to create
        num_top = min(len(TOP_LEVEL_DEPARTMENTS), max(8, target_domains // 25))
        top_names = random.sample(TOP_LEVEL_DEPARTMENTS, num_top)
        budget_per_top = target_domains // num_top

        for top_name in top_names:
            if domain_counter[0] >= target_domains:
                break

            folder = Folder.objects.create(
                name=make_name(1, top_name),
                description=f"Top-level test domain: {top_name}",
                parent_folder=root_folder,
                content_type=Folder.ContentType.DOMAIN,
            )
            all_domains.append((folder, 1))

            # Create subtree
            remaining_budget = min(
                budget_per_top + random.randint(-5, 10),
                target_domains - domain_counter[0],
            )
            next_pool = self._get_names_pool(2)
            create_children(folder, 2, next_pool, remaining_budget)

        # If we haven't hit the target, create more top-level domains with children
        while domain_counter[0] < target_domains:
            extra_name = f"Division {domain_counter[0] + 1}"
            folder = Folder.objects.create(
                name=make_name(1, extra_name),
                description=f"Additional test domain: {extra_name}",
                parent_folder=root_folder,
                content_type=Folder.ContentType.DOMAIN,
            )
            all_domains.append((folder, 1))

            remaining = target_domains - domain_counter[0]
            if remaining > 0:
                next_pool = self._get_names_pool(2)
                create_children(folder, 2, next_pool, min(remaining, 10))

        total_domains = domain_counter[0]
        self.stdout.write(self.style.SUCCESS(f"Created {total_domains} domains"))

        # Create perimeters: each domain gets 0-30 random perimeters
        self.stdout.write("Creating perimeters (0-30 per domain)...")
        perimeter_count = 0
        perimeter_global_idx = 0

        for domain, _ in all_domains:
            num_for_domain = random.randint(0, 30)
            for j in range(num_for_domain):
                perimeter_global_idx += 1
                label = random.choice(PERIMETER_NAMES)
                Perimeter.objects.create(
                    name=f"{TEST_PREFIX}{label} #{perimeter_global_idx:04d}",
                    description=f"Test perimeter in {domain.name}",
                    folder=domain,
                    ref_id=f"TEST-PER-{perimeter_global_idx:04d}",
                    lc_status=random.choice(LC_STATUSES),
                )
                perimeter_count += 1

            if perimeter_count % 100 == 0 and perimeter_count > 0:
                self.stdout.write(f"  Created {perimeter_count} perimeters so far...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {perimeter_count} perimeters across {total_domains} domains"
            )
        )

        # Print summary
        self._print_summary(all_domains, max_depth)

    def _get_names_pool(self, depth):
        if depth <= 1:
            return list(TOP_LEVEL_DEPARTMENTS)
        elif depth == 2:
            return list(SECOND_LEVEL_UNITS)
        elif depth == 3:
            return list(THIRD_LEVEL_TEAMS)
        else:
            return list(FOURTH_LEVEL_PROJECTS)

    def _clean(self, options):
        self.stdout.write("Cleaning existing test data...")

        deleted_perimeters = Perimeter.objects.filter(
            name__startswith=TEST_PREFIX
        ).count()
        Perimeter.objects.filter(name__startswith=TEST_PREFIX).delete()

        deleted_folders = Folder.objects.filter(name__startswith=TEST_PREFIX).count()
        Folder.objects.filter(name__startswith=TEST_PREFIX).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleaned {deleted_folders} domains and {deleted_perimeters} perimeters"
            )
        )

    def _print_summary(self, all_domains, max_depth):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        # Count by depth
        depth_counts = {}
        for _, depth in all_domains:
            depth_counts[depth] = depth_counts.get(depth, 0) + 1

        self.stdout.write("\nDomains by depth:")
        for d in sorted(depth_counts.keys()):
            label = {
                1: "Top-level",
                2: "Second-level",
                3: "Third-level",
                4: "Fourth-level",
            }.get(d, f"Depth {d}")
            self.stdout.write(f"  {label} (depth {d}): {depth_counts[d]}")

        total = sum(depth_counts.values())
        self.stdout.write(f"  Total domains: {total}")

        # Perimeters
        per_count = Perimeter.objects.filter(name__startswith=TEST_PREFIX).count()
        self.stdout.write(f"\nPerimeters: {per_count}")

        # Perimeters by lc_status
        self.stdout.write("\nPerimeters by lifecycle status:")
        for status_val, status_label in Perimeter.PRJ_LC_STATUS:
            count = Perimeter.objects.filter(
                lc_status=status_val, name__startswith=TEST_PREFIX
            ).count()
            if count:
                self.stdout.write(f"  {status_label}: {count}")

        self.stdout.write("=" * 60)
