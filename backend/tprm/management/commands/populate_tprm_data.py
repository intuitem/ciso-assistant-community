import random
from django.core.management.base import BaseCommand
from tprm.models import Entity, Representative, Solution
from core.models import Terminology
from iam.models import Folder


class Command(BaseCommand):
    help = "Populates random TPRM data with entities, solutions, and representatives"

    def add_arguments(self, parser):
        parser.add_argument(
            "--entities",
            type=int,
            default=20,
            help="Number of entities to create (default: 20)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST- prefixed TPRM data (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        num_entities = options["entities"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self.stdout.write("Cleaning existing test data...")

            # Delete representatives first (they reference entities)
            deleted_representatives = Representative.objects.filter(
                email__startswith="test-"
            ).count()
            Representative.objects.filter(email__startswith="test-").delete()

            # Delete solutions (they reference entities)
            deleted_solutions = Solution.objects.filter(
                name__startswith="TEST-"
            ).count()
            Solution.objects.filter(name__startswith="TEST-").delete()

            # Delete entities
            deleted_entities = Entity.objects.filter(name__startswith="TEST-").count()
            Entity.objects.filter(name__startswith="TEST-").delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleaned {deleted_entities} entities, {deleted_solutions} solutions, "
                    f"and {deleted_representatives} representatives"
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

        # Get available entity relationships
        entity_relationships = list(
            Terminology.objects.filter(
                field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                is_visible=True,
            )
        )
        if not entity_relationships:
            self.stdout.write(
                self.style.WARNING(
                    "No entity relationships found. Entities will have no relationships."
                )
            )

        # Entity name templates
        entity_types = [
            "Technology",
            "Consulting",
            "Security",
            "Cloud Services",
            "Software",
            "Analytics",
            "Infrastructure",
            "Compliance",
            "Legal",
            "Financial",
            "Marketing",
            "Healthcare",
            "Insurance",
            "Logistics",
            "Manufacturing",
            "Telecom",
            "Energy",
            "Education",
            "Government",
            "Retail",
        ]

        entity_suffixes = [
            "Corp",
            "Inc",
            "Ltd",
            "LLC",
            "Solutions",
            "Services",
            "Group",
            "Partners",
            "Associates",
            "Systems",
        ]

        # Solution types
        solution_types = [
            "Cloud Platform",
            "Security Monitoring",
            "Data Analytics",
            "CRM System",
            "ERP Software",
            "Identity Management",
            "Backup Solution",
            "Network Infrastructure",
            "Compliance Platform",
            "Risk Management",
            "Payment Processing",
            "Communication Tools",
            "HR Management",
            "Project Management",
            "API Gateway",
            "Database Service",
            "DevOps Tools",
            "Collaboration Suite",
            "Email Services",
            "Firewall System",
        ]

        # Representative roles
        representative_roles = [
            "Account Manager",
            "Technical Contact",
            "Security Lead",
            "Compliance Officer",
            "Project Manager",
            "Sales Representative",
            "Customer Success Manager",
            "Support Engineer",
            "Solution Architect",
            "Executive Sponsor",
        ]

        # Create entities
        self.stdout.write(f"Creating {num_entities} test entities...")
        entities_created = []

        for i in range(num_entities):
            # Generate unique entity name
            entity_type = random.choice(entity_types)
            suffix = random.choice(entity_suffixes)
            name = f"TEST-{entity_type} {suffix} #{i + 1}"

            # Generate mission/description
            mission = (
                f"This is a test entity created for demonstration purposes. "
                f"{name} specializes in {entity_type.lower()} services. "
                f"Automatically generated and should be used for testing only."
            )

            description = (
                f"Test entity providing {entity_type.lower()} services and solutions."
            )

            # Create entity
            entity = Entity.objects.create(
                name=name,
                description=description,
                folder=root_folder,
                mission=mission,
                reference_link=f"https://example.com/entity-{i + 1}",
                builtin=False,
            )

            # Assign random relationships (1-3)
            if entity_relationships:
                num_relationships = random.randint(1, min(3, len(entity_relationships)))
                selected_relationships = random.sample(
                    entity_relationships, num_relationships
                )
                entity.relationship.set(selected_relationships)

            entities_created.append(entity)

            # Progress indicator
            if (i + 1) % 10 == 0:
                self.stdout.write(f"  Created {i + 1}/{num_entities} entities...")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {num_entities} entities")
        )

        # Create representatives for entities (1-4 per entity)
        self.stdout.write("Creating representatives...")
        representatives_created = []

        for i, entity in enumerate(entities_created):
            num_reps = random.randint(1, 4)

            for r in range(num_reps):
                first_name = random.choice(
                    [
                        "John",
                        "Jane",
                        "Michael",
                        "Sarah",
                        "David",
                        "Emily",
                        "Robert",
                        "Lisa",
                        "James",
                        "Maria",
                    ]
                )
                last_name = random.choice(
                    [
                        "Smith",
                        "Johnson",
                        "Williams",
                        "Brown",
                        "Jones",
                        "Garcia",
                        "Miller",
                        "Davis",
                        "Rodriguez",
                        "Martinez",
                    ]
                )
                role = random.choice(representative_roles)

                # Create unique email
                email = f"test-{first_name.lower()}.{last_name.lower()}.{i + 1}.{r + 1}@example.com"

                representative = Representative.objects.create(
                    entity=entity,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}",
                    role=role,
                    description=f"{role} for {entity.name}",
                )
                representatives_created.append(representative)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(representatives_created)} representatives"
            )
        )

        # Create solutions (1-3 per entity as provider)
        self.stdout.write("Creating solutions...")
        solutions_created = []

        # Get the main entity as recipient (or use first test entity if not available)
        main_entity = Entity.get_main_entity()
        if not main_entity and entities_created:
            main_entity = entities_created[0]

        for i, entity in enumerate(entities_created):
            num_solutions = random.randint(1, 3)

            for s in range(num_solutions):
                solution_type = random.choice(solution_types)
                name = f"TEST-{solution_type} by {entity.name.replace('TEST-', '')} #{s + 1}"

                description = (
                    f"Test solution provided by {entity.name}. "
                    f"This {solution_type.lower()} solution is used for demonstration purposes. "
                    f"Automatically generated for testing only."
                )

                # Random criticality (0-4)
                criticality = random.randint(0, 4)

                solution = Solution.objects.create(
                    name=name,
                    description=description,
                    provider_entity=entity,
                    recipient_entity=main_entity,
                    ref_id=f"TEST-SOL-{i + 1:04d}-{s + 1}",
                    criticality=criticality,
                )
                solutions_created.append(solution)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(solutions_created)} solutions"
            )
        )

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        self.stdout.write(f"\nTotal Entities Created: {len(entities_created)}")
        self.stdout.write(
            f"Total Representatives Created: {len(representatives_created)}"
        )
        self.stdout.write(f"Total Solutions Created: {len(solutions_created)}")

        # Relationships breakdown
        if entity_relationships:
            self.stdout.write(f"\nEntity Relationships Distribution:")
            for relationship in entity_relationships[:10]:  # Show top 10
                count = Entity.objects.filter(
                    name__startswith="TEST-", relationship=relationship
                ).count()
                self.stdout.write(f"  {relationship.name.capitalize()}: {count}")

        # Representatives per entity
        avg_reps = len(representatives_created) / len(entities_created)
        self.stdout.write(f"\nAverage Representatives per Entity: {avg_reps:.1f}")

        # Solutions per entity
        avg_solutions = len(solutions_created) / len(entities_created)
        self.stdout.write(f"Average Solutions per Entity: {avg_solutions:.1f}")

        # Solution criticality breakdown
        self.stdout.write(f"\nSolutions by Criticality:")
        for criticality in range(5):
            count = Solution.objects.filter(
                name__startswith="TEST-", criticality=criticality
            ).count()
            self.stdout.write(f"  Level {criticality}: {count}")

        # Representative roles breakdown
        self.stdout.write(f"\nTop Representative Roles:")
        role_counts = {}
        for rep in representatives_created:
            role_counts[rep.role] = role_counts.get(rep.role, 0) + 1

        for role, count in sorted(
            role_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            self.stdout.write(f"  {role}: {count}")

        self.stdout.write("=" * 60)
