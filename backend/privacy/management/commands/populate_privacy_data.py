import random
from datetime import timedelta
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
    RightRequest,
    DataBreach,
    ART6_LAWFUL_BASIS_CHOICES,
    TRANSFER_MECHANISM_CHOICES,
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
            deleted_right_requests = RightRequest.objects.filter(
                name__startswith="TEST-"
            ).count()
            deleted_breaches = DataBreach.objects.filter(
                name__startswith="TEST-"
            ).count()

            Processing.objects.filter(name__startswith="TEST-").delete()
            RightRequest.objects.filter(name__startswith="TEST-").delete()
            DataBreach.objects.filter(name__startswith="TEST-").delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleaned {deleted_processings} processing records, "
                    f"{deleted_right_requests} right requests, "
                    f"{deleted_breaches} data breaches, "
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

        # Country choices
        common_countries = [
            "US",
            "GB",
            "DE",
            "FR",
            "CA",
            "JP",
            "AU",
            "IN",
            "CN",
            "BR",
            "AR",
            "ID",
            "IT",
            "KR",
            "MX",
            "RU",
            "SA",
            "ZA",
            "TR",
            "BE",
            "MA",
            "DZ",
        ]

        # Legal basis choices (Art 6 bases for Purpose)
        common_legal_bases = [choice[0] for choice in ART6_LAWFUL_BASIS_CHOICES]

        # Transfer mechanism choices (Art 45-49 for DataTransfer)
        transfer_mechanisms = [choice[0] for choice in TRANSFER_MECHANISM_CHOICES]

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
                author=random.choice(users).actor if users else None,
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
                        transfer_mechanism=random.choice(transfer_mechanisms),
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

        # Create right requests (about 30% of processings)
        num_right_requests = max(1, int(num_processings * 0.3))
        self.stdout.write(f"\nCreating {num_right_requests} right requests...")

        for i in range(num_right_requests):
            requested_on = timezone.now().date() - timedelta(
                days=random.randint(1, 180)
            )
            due_date_offset = random.randint(15, 45)
            due_date = requested_on + timedelta(days=due_date_offset)

            right_request = RightRequest.objects.create(
                name=f"TEST-Right Request #{i + 1}",
                description=f"Test right request for {random.choice(['access', 'deletion', 'rectification'])} of personal data",
                folder=root_folder,
                ref_id=f"TEST-RR-{i + 1:04d}",
                requested_on=requested_on,
                due_date=due_date,
                request_type=random.choice(
                    [choice[0] for choice in RightRequest.REQUEST_TYPE_CHOICES]
                ),
                status=random.choice(
                    [choice[0] for choice in RightRequest.STATUS_CHOICES]
                ),
                observation=f"Test observation for right request #{i + 1}",
            )

            # Assign owners (0-2 users)
            if users:
                num_owners = random.randint(0, min(2, len(users)))
                if num_owners > 0:
                    right_request.owner.set(random.sample(users, num_owners))

            # Associate with 1-3 processings
            num_proc = random.randint(1, min(3, len(processings_created)))
            right_request.processings.set(random.sample(processings_created, num_proc))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {num_right_requests} right requests"
            )
        )

        # Create data breaches (about 10-15% of processings)
        num_breaches = max(1, int(num_processings * random.uniform(0.1, 0.15)))
        self.stdout.write(f"\nCreating {num_breaches} data breaches...")

        breach_descriptions = [
            "Unauthorized access to database containing personal data",
            "Accidental disclosure of personal information via email",
            "Lost laptop containing unencrypted personal data",
            "Ransomware attack affecting personal data systems",
            "Third-party vendor data exposure incident",
            "Misconfigured cloud storage bucket exposing data",
            "Phishing attack leading to credential compromise",
            "Insider threat resulting in data exfiltration",
            "Physical document theft from office premises",
            "Improper disposal of documents containing personal data",
        ]

        for i in range(num_breaches):
            discovered_on = timezone.now() - timedelta(
                days=random.randint(1, 120), hours=random.randint(0, 23)
            )

            # Determine risk level and whether notifications were made
            risk_level = random.choice(
                [choice[0] for choice in DataBreach.RISK_LEVEL_CHOICES]
            )
            status = random.choice([choice[0] for choice in DataBreach.STATUS_CHOICES])

            # High risk breaches are more likely to require notifications
            authority_notified = (
                risk_level == "privacy_high_risk" and random.random() < 0.8
            )
            subjects_notified = (
                risk_level
                in [
                    "privacy_high_risk",
                    "privacy_risk",
                ]
                and random.random() < 0.6
            )

            data_breach = DataBreach.objects.create(
                name=f"TEST-Data Breach #{i + 1}",
                description=random.choice(breach_descriptions),
                folder=root_folder,
                ref_id=f"TEST-DB-{i + 1:04d}",
                discovered_on=discovered_on,
                breach_type=random.choice(
                    [choice[0] for choice in DataBreach.BREACH_TYPE_CHOICES]
                ),
                risk_level=risk_level,
                status=status,
                affected_subjects_count=random.randint(10, 10000),
                affected_personal_data_count=random.randint(5, 100),
                authority_notified_on=discovered_on
                + timedelta(hours=random.randint(24, 72))
                if authority_notified
                else None,
                authority_notification_ref=f"AUTH-REF-{i + 1:06d}"
                if authority_notified
                else "",
                subjects_notified_on=discovered_on
                + timedelta(days=random.randint(3, 14))
                if subjects_notified
                else None,
                potential_consequences="Potential identity theft, financial fraud, privacy violations, and reputational damage to affected individuals.",
                observation=f"Test data breach record #{i + 1} for demonstration purposes.",
            )

            # Assign to users (1-3)
            if users:
                num_assigned = random.randint(1, min(3, len(users)))
                data_breach.assigned_to.set(random.sample(users, num_assigned))

            # Associate with 1-2 processings
            num_proc = random.randint(1, min(2, len(processings_created)))
            affected_processings = random.sample(processings_created, num_proc)
            data_breach.affected_processings.set(affected_processings)

            # Associate with personal data from the affected processings
            personal_data_pool = []
            for proc in affected_processings:
                personal_data_pool.extend(list(proc.personal_data.all()))

            if personal_data_pool:
                num_pd = random.randint(1, min(5, len(personal_data_pool)))
                data_breach.affected_personal_data.set(
                    random.sample(personal_data_pool, num_pd)
                )

            # Add authorities if notified
            if authority_notified and entities:
                num_authorities = random.randint(1, min(2, len(entities)))
                data_breach.authorities.set(random.sample(entities, num_authorities))

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {num_breaches} data breaches")
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

        # Right Requests statistics
        right_request_count = RightRequest.objects.filter(
            name__startswith="TEST-"
        ).count()
        self.stdout.write(f"\nRight Requests Created: {right_request_count}")

        if right_request_count > 0:
            self.stdout.write(f"\nRight Requests by Type:")
            for req_type, req_label in RightRequest.REQUEST_TYPE_CHOICES:
                count = RightRequest.objects.filter(
                    name__startswith="TEST-", request_type=req_type
                ).count()
                if count > 0:
                    self.stdout.write(f"  {req_label}: {count}")

            self.stdout.write(f"\nRight Requests by Status:")
            for status_val, status_label in RightRequest.STATUS_CHOICES:
                count = RightRequest.objects.filter(
                    name__startswith="TEST-", status=status_val
                ).count()
                if count > 0:
                    self.stdout.write(f"  {status_label}: {count}")

        # Data Breaches statistics
        breach_count = DataBreach.objects.filter(name__startswith="TEST-").count()
        self.stdout.write(f"\nData Breaches Created: {breach_count}")

        if breach_count > 0:
            self.stdout.write(f"\nData Breaches by Risk Level:")
            for risk_val, risk_label in DataBreach.RISK_LEVEL_CHOICES:
                count = DataBreach.objects.filter(
                    name__startswith="TEST-", risk_level=risk_val
                ).count()
                if count > 0:
                    self.stdout.write(f"  {risk_label}: {count}")

            self.stdout.write(f"\nData Breaches by Status:")
            for status_val, status_label in DataBreach.STATUS_CHOICES:
                count = DataBreach.objects.filter(
                    name__startswith="TEST-", status=status_val
                ).count()
                if count > 0:
                    self.stdout.write(f"  {status_label}: {count}")

            authority_notified_count = DataBreach.objects.filter(
                name__startswith="TEST-", authority_notified_on__isnull=False
            ).count()
            subjects_notified_count = DataBreach.objects.filter(
                name__startswith="TEST-", subjects_notified_on__isnull=False
            ).count()
            self.stdout.write(f"\nNotifications:")
            self.stdout.write(f"  Authority Notified: {authority_notified_count}")
            self.stdout.write(f"  Data Subjects Notified: {subjects_notified_count}")

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
