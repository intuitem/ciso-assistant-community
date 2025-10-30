import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from privacy.models import (
    Processing,
    Purpose,
    PersonalData,
    DataSubject,
    DataRecipient,
    DataContractor,
    DataTransfer,
    ProcessingNature,
    LEGAL_BASIS_CHOICES,
)
from iam.models import Folder, User
from tprm.models import Entity
from core.constants import COUNTRY_CHOICES


class Command(BaseCommand):
    help = "Populates random privacy processing data with associated personal data, transfers, etc."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=20,
            help="Number of processing records to create (default: 20)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST- prefixed privacy data (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        num_processings = options["count"]
        clean = options["clean"]
        fresh = options["fresh"]

        # Clean existing test data if requested
        if clean or fresh:
            self.stdout.write("Cleaning existing test data...")

            # Delete all related objects first due to cascade
            deleted_processings = Processing.objects.filter(
                name__startswith="TEST-"
            ).count()
            Processing.objects.filter(name__startswith="TEST-").delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleaned {deleted_processings} processing records and all associated data"
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

        # Get active users
        users = list(User.objects.filter(is_active=True)[:10])
        if not users:
            self.stdout.write(
                self.style.WARNING(
                    "No active users found. Using system for assignments."
                )
            )

        # Get entities for contractors/transfers
        entities = list(Entity.objects.all()[:20])
        if not entities:
            self.stdout.write(
                self.style.WARNING(
                    "No entities found. Data contractors and transfers will have no entity."
                )
            )

        # Get processing natures
        processing_natures = list(ProcessingNature.objects.all())
        if not processing_natures:
            self.stdout.write(
                self.style.WARNING(
                    "No processing natures found. Consider running migrations or creating defaults."
                )
            )

        # Processing activity templates
        processing_activities = [
            "Customer Relationship Management",
            "Employee HR Management",
            "Marketing Campaign Management",
            "Payment Processing",
            "User Account Management",
            "Analytics and Reporting",
            "Technical Support Services",
            "Newsletter Distribution",
            "Job Application Processing",
            "Website Analytics",
            "Mobile Application Services",
            "Cloud Storage Services",
            "Video Surveillance",
            "Access Control System",
            "Performance Evaluation",
            "Training and Development",
            "Recruitment and Hiring",
            "Vendor Management",
            "Customer Support Portal",
            "E-commerce Platform",
        ]

        # Status choices
        status_choices = [
            "privacy_draft",
            "privacy_in_review",
            "privacy_approved",
            "privacy_deprecated",
        ]
        status_weights = [0.2, 0.25, 0.5, 0.05]

        # Country choices (select common ones)
        common_countries = [
            "USA",
            "GBR",
            "DEU",
            "FRA",
            "CAN",
            "JPN",
            "AUS",
            "IND",
            "CHN",
            "BRA",
        ]

        # Legal basis choices (common ones)
        common_legal_bases = [
            legal_basis[0]
            for legal_basis in LEGAL_BASIS_CHOICES
            if legal_basis[0]
            in [
                "privacy_consent",
                "privacy_contract",
                "privacy_legal_obligation",
                "privacy_legitimate_interests",
                "privacy_explicit_consent",
            ]
        ]

        # Create processing records
        self.stdout.write(f"Creating {num_processings} test processing records...")
        processings_created = []

        for i in range(num_processings):
            # Generate unique processing name
            activity = random.choice(processing_activities)
            name = f"TEST-{activity} #{i + 1}"

            # Generate description
            description = (
                f"This is a test processing activity created for demonstration purposes. "
                f"Processing involves {activity.lower()}. "
                f"Automatically generated and should be used for testing only."
            )

            # Determine status
            status = random.choices(status_choices, weights=status_weights)[0]

            # Determine if DPIA required (30% chance for high-risk processing)
            dpia_required = random.random() < 0.3

            # Create processing
            processing = Processing.objects.create(
                name=name,
                description=description,
                folder=root_folder,
                ref_id=f"TEST-PROC-{i + 1:04d}",
                status=status,
                author=random.choice(users) if users else None,
                dpia_required=dpia_required,
                dpia_reference=f"DPIA-{i + 1:04d}" if dpia_required else "",
                has_sensitive_personal_data=False,  # Will be updated if sensitive data added
            )

            # Assign users (0-3)
            if users:
                num_assigned = random.randint(0, min(3, len(users)))
                if num_assigned > 0:
                    assigned = random.sample(users, num_assigned)
                    processing.assigned_to.set(assigned)

            # Assign processing natures (1-4)
            if processing_natures:
                num_natures = random.randint(1, min(4, len(processing_natures)))
                selected_natures = random.sample(processing_natures, num_natures)
                processing.nature.set(selected_natures)

            # Set owner entity if available
            if entities:
                processing.owner = random.choice(entities)
                processing.save(update_fields=["owner"])

            # Create 1-3 purposes
            num_purposes = random.randint(1, 3)
            for p in range(num_purposes):
                Purpose.objects.create(
                    processing=processing,
                    name=f"Purpose {p + 1} for {activity}",
                    description=f"Purpose description for {activity.lower()}",
                    legal_basis=random.choice(common_legal_bases),
                )

            # Create 2-5 personal data items
            num_personal_data = random.randint(2, 5)
            personal_data_categories = [
                "privacy_name",
                "privacy_email",
                "privacy_phone_number",
                "privacy_address",
                "privacy_ip_address",
                "privacy_browsing_history",
                "privacy_financial_data",
                "privacy_employment_details",
                "privacy_health_data",  # sensitive
                "privacy_biometric_data",  # sensitive
                "privacy_political_opinions",  # sensitive
            ]

            sensitive_categories = [
                "privacy_health_data",
                "privacy_biometric_data",
                "privacy_political_opinions",
                "privacy_racial_ethnic_origin",
                "privacy_religious_beliefs",
            ]

            selected_categories = random.sample(
                personal_data_categories,
                min(num_personal_data, len(personal_data_categories)),
            )

            for category in selected_categories:
                is_sensitive = category in sensitive_categories
                PersonalData.objects.create(
                    processing=processing,
                    name=f"Personal Data - {category}",
                    description=f"Description for {category}",
                    category=category,
                    retention=f"{random.randint(1, 7)} years",
                    deletion_policy=random.choice(
                        [choice[0] for choice in PersonalData.DELETION_POLICY_CHOICES]
                    ),
                    is_sensitive=is_sensitive,
                )

            # Refresh to get updated sensitive flag
            processing.refresh_from_db()

            # Create 1-3 data subjects
            num_subjects = random.randint(1, 3)
            subject_categories = [
                "privacy_customer",
                "privacy_employee",
                "privacy_user",
                "privacy_job_applicant",
                "privacy_contractor",
            ]
            for s in range(num_subjects):
                category = random.choice(subject_categories)
                DataSubject.objects.create(
                    processing=processing,
                    name=f"Data Subject - {category}",
                    description=f"Data subjects in category {category}",
                    category=category,
                )

            # Create 1-4 data recipients
            num_recipients = random.randint(1, 4)
            recipient_categories = [
                "privacy_internal_team",
                "privacy_service_provider",
                "privacy_cloud_provider",
                "privacy_payment_processor",
                "privacy_legal_advisor",
                "privacy_regulatory_authority",
            ]
            for r in range(num_recipients):
                category = random.choice(recipient_categories)
                DataRecipient.objects.create(
                    processing=processing,
                    name=f"Recipient - {category}",
                    description=f"Data recipient in category {category}",
                    category=category,
                )

            # Create 0-2 data contractors (if entities available)
            if entities:
                num_contractors = random.randint(0, 2)
                for c in range(num_contractors):
                    DataContractor.objects.create(
                        processing=processing,
                        name=f"Contractor {c + 1}",
                        description=f"Data contractor for {activity.lower()}",
                        entity=random.choice(entities),
                        relationship_type=random.choice(
                            [
                                choice[0]
                                for choice in DataContractor.RELATIONSHIP_TYPE_CHOICES
                            ]
                        ),
                        country=random.choice(common_countries),
                        documentation_link=f"https://example.com/contract-{i}-{c}",
                    )

            # Create 0-2 data transfers (if entities available)
            if entities:
                num_transfers = random.randint(0, 2)
                for t in range(num_transfers):
                    DataTransfer.objects.create(
                        processing=processing,
                        name=f"Transfer {t + 1} to international location",
                        description=f"International data transfer for {activity.lower()}",
                        entity=random.choice(entities),
                        country=random.choice(common_countries),
                        legal_basis=random.choice(common_legal_bases),
                        guarantees="Standard contractual clauses (SCCs) in place",
                        documentation_link=f"https://example.com/transfer-{i}-{t}",
                    )

            processings_created.append(processing)

            # Progress indicator
            if (i + 1) % 10 == 0:
                self.stdout.write(
                    f"  Created {i + 1}/{num_processings} processing records..."
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {num_processings} processing records"
            )
        )

        # Print summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY:")
        self.stdout.write("=" * 60)

        self.stdout.write(
            f"\nTotal Processing Records Created: {len(processings_created)}"
        )

        self.stdout.write(f"\nProcessing by Status:")
        for status_val, status_label in Processing.STATUS_CHOICES:
            count = Processing.objects.filter(
                status=status_val, name__startswith="TEST-"
            ).count()
            self.stdout.write(f"  {status_label}: {count}")

        sensitive_count = Processing.objects.filter(
            name__startswith="TEST-", has_sensitive_personal_data=True
        ).count()
        self.stdout.write(f"\nWith Sensitive Personal Data: {sensitive_count}")

        dpia_count = Processing.objects.filter(
            name__startswith="TEST-", dpia_required=True
        ).count()
        self.stdout.write(f"DPIA Required: {dpia_count}")

        # Count associated objects
        purpose_count = Purpose.objects.filter(
            processing__name__startswith="TEST-"
        ).count()
        personal_data_count = PersonalData.objects.filter(
            processing__name__startswith="TEST-"
        ).count()
        subject_count = DataSubject.objects.filter(
            processing__name__startswith="TEST-"
        ).count()
        recipient_count = DataRecipient.objects.filter(
            processing__name__startswith="TEST-"
        ).count()
        contractor_count = DataContractor.objects.filter(
            processing__name__startswith="TEST-"
        ).count()
        transfer_count = DataTransfer.objects.filter(
            processing__name__startswith="TEST-"
        ).count()

        self.stdout.write(f"\nAssociated Data Created:")
        self.stdout.write(f"  Purposes: {purpose_count}")
        self.stdout.write(f"  Personal Data Items: {personal_data_count}")
        self.stdout.write(f"  Data Subjects: {subject_count}")
        self.stdout.write(f"  Data Recipients: {recipient_count}")
        self.stdout.write(f"  Data Contractors: {contractor_count}")
        self.stdout.write(f"  Data Transfers: {transfer_count}")

        # Show top personal data categories
        self.stdout.write(f"\nTop Personal Data Categories:")
        category_counts = {}
        for pd in PersonalData.objects.filter(processing__name__startswith="TEST-"):
            category_counts[pd.category] = category_counts.get(pd.category, 0) + 1

        for category, count in sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            # Get label from choices
            label = dict(PersonalData.PERSONAL_DATA_CHOICES).get(category, category)
            self.stdout.write(f"  {label}: {count}")

        self.stdout.write("=" * 60)
