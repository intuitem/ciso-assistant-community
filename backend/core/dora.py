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

DORA_BINARY_CHOICES = [
    ("eba_BT:x28", "Yes"),
    ("eba_BT:x29", "No"),
]

DORA_RELIANCE_CHOICES = [
    ("eba_ZZ:x794", "Not significant"),
    ("eba_ZZ:x795", "Low reliance"),
    ("eba_ZZ:x796", "Material reliance"),
    ("eba_ZZ:x797", "Full reliance"),
]

DORA_SENSITIVENESS_CHOICES = [
    ("eba_ZZ:x791", "Low"),
    ("eba_ZZ:x792", "Medium"),
    ("eba_ZZ:x793", "High"),
]

DORA_YES_NO_ASSESSMENT_CHOICES = [
    ("eba_BT:x28", "Yes"),
    ("eba_BT:x29", "No"),
    ("eba_BT:x21", "Assessment not performed"),
]

DORA_DISCONTINUING_IMPACT_CHOICES = [
    ("eba_ZZ:x791", "Low"),
    ("eba_ZZ:x792", "Medium"),
    ("eba_ZZ:x793", "High"),
    ("eba_ZZ:x799", "Assessment not performed"),
]

DORA_ENTITY_NATURE_CHOICES = [
    ("eba_ZZ:x838", "branch of a financial entity"),
    ("eba_ZZ:x839", "not a branch"),
]

DORA_PROVIDER_PERSON_TYPE_CHOICES = [
    ("eba_CT:x212", "Legal person, excluding individual acting in a business capacity"),
    ("eba_CT:x213", "Individual acting in a business capacity"),
]

DORA_SUBSTITUTABILITY_CHOICES = [
    ("eba_ZZ:x959", "Not substitutable"),
    ("eba_ZZ:x962", "Easily substitutable"),
    ("eba_ZZ:x961", "Medium complexity in terms of substitutability"),
    ("eba_ZZ:x960", "Highly complex substitutability"),
]

DORA_NON_SUBSTITUTABILITY_REASON_CHOICES = [
    ("eba_ZZ:x963", "Lack of real alternatives"),
    ("eba_ZZ:x964", "Difficulties in migrating or reintegrating"),
    (
        "eba_ZZ:x965",
        "Lack of real alternatives and difficulties in migrating or reintegrating",
    ),
]

DORA_REINTEGRATION_POSSIBILITY_CHOICES = [
    ("eba_ZZ:x798", "Easy"),
    ("eba_ZZ:x966", "Difficult"),
    ("eba_ZZ:x967", "Highly complex"),
]

