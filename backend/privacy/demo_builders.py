"""Privacy demo: a GDPR record of processing activities.

Eleven processings spread over the demo domain and its sub-domains (store
orders, camera video, thermostat telemetry, app analytics, support, marketing,
HR, recruitment, plant CCTV, instalment credit checks, the hub beta), each with
its purposes, personal data, data subjects, recipients, processors and
international transfers; then data subject right requests and data breaches
that point back at them. Children inherit their processing's folder on save.
Third-party entities are left unset: they belong to the TPRM story.
"""

from datetime import UTC, datetime, time, timedelta
from typing import ClassVar

from core.demo import COMPANY, PAY_ENTITY, DemoBuilder, register
from core.models import Terminology
from iam.models import Folder
from privacy.models import (
    DataBreach,
    DataContractor,
    DataRecipient,
    DataSubject,
    DataTransfer,
    PersonalData,
    Processing,
    Purpose,
    RightRequest,
)

# Each processing: header, then its children. Folder None is the demo domain.
PROCESSINGS = [
    {
        "ref_id": "ROPA-001",
        "name": "Online store orders and customer accounts",
        "folder": "Online Store & Payments",
        "status": "privacy_approved",
        "description": (
            "Customer account creation, checkout, delivery, returns and warranty "
            "for Kelvin, Lookout and Keystone devices bought on the online store."
        ),
        "information_channel": (
            f"Privacy notice at checkout and in order confirmation emails from {COMPANY}"
        ),
        "usage_channel": "Online store web front, companion app account screens",
        "dpia_required": False,
        "nature": ["privacy_collection", "privacy_storage", "privacy_use"],
        "controls": ["AC.001", "AC.011", "AC.016"],
        "perimeters": ["PER.002"],
        "purposes": [
            ("Order fulfilment, delivery and returns", "privacy_contract", None),
            ("Invoicing and accounting records", "privacy_legal_obligation", None),
            (
                "Fraud screening on card payments",
                "privacy_legitimate_interests",
                None,
            ),
            ("Two-year legal warranty handling", "privacy_legal_obligation", None),
        ],
        "personal_data": [
            (
                "Customer identity",
                "privacy_name",
                "3 years after last order",
                "privacy_automatic_deletion",
                ["Customer and device accounts"],
            ),
            (
                "Delivery address",
                "privacy_address",
                "3 years after last order",
                "privacy_automatic_deletion",
                ["Customer and device accounts", "Order fulfilment"],
            ),
            (
                "Account email and password hash",
                "privacy_email",
                "Until account closure",
                "privacy_user_requested_deletion",
                ["Customer and device accounts", "Online store web front"],
            ),
            (
                "Card payment token",
                "privacy_payment_card",
                "13 months",
                "privacy_automatic_deletion",
                ["Store checkout and payments"],
            ),
            (
                "Order and warranty history",
                "privacy_transaction_history",
                "10 years (accounting law)",
                "privacy_legal_regulatory_hold",
                ["Customer and device accounts", "Order fulfilment"],
            ),
        ],
        "subjects": [
            ("Online store customers", "privacy_customer"),
            ("Gift recipients at delivery addresses", "privacy_other"),
        ],
        "recipients": [
            ("Customer care team (Lyon)", "privacy_internal_team"),
            ("Parcel carrier", "privacy_service_provider"),
            ("Card acquirer", "privacy_payment_processor"),
            ("Cloud hosting provider", "privacy_cloud_provider"),
        ],
        "contractors": [
            (
                "Tallbridge Logistics",
                "privacy_data_processor",
                "NL",
                "https://dpa.example.com/tallbridge",
            ),
            ("Pellion Payments", "privacy_independent_controller", "BE", ""),
        ],
        "transfers": [
            (
                "Carrier tracking platform (UK)",
                "GB",
                "privacy_adequacy_decision",
                "UK adequacy decision; Tallbridge tracking portal hosted in London.",
            ),
        ],
    },
    {
        "ref_id": "ROPA-002",
        "name": "Lookout camera video storage",
        "folder": "Connected Products",
        "status": "privacy_approved",
        "description": (
            "Cloud storage and playback of motion-triggered clips recorded by "
            "Lookout indoor and outdoor cameras, with event thumbnails pushed to "
            "the companion app."
        ),
        "information_channel": (
            "In-app notice at camera setup; window sticker kit for outdoor cameras"
        ),
        "usage_channel": "Companion app, device cloud clip storage",
        "dpia_required": True,
        "dpia_reference": "DPIA-2025-02",
        "nature": [
            "privacy_recording",
            "privacy_storage",
            "privacy_consultation",
            "privacy_erasureOrDestruction",
        ],
        "controls": ["AC.010", "AC.014", "AC.018"],
        "perimeters": ["PER.001"],
        "purposes": [
            (
                "Storing and replaying clips for the camera owner",
                "privacy_contract",
                None,
            ),
            (
                "Diagnosing camera faults on owner request",
                "privacy_legitimate_interests",
                None,
            ),
            (
                "Answering law enforcement orders",
                "privacy_legal_obligation",
                "privacy_legal_claims",
            ),
        ],
        "personal_data": [
            (
                "Video clips",
                "privacy_video_recordings",
                "30 days (Plus plan: 60 days)",
                "privacy_automatic_deletion",
                ["Customer and device accounts", "Device cloud Kubernetes cluster"],
            ),
            (
                "Audio track of clips",
                "privacy_voice_recordings",
                "Same as the clip",
                "privacy_automatic_deletion",
                ["Device cloud Kubernetes cluster"],
            ),
            (
                "Event thumbnails",
                "privacy_images_photos",
                "30 days",
                "privacy_automatic_deletion",
                ["Companion mobile app", "Device cloud Kubernetes cluster"],
            ),
            (
                "Motion event metadata",
                "privacy_device_information",
                "13 months",
                "privacy_anonymization",
                ["MQTT device gateway", "PostgreSQL primary"],
            ),
            (
                "Camera installation location",
                "privacy_location_data",
                "Until the camera is unpaired",
                "privacy_user_requested_deletion",
                ["Customer and device accounts"],
            ),
        ],
        "subjects": [
            ("Camera owners", "privacy_customer"),
            ("Household members", "privacy_other"),
            ("Children filmed at home", "privacy_minor"),
            ("Visitors and passers-by", "privacy_visitor"),
        ],
        "recipients": [
            ("Device cloud operations", "privacy_internal_team"),
            ("Outsourced support (with owner consent)", "privacy_service_provider"),
            ("Police, on judicial order", "privacy_law_enforcement"),
        ],
        "contractors": [
            (
                "Kestrava Cloud",
                "privacy_data_processor",
                "DE",
                "https://dpa.example.com/kestrava",
            ),
            (
                "Mireo Support",
                "privacy_sub_processor",
                "PT",
                "https://dpa.example.com/mireo",
            ),
        ],
        "transfers": [],
    },
    {
        "ref_id": "ROPA-003",
        "name": "Kelvin energy usage telemetry",
        "folder": "Connected Products",
        "status": "privacy_approved",
        "description": (
            "Temperature, setpoint and heating runtime readings sent by Kelvin "
            "thermostats every five minutes, used for schedules, energy reports "
            "and the optional demand-response programme."
        ),
        "information_channel": "Companion app onboarding and settings screen",
        "usage_channel": "MQTT device gateway, companion app energy reports",
        "dpia_required": False,
        "nature": [
            "privacy_collection",
            "privacy_storage",
            "privacy_use",
            "privacy_alignmentOrCombination",
        ],
        "controls": ["AC.011", "AC.018"],
        "perimeters": ["PER.001"],
        "purposes": [
            ("Running heating schedules and remote control", "privacy_contract", None),
            ("Monthly energy savings reports", "privacy_contract", None),
            (
                "Product improvement on aggregated readings",
                "privacy_legitimate_interests",
                None,
            ),
            ("Grid demand-response programme", "privacy_consent", None),
        ],
        "personal_data": [
            (
                "Energy consumption readings",
                "privacy_user_behavior",
                "24 months, then aggregated",
                "privacy_anonymization",
                ["MQTT device gateway", "PostgreSQL primary"],
            ),
            (
                "Occupancy schedule",
                "privacy_lifestyle_information",
                "Until changed by the user",
                "privacy_user_requested_deletion",
                ["Customer and device accounts"],
            ),
            (
                "Postal code for weather compensation",
                "privacy_location_data",
                "Until the thermostat is unpaired",
                "privacy_user_requested_deletion",
                ["Customer and device accounts"],
            ),
            (
                "Device serial and firmware version",
                "privacy_device_information",
                "Lifetime of the device",
                "privacy_manual_review_deletion",
                ["Device firmware and signing keys"],
            ),
        ],
        "subjects": [
            ("Thermostat owners", "privacy_customer"),
            ("Members of the household", "privacy_other"),
        ],
        "recipients": [
            ("Device cloud operations", "privacy_internal_team"),
            ("Energy supplier partners (opt-in only)", "privacy_business_partner"),
        ],
        "contractors": [
            (
                "Kestrava Cloud",
                "privacy_data_processor",
                "DE",
                "https://dpa.example.com/kestrava",
            ),
            ("Voltaria Energy", "privacy_independent_controller", "FR", ""),
        ],
        "transfers": [],
    },
    {
        "ref_id": "ROPA-004",
        "name": "Companion app product analytics",
        "folder": "Connected Products",
        "status": "privacy_in_review",
        "description": (
            "Screen views, feature usage and crash reports collected by the "
            "Fennick Analytics SDK embedded in the iOS and Android companion app."
        ),
        "information_channel": "Consent prompt at first app launch",
        "usage_channel": "Fennick Analytics dashboards",
        "dpia_required": False,
        "nature": ["privacy_collection", "privacy_use", "privacy_structuring"],
        "controls": ["AC.011"],
        "perimeters": ["PER.001"],
        "purposes": [
            ("Measuring feature adoption", "privacy_consent", None),
            ("Crash diagnostics", "privacy_legitimate_interests", None),
        ],
        "personal_data": [
            (
                "App instance identifier",
                "privacy_online_identifiers",
                "14 months",
                "privacy_automatic_deletion",
                ["Companion mobile app"],
            ),
            (
                "Phone model and OS version",
                "privacy_device_information",
                "14 months",
                "privacy_automatic_deletion",
                ["Companion mobile app"],
            ),
            (
                "In-app navigation events",
                "privacy_user_behavior",
                "14 months",
                "privacy_anonymization",
                ["Companion mobile app"],
            ),
            (
                "Truncated IP address",
                "privacy_ip_address",
                "30 days",
                "privacy_automatic_deletion",
                [],
            ),
        ],
        "subjects": [("Companion app users", "privacy_user")],
        "recipients": [
            ("Product management", "privacy_internal_team"),
            ("Analytics provider", "privacy_analytics_provider"),
        ],
        "contractors": [
            (
                "Fennick Analytics",
                "privacy_data_processor",
                "US",
                "https://dpa.example.com/fennick",
            ),
        ],
        "transfers": [
            (
                "Analytics platform (US)",
                "US",
                "privacy_certification_mechanisms",
                (
                    "Fennick certified under the EU-US Data Privacy Framework; SCCs "
                    "module 2 kept as fallback, IP addresses truncated in the SDK."
                ),
            ),
        ],
    },
    {
        "ref_id": "ROPA-005",
        "name": "Customer support and returns (RMA)",
        "folder": None,
        "status": "privacy_approved",
        "description": (
            "Tickets, chat, calls and return merchandise authorisations handled "
            "by Mireo Support; device logs of returned cameras are analysed by "
            "the contract manufacturer in Shenzhen."
        ),
        "information_channel": "Support portal notice and IVR message",
        "usage_channel": "Helpdesk platform, telephony, RMA portal",
        "dpia_required": False,
        "nature": [
            "privacy_recording",
            "privacy_consultation",
            "privacy_disclosureByTransmission",
        ],
        "controls": ["AC.001", "AC.004", "AC.009"],
        "perimeters": ["PER.001", "PER.002"],
        "purposes": [
            ("Handling customer requests", "privacy_contract", None),
            ("Return and replacement of faulty devices", "privacy_contract", None),
            (
                "Call recording for quality and training",
                "privacy_legitimate_interests",
                None,
            ),
        ],
        "personal_data": [
            (
                "Contact details",
                "privacy_contact_details",
                "3 years after last ticket",
                "privacy_automatic_deletion",
                ["Customer and device accounts"],
            ),
            (
                "Support tickets and chat transcripts",
                "privacy_correspondence",
                "3 years after last ticket",
                "privacy_partial_deletion",
                [],
            ),
            (
                "Call recordings",
                "privacy_voice_recordings",
                "6 months",
                "privacy_automatic_deletion",
                [],
            ),
            (
                "Device diagnostic logs",
                "privacy_device_information",
                "12 months after RMA closure",
                "privacy_automatic_deletion",
                ["Device cloud Kubernetes cluster"],
            ),
        ],
        "subjects": [
            ("Customers contacting support", "privacy_customer"),
            ("Retail partner customers", "privacy_customer"),
        ],
        "recipients": [
            ("Customer care team (Lyon)", "privacy_internal_team"),
            ("Outsourced support centre", "privacy_service_provider"),
            ("Contract manufacturer (RMA analysis)", "privacy_supplier"),
        ],
        "contractors": [
            (
                "Mireo Support",
                "privacy_data_processor",
                "PT",
                "https://dpa.example.com/mireo",
            ),
            ("Mireo Support nearshore centre", "privacy_sub_processor", "MA", ""),
            (
                "Shenwa Contract Manufacturing (RMA analysis)",
                "privacy_other",
                "CN",
                "https://dpa.example.com/shenwa",
            ),
        ],
        "transfers": [
            (
                "Support nearshore centre (Morocco)",
                "MA",
                "privacy_standard_contractual_clauses",
                (
                    "SCCs module 3 with Mireo; agents work through VDI only, no local "
                    "storage, camera clips never visible from Morocco."
                ),
            ),
            (
                "RMA failure analysis (Shenzhen)",
                "CN",
                "privacy_standard_contractual_clauses",
                (
                    "SCCs module 2 and transfer impact assessment; device logs "
                    "pseudonymised (serial only) before upload, clips wiped on return."
                ),
            ),
        ],
    },
    {
        "ref_id": "ROPA-006",
        "name": "Marketing emails",
        "folder": "Online Store & Payments",
        "status": "privacy_in_review",
        "description": (
            "Product launch announcements, promotions and newsletters sent to "
            "opted-in customers and prospects through Quorra Mail."
        ),
        "information_channel": "Consent checkbox at account creation and sign-up form",
        "usage_channel": "Quorra Mail campaign manager",
        "dpia_required": False,
        "nature": [
            "privacy_collection",
            "privacy_use",
            "privacy_alignmentOrCombination",
        ],
        "controls": ["AC.011"],
        "perimeters": ["PER.002"],
        "purposes": [
            ("Sending promotional emails", "privacy_consent", None),
            ("Measuring campaign performance", "privacy_legitimate_interests", None),
        ],
        "personal_data": [
            (
                "Email address",
                "privacy_email",
                "3 years after last click",
                "privacy_automatic_deletion",
                ["Customer and device accounts"],
            ),
            (
                "Owned products and preferences",
                "privacy_preferences",
                "Until unsubscribe",
                "privacy_user_requested_deletion",
                [],
            ),
            (
                "Email engagement tracking",
                "privacy_user_behavior",
                "13 months",
                "privacy_anonymization",
                [],
            ),
        ],
        "subjects": [
            ("Newsletter subscribers", "privacy_customer"),
            ("Prospects from trade fairs", "privacy_prospect"),
        ],
        "recipients": [
            ("Marketing team", "privacy_internal_team"),
            ("Email service provider", "privacy_marketing_agency"),
        ],
        "contractors": [
            (
                "Quorra Mail",
                "privacy_data_processor",
                "IE",
                "https://dpa.example.com/quorra",
            ),
        ],
        "transfers": [
            (
                "Email delivery relays (US)",
                "US",
                "privacy_standard_contractual_clauses",
                (
                    "Quorra Mail sub-processor not certified under the Data Privacy "
                    "Framework: SCCs module 3, encryption at rest with EU-held keys."
                ),
            ),
        ],
    },
    {
        "ref_id": "ROPA-007",
        "name": "Payroll and HR administration",
        "folder": "Corporate IT",
        "status": "privacy_approved",
        "description": (
            "Payroll, leave, benefits and statutory declarations for the 1,400 "
            "employees in Lyon, Brno and Eindhoven."
        ),
        "information_channel": "Employee privacy notice on the intranet",
        "usage_channel": "HRIS, payroll provider portal",
        "dpia_required": True,
        "dpia_reference": "DPIA-2025-03",
        "nature": [
            "privacy_recording",
            "privacy_storage",
            "privacy_disclosureByTransmission",
        ],
        "controls": ["AC.001", "AC.005", "AC.009"],
        "perimeters": [],
        "purposes": [
            (
                "Salary payment and statutory declarations",
                "privacy_legal_obligation",
                None,
            ),
            (
                "Sick leave and occupational health follow-up",
                "privacy_legal_obligation",
                "privacy_employment_social_security",
            ),
            ("Union dues deduction", "privacy_consent", "privacy_explicit_consent"),
            ("Workforce account provisioning", "privacy_contract", None),
        ],
        "personal_data": [
            (
                "Employee identity",
                "privacy_name",
                "5 years after departure",
                "privacy_manual_review_deletion",
                ["Workforce identity provider"],
            ),
            (
                "Bank details",
                "privacy_bank_account",
                "5 years after departure",
                "privacy_manual_review_deletion",
                [],
            ),
            (
                "Salary and bonuses",
                "privacy_salary_information",
                "5 years after departure",
                "privacy_legal_regulatory_hold",
                [],
            ),
            (
                "Social security number",
                "privacy_social_security",
                "5 years after departure",
                "privacy_legal_regulatory_hold",
                [],
            ),
            (
                "Sick leave certificates",
                "privacy_health_data",
                "2 years",
                "privacy_automatic_deletion",
                [],
            ),
            (
                "Union membership",
                "privacy_trade_union_membership",
                "Until consent is withdrawn",
                "privacy_user_requested_deletion",
                [],
            ),
        ],
        "subjects": [
            ("Employees", "privacy_employee"),
            ("Former employees", "privacy_employee"),
            ("Temporary plant workers", "privacy_contractor"),
        ],
        "recipients": [
            ("HR department", "privacy_internal_team"),
            ("Tax and social security administrations", "privacy_tax_authority"),
            ("External payroll auditor", "privacy_auditor"),
            ("Brightline Identity (workforce identity SaaS)", "privacy_it_provider"),
        ],
        "contractors": [
            (
                "Pavlek Payroll Services",
                "privacy_data_processor",
                "FR",
                "https://dpa.example.com/pavlek",
            ),
            (
                "Pavlek Payroll Services (Brno office)",
                "privacy_sub_processor",
                "CZ",
                "",
            ),
        ],
        "transfers": [
            (
                "Identity provider support (US)",
                "US",
                "privacy_certification_mechanisms",
                (
                    "Brightline Identity certified under the EU-US Data Privacy "
                    "Framework; follow-the-sun support limited to directory metadata."
                ),
            ),
        ],
    },
    {
        "ref_id": "ROPA-008",
        "name": "Recruitment",
        "folder": "Corporate IT",
        "status": "privacy_draft",
        "description": (
            "Applicant tracking from job posting to hiring decision, including "
            "background checks for firmware signing key custodians."
        ),
        "information_channel": "Careers page privacy notice",
        "usage_channel": "Applicant tracking system",
        "dpia_required": True,
        "dpia_reference": "",
        "nature": [
            "privacy_collection",
            "privacy_consultation",
            "privacy_erasureOrDestruction",
        ],
        "controls": [],
        "perimeters": [],
        "purposes": [
            ("Assessing applications", "privacy_contract", None),
            (
                "Background check for signing key custodians",
                "privacy_legal_obligation",
                "privacy_substantial_public_interest",
            ),
            ("Talent pool for future openings", "privacy_consent", None),
        ],
        "personal_data": [
            (
                "CV and cover letter",
                "privacy_professional_qualifications",
                "2 years after last contact",
                "privacy_automatic_deletion",
                [],
            ),
            (
                "Interview notes and technical test results",
                "privacy_work_performance",
                "6 months after decision",
                "privacy_automatic_deletion",
                [],
            ),
            (
                "Criminal record extract",
                "privacy_criminal_records",
                "Deleted after verification",
                "privacy_manual_review_deletion",
                [],
            ),
        ],
        "subjects": [("Job applicants", "privacy_job_applicant")],
        "recipients": [
            ("Hiring managers", "privacy_internal_team"),
            ("Recruitment agency", "privacy_service_provider"),
        ],
        "contractors": [
            (
                "Talvio Recruit",
                "privacy_data_processor",
                "IE",
                "https://dpa.example.com/talvio",
            ),
        ],
        "transfers": [
            (
                "ATS hosting (Switzerland)",
                "CH",
                "privacy_adequacy_decision",
                "Swiss adequacy decision; hosting contract reviewed in 2025.",
            ),
        ],
    },
    {
        "ref_id": "ROPA-009",
        "name": "Brno plant CCTV and access badges",
        "folder": "Manufacturing",
        "status": "privacy_approved",
        "description": (
            "Video surveillance of the assembly hall, warehouse and loading bays, "
            "and badge-controlled access to the plant and the SCADA room."
        ),
        "information_channel": "Signage at every entrance; works council agreement",
        "usage_channel": "On-premise video recorder, access control system",
        "dpia_required": True,
        "dpia_reference": "DPIA-2024-07",
        "nature": [
            "privacy_recording",
            "privacy_storage",
            "privacy_erasureOrDestruction",
        ],
        "controls": ["AC.007", "AC.012"],
        "perimeters": ["PER.003"],
        "purposes": [
            (
                "Security of goods, premises and OT rooms",
                "privacy_legitimate_interests",
                None,
            ),
            (
                "Evidence for theft or sabotage investigations",
                "privacy_legitimate_interests",
                "privacy_legal_claims",
            ),
        ],
        "personal_data": [
            (
                "Video footage",
                "privacy_video_recordings",
                "14 days",
                "privacy_automatic_deletion",
                [],
            ),
            (
                "Badge entry logs",
                "privacy_location_data",
                "90 days",
                "privacy_automatic_deletion",
                ["Plant SCADA server"],
            ),
            (
                "Badge photo",
                "privacy_images_photos",
                "Until badge return",
                "privacy_manual_review_deletion",
                [],
            ),
        ],
        "subjects": [
            ("Plant staff", "privacy_employee"),
            ("Integrator and maintenance technicians", "privacy_contractor"),
            ("Drivers and visitors", "privacy_visitor"),
        ],
        "recipients": [
            ("Site security", "privacy_internal_team"),
            ("Police, on requisition", "privacy_law_enforcement"),
        ],
        "contractors": [
            ("Strazni Security", "privacy_data_processor", "CZ", ""),
        ],
        "transfers": [],
    },
    {
        "ref_id": "ROPA-010",
        "name": "Instalment payment credit checks",
        "folder": "Online Store & Payments",
        "status": "privacy_approved",
        "description": (
            f"Creditworthiness assessment run by {PAY_ENTITY} before granting "
            "3x or 10x instalment payments at checkout; automated scoring with a "
            "human review on request."
        ),
        "information_channel": "Instalment terms and pre-contractual information",
        "usage_channel": "Checkout instalment flow, credit decision engine",
        "dpia_required": True,
        "dpia_reference": "DPIA-2025-05",
        "nature": [
            "privacy_collection",
            "privacy_consultation",
            "privacy_alignmentOrCombination",
        ],
        "controls": ["AC.016", "AC.009"],
        "perimeters": ["PER.002"],
        "purposes": [
            (
                "Creditworthiness assessment (consumer credit law)",
                "privacy_legal_obligation",
                None,
            ),
            ("Managing the instalment plan", "privacy_contract", None),
            ("Anti-money laundering checks", "privacy_legal_obligation", None),
        ],
        "personal_data": [
            (
                "Applicant identity and ID document",
                "privacy_government_identifiers",
                "5 years after the plan ends (AML)",
                "privacy_legal_regulatory_hold",
                ["Store checkout and payments"],
            ),
            (
                "Declared income and expenses",
                "privacy_financial_data",
                "5 years after the plan ends",
                "privacy_legal_regulatory_hold",
                ["Store checkout and payments"],
            ),
            (
                "Credit bureau score",
                "privacy_financial_data",
                "Duration of the plan",
                "privacy_automatic_deletion",
                ["Store checkout and payments"],
            ),
            (
                "Repayment history",
                "privacy_transaction_history",
                "5 years after the plan ends",
                "privacy_legal_regulatory_hold",
                ["Store checkout and payments", "PostgreSQL primary"],
            ),
        ],
        "subjects": [("Instalment applicants", "privacy_customer")],
        "recipients": [
            (f"{PAY_ENTITY} credit risk team", "privacy_subsidiary"),
            ("Credit bureau", "privacy_business_partner"),
            (
                "Payment institution supervisor, on request",
                "privacy_regulatory_authority",
            ),
        ],
        "contractors": [
            ("Credora Bureau", "privacy_independent_controller", "FR", ""),
            (
                "Pellion Payments",
                "privacy_data_processor",
                "BE",
                "https://dpa.example.com/pellion",
            ),
        ],
        "transfers": [],
    },
    {
        "ref_id": "ROPA-011",
        "name": "Keystone hub v3 beta programme",
        "folder": "Connected Products",
        "status": "privacy_draft",
        "description": (
            "Recruitment of 300 beta testers, detailed diagnostics upload and "
            "feedback interviews for the Keystone hub v3 pre-release."
        ),
        "information_channel": "Beta participation agreement",
        "usage_channel": "Beta portal, device cloud diagnostics bucket",
        "dpia_required": False,
        "nature": ["privacy_collection", "privacy_use", "privacy_storage"],
        "controls": ["AC.006"],
        "perimeters": ["PER.004"],
        "purposes": [
            ("Running the beta programme", "privacy_contract", None),
            ("Usability research interviews", "privacy_consent", None),
        ],
        "personal_data": [
            (
                "Tester contact details",
                "privacy_contact_details",
                "6 months after general availability",
                "privacy_automatic_deletion",
                [],
            ),
            (
                "Verbose hub diagnostics",
                "privacy_device_information",
                "Until general availability",
                "privacy_automatic_deletion",
                ["S3 evidence bucket"],
            ),
            (
                "Interview feedback",
                "privacy_feedback",
                "12 months",
                "privacy_anonymization",
                [],
            ),
        ],
        "subjects": [("Beta testers", "privacy_customer")],
        "recipients": [
            ("Keystone product team", "privacy_internal_team"),
            ("Hardware design office (Eindhoven)", "privacy_internal_team"),
        ],
        "contractors": [
            (
                "Kestrava Cloud",
                "privacy_data_processor",
                "DE",
                "https://dpa.example.com/kestrava",
            ),
        ],
        "transfers": [],
    },
]

