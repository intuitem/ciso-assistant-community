import random
from django.core.management.base import BaseCommand
from core.models import Actor, Asset
from iam.models import Folder

PREFIX = "TEST-"


class Command(BaseCommand):
    help = "Populates random asset data with parent-child hierarchy for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Total number of assets to create (default: 100)",
        )
        parser.add_argument(
            "--depth",
            type=int,
            default=4,
            help="Maximum depth of the asset hierarchy (default: 4)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all test assets (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        count = options["count"]
        max_depth = options["depth"]
        clean = options["clean"]
        fresh = options["fresh"]

        if clean or fresh:
            self.stdout.write("Cleaning existing test assets...")
            deleted_count = Asset.objects.filter(name__startswith=PREFIX).count()
            Asset.objects.filter(name__startswith=PREFIX).delete()
            self.stdout.write(
                self.style.SUCCESS(f"Cleaned {deleted_count} test assets")
            )

        if clean and not fresh:
            self.stdout.write(
                self.style.SUCCESS("Clean completed. No new data created.")
            )
            return

        root_folder = Folder.get_root_folder()
        actors = list(Actor.objects.filter(user__is_active=True)[:10])

        # --- name pools --------------------------------------------------
        primary_names = [
            "Customer Data Management",
            "Financial Reporting",
            "Order Processing",
            "Human Resources Records",
            "Product Catalog",
            "Intellectual Property Store",
            "Supply Chain Management",
            "Client Relationship Management",
            "Regulatory Compliance Records",
            "Research & Development Data",
            "Marketing Analytics",
            "Payroll Processing",
            "Inventory Management",
            "Contract Management",
            "Patient Records",
            "Student Information System",
            "Insurance Claims Processing",
            "Trading Platform",
            "Content Management",
            "Business Intelligence",
        ]

        support_names_by_depth = {
            1: [
                "Application Server",
                "Database Server",
                "Web Application",
                "API Gateway",
                "Message Broker",
                "Load Balancer",
                "Identity Provider",
                "Data Warehouse",
                "ERP System",
                "CRM Platform",
                "Email Server",
                "File Storage Service",
                "CI/CD Pipeline",
                "Monitoring Platform",
                "Backup System",
            ],
            2: [
                "Virtual Machine",
                "Container Cluster",
                "Storage Array",
                "Network Switch",
                "Firewall",
                "VPN Concentrator",
                "DNS Server",
                "Reverse Proxy",
                "Cache Server",
                "Log Aggregator",
                "Certificate Manager",
                "Secrets Vault",
                "Object Storage",
                "Block Storage",
                "Queue Service",
            ],
            3: [
                "Physical Server",
                "Rack Unit",
                "UPS System",
                "Network Cable Plant",
                "HVAC System",
                "Power Distribution Unit",
                "KVM Switch",
                "Tape Library",
                "SAN Fabric",
                "Core Router",
                "Edge Switch",
                "Access Point",
                "Physical Security System",
                "Environmental Sensor",
                "Generator",
            ],
            4: [
                "Data Center",
                "Server Room",
                "Colocation Facility",
                "Telecommunications Room",
                "Network Closet",
                "Cloud Region",
                "Availability Zone",
                "Building",
                "Campus",
                "Remote Site",
            ],
        }

        security_objective_levels = [0, 1, 2, 3, 4]
        security_objective_weights = [5, 15, 40, 30, 10]

        def random_security_objectives():
            return {
                "objectives": {
                    obj: {
                        "value": random.choices(
                            security_objective_levels,
                            weights=security_objective_weights,
                        )[0],
                        "is_enabled": True,
                    }
                    for obj in Asset.DEFAULT_SECURITY_OBJECTIVES
                }
            }

        def random_disaster_recovery_objectives():
            return {
                "objectives": {
                    "rto": {"value": random.choice([0, 1, 2, 3, 4])},
                    "rpo": {"value": random.choice([0, 1, 2, 3, 4])},
                    "mtd": {"value": random.choice([0, 1, 2, 3, 4])},
                }
            }

        # --- distribute assets across depth levels -----------------------
        # ~20% primary (depth 0), rest distributed across support depths
        num_primary = max(2, int(count * 0.2))
        num_support = count - num_primary

        # Distribute support assets with more at shallow depth
        depth_weights = [max_depth - d for d in range(max_depth)]
        total_weight = sum(depth_weights)
        assets_per_depth = {}
        remaining = num_support
        for d in range(max_depth):
            if d == max_depth - 1:
                assets_per_depth[d + 1] = remaining
            else:
                n = max(1, int(num_support * depth_weights[d] / total_weight))
                assets_per_depth[d + 1] = min(n, remaining)
                remaining -= assets_per_depth[d + 1]

        self.stdout.write(
            f"Creating {count} assets: {num_primary} primary + {num_support} support "
            f"(max depth {max_depth})"
        )
        self.stdout.write(f"  Depth 0 (primary): {num_primary}")
        for d in range(1, max_depth + 1):
            self.stdout.write(f"  Depth {d} (support): {assets_per_depth[d]}")

        # --- create primary assets (depth 0) -----------------------------
        assets_by_depth = {0: []}
        created = 0

        for i in range(num_primary):
            name_base = primary_names[i % len(primary_names)]
            suffix = (
                f" #{i // len(primary_names) + 1}" if i >= len(primary_names) else ""
            )
            asset = Asset.objects.create(
                name=f"{PREFIX}{name_base}{suffix}",
                description=f"Test primary asset for {name_base.lower()}.",
                folder=root_folder,
                type=Asset.Type.PRIMARY,
                business_value=random.choice(["Critical", "High", "Medium", "Low", ""]),
                ref_id=f"TEST-AST-{created + 1:04d}",
                security_objectives=random_security_objectives(),
                disaster_recovery_objectives=random_disaster_recovery_objectives(),
            )
            if actors:
                asset.owner.set(
                    random.sample(actors, k=random.randint(0, min(3, len(actors))))
                )
            assets_by_depth[0].append(asset)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"  Created {num_primary} primary assets"))

        # --- create support assets at each depth -------------------------
        for depth in range(1, max_depth + 1):
            n = assets_per_depth[depth]
            names_pool = support_names_by_depth.get(
                depth, support_names_by_depth[max(support_names_by_depth.keys())]
            )
            parent_pool = assets_by_depth[depth - 1]
            assets_by_depth[depth] = []

            for i in range(n):
                name_base = names_pool[i % len(names_pool)]
                suffix = f" #{i // len(names_pool) + 1}" if i >= len(names_pool) else ""

                asset = Asset.objects.create(
                    name=f"{PREFIX}{name_base}{suffix}",
                    description=f"Test support asset ({name_base.lower()}) at depth {depth}.",
                    folder=root_folder,
                    type=Asset.Type.SUPPORT,
                    business_value=random.choice(["High", "Medium", "Low", ""]),
                    ref_id=f"TEST-AST-{created + 1:04d}",
                    security_objectives=random_security_objectives(),
                    disaster_recovery_objectives=random_disaster_recovery_objectives(),
                )

                # Link to 1-3 parents from the level above
                num_parents = random.randint(1, min(3, len(parent_pool)))
                parents = random.sample(parent_pool, k=num_parents)
                asset.parent_assets.set(parents)

                if actors:
                    asset.owner.set(
                        random.sample(actors, k=random.randint(0, min(2, len(actors))))
                    )

                assets_by_depth[depth].append(asset)
                created += 1

                if created % 25 == 0:
                    self.stdout.write(f"  Created {created}/{count} assets...")

            self.stdout.write(
                self.style.SUCCESS(f"  Created {n} support assets at depth {depth}")
            )

        # --- summary ------------------------------------------------------
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        total_primary = Asset.objects.filter(
            name__startswith=PREFIX, type=Asset.Type.PRIMARY
        ).count()
        total_support = Asset.objects.filter(
            name__startswith=PREFIX, type=Asset.Type.SUPPORT
        ).count()
        self.stdout.write(f"  Primary assets: {total_primary}")
        self.stdout.write(f"  Support assets: {total_support}")
        self.stdout.write(f"  Total:          {total_primary + total_support}")

        self.stdout.write("\nHierarchy sample (first 5 primary chains):")
        primaries = Asset.objects.filter(
            name__startswith=PREFIX, type=Asset.Type.PRIMARY
        )[:5]
        for p in primaries:
            self._print_tree(p, indent=2)

        self.stdout.write("=" * 60)

    def _print_tree(self, asset, indent=0):
        prefix = " " * indent
        type_label = "PRI" if asset.type == Asset.Type.PRIMARY else "SUP"
        children_count = asset.child_assets.filter(name__startswith=PREFIX).count()
        self.stdout.write(
            f"{prefix}- [{type_label}] {asset.name} ({children_count} children)"
        )
        for child in asset.child_assets.filter(name__startswith=PREFIX)[:3]:
            self._print_tree(child, indent + 4)
        remaining = children_count - 3
        if remaining > 0:
            self.stdout.write(f"{' ' * (indent + 4)}  ... and {remaining} more")