DORA_LICENSED_ACTIVITY_CHOICES = [
    (
        "eba_TA:x185",
        "Non-Life Insurance: Classes 1 and 2: 'Accident and Health Insurance'",
    ),
    (
        "eba_TA:x186",
        "Non-Life Insurance: Classes 1 (fourth indent), 3, 7 and 10: 'Motor Insurance'",
    ),
    (
        "eba_TA:x187",
        "Non-Life Insurance: Classes 1 (fourth indent), 4, 6, 7 and 12: 'Marine and Transport Insurance'",
    ),
    (
        "eba_TA:x188",
        "Non-Life Insurance: Classes 1 (fourth indent), 5, 7 and 11: 'Aviation Insurance'",
    ),
    (
        "eba_TA:x189",
        "Non-Life Insurance: Classes 8 and 9: 'Insurance against Fire and other Damage to Property'",
    ),
    (
        "eba_TA:x190",
        "Non-Life Insurance: Classes 10, 11, 12 and 13: 'Liability Insurance'",
    ),
    (
        "eba_TA:x191",
        "Non-Life Insurance: Classes 14 and 15: 'Credit and Suretyship Insurance'",
    ),
    (
        "eba_TA:x192",
        "Non-Life Insurance: All classes, at the choice of the Member States, which shall notify the other Member States and the Commission of their choice",
    ),
    (
        "eba_TA:x193",
        "Life Insurance: The life insurance referred to in points (a)(i), (ii) and (iii) of Article 2(3) excluding those referred to in II and III",
    ),
    ("eba_TA:x194", "Life Insurance: Marriage assurance, birth assurance"),
    (
        "eba_TA:x195",
        "Life Insurance: The insurance referred to in points (a)(i) and (ii) of Article 2(3), which are linked to investment funds",
    ),
    (
        "eba_TA:x196",
        "Life Insurance: Permanent health insurance, referred to in point (a)(iv) of Article 2(3)",
    ),
    (
        "eba_TA:x197",
        "Life Insurance: Tontines, referred to in point (b)(i) of Article 2(3)",
    ),
    (
        "eba_TA:x198",
        "Life Insurance: Capital redemption operations, referred to in point (b)(ii) of Article 2(3)",
    ),
    (
        "eba_TA:x199",
        "Life Insurance: Management of group pension funds, referred to in point (b)(iii) and (iv) of Article 2(3)",
    ),
    (
        "eba_TA:x200",
        "Life Insurance: The operations referred to in point (b)(v) of Article 2(3)",
    ),
    ("eba_TA:x201", "Life Insurance: The operations referred to in Article 2(3)(c)"),
    ("eba_TA:x163", "Lending activities"),
    ("eba_TA:x164", "Financial leasing"),
    ("eba_TA:x165", "Issuing and administering other means of payment"),
    ("eba_TA:x166", "Guarantees and commitments"),
    (
        "eba_TA:x167",
        "Guarantees and commitments related to securities lending and borrowing, within the meaning of point 6 of Annex I to Directive 2013/36/EU",
    ),
    ("eba_TA:x168", "Trading for own account or for account of customers"),
    (
        "eba_TA:x169",
        "Participation in securities issues and the provision of services relating to such issues",
    ),
    ("eba_TA:x28", "Payment services"),
    ("eba_TA:x170", "Advisory services"),
    ("eba_TA:x171", "Money broking"),
    ("eba_TA:x172", "Portfolio management and advice"),
    ("eba_TA:x173", "Dealing on own account"),
    ("eba_TA:x174", "Safekeeping and administration of securities"),
    (
        "eba_TA:x175",
        "Safekeeping and administration of financial instruments for the account of clients",
    ),
    (
        "eba_TA:x176",
        "safe-keeping and administration in relation to shares or units of collective investment undertakings",
    ),
    (
        "eba_TA:x177",
        "non-core services (safekeeping and administration in relation to units of collective investment undertakings)",
    ),
    ("eba_TA:x178", "Safe custody services"),
    ("eba_TA:x179", "Credit reference services"),
    ("eba_TA:x180", "Issuing electronic money"),
    (
        "eba_TA:x181",
        "reception and transmission of orders for crypto-assets on behalf of clients",
    ),
    ("eba_TA:x182", "Portfolio management on crypto-assets"),
    ("eba_TA:x183", "management of portfolios of investments (AIFMD)"),
    ("eba_TA:x184", "management of portfolios of investments (UCITSD)"),
    ("eba_TA:x202", "insurance distribution"),
    ("eba_TA:x203", "reinsurance distribution"),
    ("eba_TA:x204", "Investment services related to the underlying of the derivatives"),
    (
        "eba_TA:x205",
        "Retirement-benefit related operations and activities arising therefrom",
    ),
    ("eba_TA:x206", "issuance of credit ratings"),
    ("eba_TA:x207", "administering the arrangements for determining a benchmark"),
    (
        "eba_TA:x208",
        "collecting, analysing or processing input data for the purpose of determining a benchmark",
    ),
    (
        "eba_TA:x209",
        "determining a benchmark through the application of a formula or other method of calculation or by an assessment of input data provided for that purpose",
    ),
    ("eba_TA:x210", "publication of benchmark"),
    ("eba_TA:x211", "Provision of crowdfunding services"),
    ("eba_TA:x212", "ancillary non-securitisation services"),
    ("eba_TA:x213", "ancillary securitisation services"),
    (
        "eba_TA:x214",
        "collection and maintenance of the records of derivatives (non-SFTs)",
    ),
    ("eba_TA:x215", "collection and maintenance of the records of SFTs"),
    ("eba_TA:x216", "collection and maintenance of the records of securitisations"),
    ("eba_TA:x217", "activity as approved publication arrangement"),
    ("eba_TA:x218", "activity as consolidated tape provider"),
    ("eba_TA:x219", "activity as approved reporting mechanism"),
    (
        "eba_TA:x220",
        "Services enabling cash to be placed on a payment account as well as all the operations required for operating a payment account",
    ),
    (
        "eba_TA:x221",
        "Services enabling cash withdrawals from a payment account as well as all the operations required for operating a payment account",
    ),
    (
        "eba_TA:x222",
        "Execution of payment transactions, including transfers of funds on a payment account with the user's payment service provider or with another payment service provider",
    ),
    (
        "eba_TA:x223",
        "Execution of payment transactions where the funds are covered by a credit line for a payment service user",
    ),
    (
        "eba_TA:x224",
        "Issuing of payment instruments and/or acquiring of payment transactions",
    ),
    ("eba_TA:x225", "Money remittance"),
    ("eba_TA:x226", "Payment initiation services"),
    ("eba_TA:x227", "Account information services"),
    (
        "eba_TA:x228",
        "Providing custody and administration of crypto-assets on behalf of clients",
    ),
    ("eba_TA:x229", "operation of a trading platform for crypto-assets"),
    ("eba_TA:x230", "Operation of a Regulated Market"),
    ("eba_TA:x231", "exchange of crypto-assets for funds"),
    ("eba_TA:x232", "exchange of crypto-assets for other crypto-assets"),
    ("eba_TA:x233", "execution of orders for crypto-assets on behalf of clients"),
    ("eba_TA:x234", "placing of crypto-assets"),
    ("eba_TA:x235", "providing advice on crypto-assets"),
    (
        "eba_TA:x236",
        "providing transfer services for crypto-assets on behalf of clients",
    ),
    ("eba_TA:x237", "issuance of asset-referenced tokens"),
    ("eba_TA:x238", "notary service"),
    ("eba_TA:x239", "central maintenance service"),
    ("eba_TA:x240", "settlement service"),
    (
        "eba_TA:x241",
        "Organising a securities lending mechanism, as agent among participants of a securities settlement system",
    ),
    ("eba_TA:x242", "collateral management services"),
    ("eba_TA:x243", "general collateral management services"),
    (
        "eba_TA:x244",
        "Establishing CSD links, providing, maintaining or operating securities accounts in relation to the settlement service, collateral management, other ancillary services",
    ),
    (
        "eba_TA:x245",
        "Settlement matching, instruction routing, trade confirmation, trade verification",
    ),
    ("eba_TA:x246", "Services related to shareholders' registers"),
    (
        "eba_TA:x247",
        "Supporting the processing of corporate actions, including tax, general meetings and information services",
    ),
    (
        "eba_TA:x248",
        "New issue services, including allocation and management of ISIN codes and similar codes",
    ),
    (
        "eba_TA:x249",
        "Instruction routing and processing, fee collection and processing and related reporting",
    ),
    ("eba_TA:x250", "Providing regulatory reporting"),
    (
        "eba_TA:x251",
        "Providing information, data and statistics to market/census bureaus or other governmental or inter-governmental entities",
    ),
    ("eba_TA:x252", "Providing IT services"),
    (
        "eba_TA:x253",
        "Providing cash accounts to, and accepting deposits from, participants in a securities settlement system and holders of securities accounts, within the meaning of point 1 of Annex I to Directive 2013/36/EU",
    ),
    (
        "eba_TA:x254",
        "Providing cash credit for reimbursement no later than the following business day, cash lending to pre-finance corporate actions and lending securities to holders of securities accounts, within the meaning of point 2 of Annex I to Directive 2013/36/EU",
    ),
    (
        "eba_TA:x255",
        "Payment services involving processing of cash and foreign exchange transactions, within the meaning of point 4 of Annex I to Directive 2013/36/EU",
    ),
    (
        "eba_TA:x256",
        "Treasury activities involving foreign exchange and transferable securities related to managing participants' long balances",
    ),
    (
        "eba_TA:x257",
        "Any other NCA-permitted non-banking-type ancillary services not specified in Annex of Regulation (EU) No 909/2014 (CSDR) - Section B",
    ),
    (
        "eba_TA:x258",
        "Any other NCA-permitted Banking-type ancillary services not specified in Annex of Regulation (EU) No 909/2014 (CSDR) - Section C",
    ),
    ("eba_TA:x259", "interposition between counterparties"),
    ("eba_TA:x260", "risk management"),
    ("eba_TA:x261", "legal and fund management accounting services"),
    ("eba_TA:x262", "customer inquiries"),
    ("eba_TA:x263", "valuation and pricing, including tax returns"),
    ("eba_TA:x264", "regulatory compliance monitoring"),
    ("eba_TA:x265", "maintenance of unit-/shareholder register"),
    ("eba_TA:x266", "unit/shares issues and redemptions"),
    ("eba_TA:x267", "maintenance of unit-holder register"),
    ("eba_TA:x268", "unit issues and redemptions"),
    ("eba_TA:x269", "contract settlements (including certificate dispatch)"),
    ("eba_TA:x270", "distribution of income"),
    ("eba_TA:x271", "record keeping"),
    ("eba_TA:x272", "Marketing"),
    ("eba_TA:x273", "services necessary to meet the fiduciary duties of the AIFM"),
    (
        "eba_TA:x274",
        "investment advice concerning one or more of the instruments listed in Annex I, Section C to Directive 2004/39/EC",
    ),
    ("eba_TA:x275", "Ancillary services"),
    ("eba_TA:x104", "Foreign exchange services"),
    ("eba_TA:x133", "Reception and transmission of orders"),
    ("eba_TA:x134", "Execution of orders on behalf of clients"),
    ("eba_TA:x136", "Portfolio management"),
    ("eba_TA:x137", "Investment advice"),
    (
        "eba_TA:x138",
        "Underwriting of financial instruments and/or placing of financial instruments on a firm commitment basis",
    ),
    ("eba_TA:x139", "Placing of financial instruments without a firm commitment basis"),
    ("eba_TA:x140", "Operation of an MTF"),
    ("eba_TA:x141", "Operation of an OTF"),
    ("eba_TA:x143", "Granting credits or loans to investors"),
    (
        "eba_TA:x144",
        "Advice to undertakings on capital structure, industrial strategy and related matters and advice and services relating to mergers and the purchase of undertakings",
    ),
    ("eba_TA:x146", "Investment research and financial analysis"),
    ("eba_TA:x147", "Services related to underwriting"),
    ("eba_TA:x162", "Taking deposits and other repayable funds"),
]