# ref_id, name, type, status, requested offset, processings, observation.
# Due dates follow the one-month GDPR deadline, extended by two months for
# complex requests. The request lives in its first processing's folder.
RIGHT_REQUESTS = [
    (
        "DSR-2026-001",
        "Access request — Lookout clips of a camera owner",
        "access",
        "done",
        -95,
        ["ROPA-002", "ROPA-001"],
        "Clip archive and account data exported via the secure portal on day 19.",
    ),
    (
        "DSR-2026-002",
        "Access to camera footage — visitor filmed by a customer camera",
        "access",
        "in_progress",
        -12,
        ["ROPA-002"],
        (
            "Requester is not the account holder: the camera owner is the "
            "controller of the footage, we only host it. Requester referred to "
            "the owner; clip preserved for 30 days pending a police request."
        ),
    ),
    (
        "DSR-2026-003",
        "Erasure after resale of a Kelvin thermostat",
        "deletion",
        "done",
        -48,
        ["ROPA-003"],
        (
            "Previous owner sold the device second-hand: energy history erased, "
            "device unpaired from the old account before the buyer paired it."
        ),
    ),
    (
        "DSR-2026-004",
        "Erasure request — former newsletter subscriber",
        "deletion",
        "done",
        -60,
        ["ROPA-006"],
        "Suppressed from all lists; email hash kept on the do-not-contact list.",
    ),
    (
        "DSR-2026-005",
        "Rectification of delivery address",
        "rectification",
        "in_progress",
        -18,
        ["ROPA-001"],
        "",
    ),
    (
        "DSR-2026-006",
        "Portability of two years of Kelvin energy history",
        "portability",
        "in_progress",
        -9,
        ["ROPA-003"],
        "CSV export of readings being generated; switching to a heat-pump vendor.",
    ),
    (
        "DSR-2026-007",
        "Objection to companion app analytics",
        "objection",
        "done",
        -33,
        ["ROPA-004"],
        "Consent withdrawn in-app; Fennick deletion request confirmed on day 6.",
    ),
    (
        "DSR-2026-008",
        "Objection to call recording",
        "objection",
        "new",
        -3,
        ["ROPA-005"],
        "",
    ),
    (
        "DSR-2026-009",
        "Human review of a refused instalment application",
        "other",
        "on_hold",
        -40,
        ["ROPA-010"],
        (
            "Article 22 request for human intervention. Extended by two months: "
            "awaiting the applicant's updated income statements."
        ),
    ),
    (
        "DSR-2026-010",
        "Restriction of processing — disputed payroll data",
        "restriction",
        "new",
        -1,
        ["ROPA-007"],
        "",
    ),
]


