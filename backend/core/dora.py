"""
DORA (Digital Operational Resilience Act) specific constants
"""

DORA_ENTITY_TYPE_CHOICES = [
    ("eba_CT:x12", "Credit institutions"),
    ("eba_CT:x599", "Investment firms"),
    ("eba_CT:x643", "Central counterparties (CCPs)"),
    ("eba_CT:x639", "Asset management companies"),
    ("eba_CT:x301", "Account information service providers"),
    ("eba_CT:x302", "Electronic money institutions"),
    ("eba_CT:x303", "Crypto-asset service providers"),
    ("eba_CT:x304", "Central security depository"),
    ("eba_CT:x305", "Trading venues"),
    ("eba_CT:x306", "Trade repositories"),
    ("eba_CT:x300", "Payment institution"),
    ("eba_CT:x316", "Other financial entity"),
    ("eba_CT:x315", "Securitisation repository"),
    ("eba_CT:x314", "Crowdfunding service providers"),
    ("eba_CT:x313", "Administrator of critical benchmarks"),
    ("eba_CT:x312", "Credit rating agency"),
    ("eba_CT:x311", "Institutions for occupational retirement provision"),
    (
        "eba_CT:x320",
        "Insurance intermediaries, reinsurance intermediaries and ancillary insurance intermediaries",
    ),
    ("eba_CT:x309", "Insurance and reinsurance undertakings"),
    ("eba_CT:x308", "Data reporting service providers"),
    ("eba_CT:x307", "Managers of alternative investment funds"),
    (
        "eba_CT:x318",
        "Non-financial entity: Other than ICT intra-group service provider",
    ),
    ("eba_CT:x317", "Non-financial entity: ICT intra-group service provider"),
    ("eba_CT:x310", "Issuers of asset-referenced tokens"),
]

DORA_ENTITY_HIERARCHY_CHOICES = [
    ("eba_RP:x53", "Ultimate parent"),
    ("eba_RP:x551", "Parent other than ultimate parent"),
    ("eba_RP:x56", "Subsidiary"),
    ("eba_RP:x21", "Entities other than entities of the group"),
    ("eba_RP:x210", "Outsourcing"),
]

DORA_CONTRACTUAL_ARRANGEMENT_CHOICES = [
    ("eba_CO:x1", "Standalone arrangement"),
    ("eba_CO:x2", "Overarching arrangement"),
    ("eba_CO:x3", "Subsequent or associated arrangement"),
]

TERMINATION_REASON_CHOICES = [
    ("eba_CO:x4", "Termination not for cause: Expired and not renewed"),
    (
        "eba_CO:x5",
        "Termination for cause: Provider in breach of applicable law, regulations or contractual provisions",
    ),
    (
        "eba_CO:x6",
        "Termination for cause: Identified impediments of the provider capable of altering the supported function",
    ),
    (
        "eba_CO:x7",
        "Termination for cause: Provider's weaknesses regarding the management and security of sensitive data or information",
    ),
    ("eba_CO:x8", "Termination: As requested by the competent authority"),
    ("eba_CO:x9", "Other reasons for termination"),
]

DORA_ICT_SERVICE_CHOICES = [
    ("eba_TA:S01", "ICT project management"),
    ("eba_TA:S02", "ICT Development"),
    ("eba_TA:S03", "ICT help desk and first level support"),
    ("eba_TA:S04", "ICT security management services"),
    ("eba_TA:S05", "Provision of data"),
    ("eba_TA:S06", "Data analysis"),
    ("eba_TA:S07", "ICT, facilities and hosting services (excluding Cloud services)"),
    ("eba_TA:S08", "Computation"),
    ("eba_TA:S09", "Non-Cloud Data storage"),
    ("eba_TA:S10", "Telecom carrier"),
    ("eba_TA:S11", "Network infrastructure"),
    ("eba_TA:S12", "Hardware and physical devices"),
    ("eba_TA:S13", "Software licencing (excluding SaaS)"),
    ("eba_TA:S14", "ICT operation management (including maintenance)"),
    ("eba_TA:S15", "ICT Consulting"),
    ("eba_TA:S16", "ICT Risk management"),
    ("eba_TA:S17", "Cloud services: IaaS"),
    ("eba_TA:S18", "Cloud services: PaaS"),
    ("eba_TA:S19", "Cloud services: SaaS"),
]