def at(ctx, offset, hour, minute=0):
    return datetime.combine(ctx.day(offset), time(hour, minute), tzinfo=UTC)


@register
class PrivacyBuilder(DemoBuilder):
    """GDPR record of processing activities, right requests and breaches."""

    name = "privacy"
    depends = ("core",)
    covers: ClassVar[dict] = {
        Processing: "folder",
        Purpose: "folder",
        PersonalData: "folder",
        DataSubject: "folder",
        DataRecipient: "folder",
        DataContractor: "folder",
        DataTransfer: "folder",
        RightRequest: "folder",
        DataBreach: "folder",
    }

    def stamps(self, ctx):
        scope = {"folder__in": ctx.folders()}
        child = ("processing__ref_id", "name")
        return [
            (Processing, scope, ("ref_id",)),
            (Purpose, scope, child),
            (PersonalData, scope, child),
            (DataSubject, scope, child),
            (DataRecipient, scope, child),
            (DataContractor, scope, child),
            (DataTransfer, scope, child),
            (RightRequest, scope, ("ref_id",)),
            (DataBreach, scope, ("ref_id",)),
        ]

    def build(self, ctx):
        processings = self.build_processings(ctx)
        self.build_right_requests(ctx, processings)
        self.build_breaches(ctx, processings)
        ctx.out(f"{len(processings)} processings seeded")

    def build_processings(self, ctx):
        folders = {
            folder.name: folder
            for folder in Folder.objects.filter(parent_folder=ctx.domain)
        }
        terms = {
            (term.field_path, term.name): term
            for term in Terminology.objects.filter(
                field_path__in=[
                    Terminology.FieldPath.PROCESSING_NATURE,
                    Terminology.FieldPath.PERSONAL_DATA_CATEGORY,
                ]
            )
        }
        nature_path = Terminology.FieldPath.PROCESSING_NATURE
        category_path = Terminology.FieldPath.PERSONAL_DATA_CATEGORY
        assets = {asset.name: asset for asset in ctx.refs["assets"]}
        controls = {control.ref_id: control for control in ctx.refs["controls"]}
        perimeters = {p.ref_id: p for p in ctx.refs["perimeters"]}
        processings = {}
        for spec in PROCESSINGS:
            folder = folders.get(spec["folder"], ctx.domain)
            processing, created = Processing.objects.get_or_create(
                name=spec["name"],
                folder=folder,
                defaults={
                    "ref_id": spec["ref_id"],
                    "status": spec["status"],
                    "description": spec["description"],
                    "information_channel": spec["information_channel"],
                    "usage_channel": spec["usage_channel"],
                    "dpia_required": spec["dpia_required"],
                    "dpia_reference": spec.get("dpia_reference", ""),
                },
            )
            processings[spec["ref_id"]] = processing
            if not created:
                continue
            processing.nature.set(
                [
                    terms[(nature_path, n)]
                    for n in spec["nature"]
                    if (nature_path, n) in terms
                ]
            )
            processing.associated_controls.set([controls[r] for r in spec["controls"]])
            processing.perimeters.set([perimeters[r] for r in spec["perimeters"]])
            for name, basis, condition in spec["purposes"]:
                Purpose.objects.create(
                    processing=processing,
                    name=name,
                    legal_basis=basis,
                    article_9_condition=condition,
                )
            for name, category, retention, policy, linked in spec["personal_data"]:
                term = terms.get((category_path, category))
                if term is None:
                    ctx.err(f"personal data category {category} missing")
                    continue
                data = PersonalData.objects.create(
                    processing=processing,
                    name=name,
                    category=term,
                    retention=retention,
                    deletion_policy=policy,
                )
                data.assets.set([assets[n] for n in linked])
            for name, category in spec["subjects"]:
                DataSubject.objects.create(
                    processing=processing, name=name, category=category
                )
            for name, category in spec["recipients"]:
                DataRecipient.objects.create(
                    processing=processing, name=name, category=category
                )
            for name, relationship, country, link in spec["contractors"]:
                DataContractor.objects.create(
                    processing=processing,
                    name=name,
                    relationship_type=relationship,
                    country=country,
                    documentation_link=link,
                )
            for name, country, mechanism, guarantees in spec["transfers"]:
                DataTransfer.objects.create(
                    processing=processing,
                    name=name,
                    country=country,
                    transfer_mechanism=mechanism,
                    guarantees=guarantees,
                )
        return processings

    def build_right_requests(self, ctx, processings):
        for (
            ref_id,
            name,
            request_type,
            status,
            offset,
            linked,
            observation,
        ) in RIGHT_REQUESTS:
            extended = status == "on_hold"
            request, created = RightRequest.objects.get_or_create(
                name=name,
                folder=processings[linked[0]].folder,
                defaults={
                    "ref_id": ref_id,
                    "request_type": request_type,
                    "status": status,
                    "requested_on": ctx.day(offset),
                    "due_date": ctx.day(offset)
                    + timedelta(days=90 if extended else 30),
                    "observation": observation,
                },
            )
            if created:
                request.processings.set([processings[r] for r in linked])

    def build_breaches(self, ctx, processings):
        controls = {control.ref_id: control for control in ctx.refs["controls"]}
        breaches = [
            {
                "ref_id": "DB-2025-01",
                "name": "Unencrypted USB key lost by payroll contractor",
                "folder": processings["ROPA-007"].folder,
                "description": (
                    "A Pavlek Payroll consultant reported the loss of a USB key "
                    "holding a payroll export for the Brno plant."
                ),
                "discovered_on": at(ctx, -150, 10, 30),
                "breach_type": "privacy_loss",
                "risk_level": "privacy_high_risk",
                "status": "privacy_closed",
                "affected_subjects_count": 412,
                "affected_personal_data_count": 1648,
                "authority_notified_on": at(ctx, -148, 16, 0),
                "authority_notification_ref": "UOOU-2025-0418",
                "subjects_notified_on": at(ctx, -145, 9, 0),
                "potential_consequences": (
                    "Exposure of salaries and bank details; risk of phishing and "
                    "identity fraud against plant staff."
                ),
                "observation": (
                    "Notified to the Czech authority (UOOU) as the plant is the "
                    "establishment concerned. Removable media blocked on payroll "
                    "workstations; contractor DPA amended."
                ),
                "processings": ["ROPA-007"],
                "data": ["Bank details", "Salary and bonuses", "Employee identity"],
                "controls": ["AC.005", "AC.004"],
            },
            {
                "ref_id": "DB-2025-02",
                "name": "Analytics SDK sent events before consent",
                "folder": processings["ROPA-004"].folder,
                "description": (
                    "Companion app 4.12 initialised the Fennick Analytics SDK "
                    "before the consent prompt was answered, for about 9 days."
                ),
                "discovered_on": at(ctx, -120, 14, 0),
                "breach_type": "privacy_unauthorized_disclosure",
                "risk_level": "privacy_no_risk",
                "status": "privacy_closed",
                "affected_subjects_count": 23800,
                "affected_personal_data_count": 47600,
                "authority_notified_on": None,
                "authority_notification_ref": "",
                "subjects_notified_on": None,
                "potential_consequences": (
                    "Pseudonymous app identifiers and phone models only; unlikely "
                    "to result in a risk to users."
                ),
                "observation": (
                    "Events purged by Fennick on day 2. Consent gate now covered by "
                    "an automated UI test in the release pipeline."
                ),
                "processings": ["ROPA-004"],
                "data": ["App instance identifier", "Phone model and OS version"],
                "controls": ["AC.006"],
            },
            {
                "ref_id": "DB-2026-01",
                "name": "Lookout clips shown to the wrong accounts",
                "folder": processings["ROPA-002"].folder,
                "description": (
                    "A caching bug in a device cloud release served event "
                    "thumbnails and some clips of other households in the "
                    "companion app timeline for 47 minutes."
                ),
                "discovered_on": at(ctx, -26, 20, 15),
                "breach_type": "privacy_unauthorized_disclosure",
                "risk_level": "privacy_high_risk",
                "status": "privacy_subjects_notified",
                "affected_subjects_count": 1312,
                "affected_personal_data_count": 2890,
                "authority_notified_on": at(ctx, -24, 11, 0),
                "authority_notification_ref": "CNIL-2026-0217",
                "subjects_notified_on": at(ctx, -22, 9, 30),
                "potential_consequences": (
                    "Footage of home interiors, children and daily routines "
                    "seen by strangers; risk of burglary targeting and distress."
                ),
                "observation": (
                    "Release rolled back within the hour; clip URLs now signed per "
                    "account. Staged rollout gate extended to the timeline service."
                ),
                "processings": ["ROPA-002"],
                "data": ["Video clips", "Event thumbnails", "Motion event metadata"],
                "controls": ["AC.014", "AC.010"],
            },
            {
                "ref_id": "DB-2026-02",
                "name": "Support agent account takeover at Mireo Support",
                "folder": processings["ROPA-005"].folder,
                "description": (
                    "A phished Mireo Support agent account was used to browse "
                    "camera tickets and request password resets for customer "
                    "accounts."
                ),
                "discovered_on": at(ctx, -14, 8, 50),
                "breach_type": "privacy_unauthorized_access",
                "risk_level": "privacy_risk",
                "status": "privacy_authority_notified",
                "affected_subjects_count": 640,
                "affected_personal_data_count": 1920,
                "authority_notified_on": at(ctx, -12, 15, 30),
                "authority_notification_ref": "CNIL-2026-0288",
                "subjects_notified_on": None,
                "potential_consequences": (
                    "Addresses and owned cameras exposed; 11 reset attempts "
                    "blocked by the second factor on the customer account."
                ),
                "observation": (
                    "Agent sessions now require phishing-resistant MFA; reset "
                    "requests from support need customer confirmation. Notice to "
                    "customers under legal review."
                ),
                "processings": ["ROPA-005"],
                "data": ["Contact details", "Support tickets and chat transcripts"],
                "controls": ["AC.004", "AC.001"],
            },
            {
                "ref_id": "DB-2026-03",
                "name": "Credential stuffing on online store accounts",
                "folder": processings["ROPA-001"].folder,
                "description": (
                    "Spike of successful logins from a residential proxy network; "
                    "attackers viewed order histories and delivery addresses."
                ),
                "discovered_on": at(ctx, -9, 6, 45),
                "breach_type": "privacy_unauthorized_access",
                "risk_level": "privacy_risk",
                "status": "privacy_authority_notified",
                "affected_subjects_count": 1870,
                "affected_personal_data_count": 5610,
                "authority_notified_on": at(ctx, -7, 14, 20),
                "authority_notification_ref": "CNIL-2026-0301",
                "subjects_notified_on": None,
                "potential_consequences": (
                    "Targeted phishing using genuine order details; fraudulent "
                    "address changes before deliveries."
                ),
                "observation": (
                    "Forced password reset done and bot protection tightened on "
                    "the login form. Customer notification pending."
                ),
                "processings": ["ROPA-001"],
                "data": [
                    "Customer identity",
                    "Delivery address",
                    "Order and warranty history",
                ],
                "controls": ["AC.001", "AC.010"],
            },
            {
                "ref_id": "DB-2026-04",
                "name": "Launch email sent with recipients in visible copy",
                "folder": processings["ROPA-006"].folder,
                "description": (
                    "A manual test send of the Keystone hub v3 teaser exposed 42 "
                    "trade-fair prospect addresses to each other."
                ),
                "discovered_on": at(ctx, -2, 15, 10),
                "breach_type": "privacy_unauthorized_disclosure",
                "risk_level": "privacy_no_risk",
                "status": "privacy_under_investigation",
                "affected_subjects_count": 42,
                "affected_personal_data_count": 42,
                "authority_notified_on": None,
                "authority_notification_ref": "",
                "subjects_notified_on": None,
                "potential_consequences": (
                    "Business email addresses only; unlikely to result in a risk "
                    "to the individuals."
                ),
                "observation": (
                    "Documented in the internal breach register; no notification "
                    "expected."
                ),
                "processings": ["ROPA-006"],
                "data": ["Email address"],
                "controls": ["AC.006"],
            },
        ]
        for spec in breaches:
            linked = spec.pop("processings")
            data_names = spec.pop("data")
            control_refs = spec.pop("controls")
            name = spec.pop("name")
            folder = spec.pop("folder")
            breach, created = DataBreach.objects.get_or_create(
                name=name, folder=folder, defaults=spec
            )
            if not created:
                continue
            breach.affected_processings.set([processings[r] for r in linked])
            breach.affected_personal_data.set(
                PersonalData.objects.filter(
                    processing__in=[processings[r] for r in linked],
                    name__in=data_names,
                ).order_by("name")
            )
            breach.remediation_measures.set([controls[r] for r in control_refs])
