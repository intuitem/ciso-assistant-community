# DORA Register of Information (RoI) — Field Mapping Specification

> **Source of truth** for the mapping between the EBA XLS Master Template columns and CISO Assistant data model fields.
> All codification values come from `backend/core/dora.py`. Export logic lives in `backend/tprm/dora_export.py`.

---

## 1. Purpose and scope

This document describes every column of every tab in the DORA Register of Information (RoI), as defined by the EBA XLS Master Template. For each column it specifies:

- the data type and, when applicable, the closed set of allowed values (LIST code);
- the CISO Assistant model field that supplies the value;
- any transformation applied at export time (prefixing, sentinel dates, auto-computation).

**Audience**: contributors working on the DORA export, AI agents generating or validating RoI data, QA engineers writing regression tests.

**Relationship to the EBA template**: the column codes (`b_XX.XX.XXXX`) and LIST identifiers (`LIST0101040`, `LISTANNEXIII`, …) match the official EBA ITS template. CSV files produced by the export use short header codes (`c0010`, `c0020`, …) that map 1-to-1 to these column codes.

---

## 2. Data model overview

### 2.1 Core objects

| Object | Description |
|---|---|
| **Entity** | A legal entity (financial institution, branch, or ICT provider). Holds LEI, country, DORA entity type/hierarchy, competent authority, total assets, person type. |
| **Contract** | A contractual arrangement with an ICT service provider. Links a beneficiary entity to a provider entity. Holds arrangement type, dates, termination reason, notice periods, governing law country, annual expense. |
| **Solution** | An ICT service delivered under a contract. Holds ICT service type, data storage/location, sensitiveness, reliance, substitutability, exit plan, reintegration, discontinuing impact, alternative providers. |
| **Asset** | A business function (when `is_business_function=True`). Holds licensed activity, criticality assessment, RTO, RPO, discontinuing impact. Linked to solutions. |

### 2.2 Object-to-tab mapping

| Tab | Primary object(s) | Row granularity |
|---|---|---|
| RT.01.01 | Entity (main) | One row (the entity maintaining the register) |
| RT.01.02 | Entity (all non-branch) | One row per entity within scope |
| RT.01.03 | Entity (branches) | One row per branch |
| RT.02.01 | Contract | One row per contract (with solutions linked to business functions) |
| RT.02.02 | Contract × Solution × Asset | One row per contract–solution–business function combination |
| RT.02.03 | Contract (intra-group) | One row per intra-group contract with an overarching contract |
| RT.03.01 | Contract | One row per contract (main entity signs all) |
| RT.03.02 | Contract (non-intra-group) | One row per contract with a third-party provider |
| RT.03.03 | Contract (intra-group) | One row per intra-group contract |
| RT.04.01 | Contract × Entity/Branch | One row per contract for beneficiary + one per branch |
| RT.05.01 | Entity (provider, deduplicated) | One row per unique provider (aggregated across contracts) |
| RT.05.02 | Contract × Solution | One row per contract–solution combination (non-intra-group) |
| RT.06.01 | Asset (business function) | One row per business function |
| RT.07.01 | Contract × Solution | One row per contract–solution combination (non-intra-group) |
| RT.99.01 | (computed) | One row of aggregated counts (headers-only placeholder) |

### 2.3 Row generation rules

- **RT.01.01**: Always exactly one row — the main (built-in) entity.
- **RT.01.02**: All entities *except* branches. Branches are identified as child entities without `dora_provider_person_type` set.
- **RT.01.03**: Only branch entities (child entities without `dora_provider_person_type`).
- **RT.02.01 / RT.02.02**: Only contracts whose solutions are linked to at least one asset with `is_business_function=True` (or its children).
- **RT.02.03**: Only contracts where `is_intragroup=True` AND `overarching_contract` is set.
- **RT.03.01**: All contracts (main entity is the signing entity for every contract).
- **RT.03.02**: Non-intra-group contracts with a provider entity.
- **RT.03.03**: Intra-group contracts — the provider entity's LEI is reported.
- **RT.04.01**: For each contract: one row for the beneficiary entity (nature = "not a branch"), plus one row per branch whose parent is the beneficiary.
- **RT.05.01**: Deduplicated provider entities across all non-intra-group contracts. Annual expense is summed.
- **RT.05.02**: Non-intra-group contracts × solutions. Rank is always `1` (sub-contracting chains not modelled).
- **RT.06.01**: All assets with `is_business_function=True`.
- **RT.07.01**: Non-intra-group contracts × solutions (same scope as RT.05.02).
- **RT.99.01**: Aggregation counts — currently headers only (placeholder).

---

## 3. Conventions

### 3.1 EBA code prefixes

| Prefix | Domain | Example |
|---|---|---|
| `eba_CT:` | Classification / Type | `eba_CT:x12` (Credit institutions) |
| `eba_GA:` | Geography / Area | `eba_GA:FR` (France) |
| `eba_CU:` | Currency | `eba_CU:EUR` (Euro) |
| `eba_TA:` | Type of Activity / Service | `eba_TA:S01` (ICT project management) |
| `eba_ZZ:` | Miscellaneous / Other | `eba_ZZ:x794` (Not significant) |
| `eba_BT:` | Boolean / Binary Type | `eba_BT:x28` (Yes) |
| `eba_CO:` | Contractual / Operational | `eba_CO:x1` (Standalone arrangement) |
| `eba_RP:` | Role / Position | `eba_RP:x53` (Ultimate parent) |

### 3.2 ISO standards

- **LISTCOUNTRY** — ISO 3166-1 alpha-2 (~250 entries). Exported with `eba_GA:` prefix. Example: `eba_GA:FR`.
- **LISTCURRENCY** — ISO 4217 (~170 entries). Exported with `eba_CU:` prefix. Example: `eba_CU:EUR`.

### 3.3 Sentinel values

| Value | Meaning |
|---|---|
| `9999-12-31` | Open-ended / missing date placeholder (implementation convention, not EBA-mandated). |

Fields using `9999-12-31` when the underlying value is null or missing:

| Field | Context |
|---|---|
| b_01.02.0070 | Date of last update (`updated_at`) |
| b_01.02.0080 | Date of integration (`created_at`) |
| b_01.02.0090 | Date of deletion (active entities) |
| b_02.02.0060 | End date of contractual arrangement |
| b_06.01.0070 | Date of last assessment of criticality (`updated_at`) |

**Exception**: b_07.01.0070 (date of last audit) returns an empty string when `updated_at` is null, rather than the sentinel value.

### 3.4 Identifier resolution

When an entity identifier is needed, the export resolves in priority order: **LEI → EUID → VAT → DUNS**. The first non-empty value is used. If none of the priority identifiers are present, the first available identifier of any type is used as fallback. The identifier type is reported alongside the code in columns that require it.

> **Note**: The EBA FAQ (March 2025) states that LEI is preferred, then EUID. Identifiers other than LEI/EUID (e.g. VAT, DUNS) may be flagged as a data quality issue by competent authorities.

### 3.5 Reference ID fallback

For contracts and assets, the `ref_id` field is preferred. If empty, the internal UUID (`id`) is used as fallback.

### 3.6 EBA type nomenclature

The EBA XLS Master Template uses specific type names that differ from the simplified names used in this specification. The mapping is:

| EBA XLS type | This spec's type | Fields using this type |
|---|---|---|
| Alphanumerical | Alphanumeric | All free-text fields |
| Pattern | Auto | b_02.02.0040, b_02.02.0050, b_03.02.0030, b_05.01.0020, b_05.01.0090, b_05.02.0040, b_05.02.0070, b_06.01.0010, b_07.01.0030 |
| Monetary | Numeric | b_01.02.0110, b_02.01.0050, b_05.01.0070 |
| Natural number | Numeric (days) / Numeric (in hours) | b_02.02.0100, b_02.02.0110, b_05.02.0050, b_06.01.0080, b_06.01.0090 |
| Closed set of options | Closed set | All LIST-backed fields |
| [Yes/No] | Yes/No (LISTBINARY, 2 entries) | b_02.02.0140, b_07.01.0080 |
| Country | Country (LISTCOUNTRY) | All country fields |
| Currency | Currency (LISTCURRENCY) | All currency fields |
| Date | Date | All date fields |

---

## 4. Tab-by-tab field mappings

### 4.1 RT.01.01 — Entity maintaining the register of information

> One row: the main entity maintaining the register.

#### b_01.01.0010 — LEI of the entity maintaining the register of information

- Type: Alphanumeric (LEI pattern, 20 characters)
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Entity (main) > Legal Identifiers > LEI

#### b_01.01.0020 — Name of the entity

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Entity (main) > Name

#### b_01.01.0030 — Country of the entity

- Type: Country (LISTCOUNTRY)
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Entity (main) > Country
- Export: prefixed with `eba_GA:` (e.g. `eba_GA:FR`)

#### b_01.01.0040 — Type of entity

- Type: Closed set (LIST0101040, 24 entries)
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: Entity (main) > Entity Type (DORA section)

| Code | Label |
|---|---|
| `eba_CT:x12` | Credit institutions |
| `eba_CT:x599` | Investment firms |
| `eba_CT:x643` | Central counterparties (CCPs) |
| `eba_CT:x639` | Asset management companies |
| `eba_CT:x301` | Account information service providers |
| `eba_CT:x302` | Electronic money institutions |
| `eba_CT:x303` | Crypto-asset service providers |
| `eba_CT:x304` | Central security depository |
| `eba_CT:x305` | Trading venues |
| `eba_CT:x306` | Trade repositories |
| `eba_CT:x300` | Payment institution |
| `eba_CT:x316` | Other financial entity |
| `eba_CT:x315` | Securitisation repository |
| `eba_CT:x314` | Crowdfunding service providers |
| `eba_CT:x313` | Administrator of critical benchmarks |
| `eba_CT:x312` | Credit rating agency |
| `eba_CT:x311` | Institutions for occupational retirement provision |
| `eba_CT:x320` | Insurance intermediaries, reinsurance intermediaries and ancillary insurance intermediaries |
| `eba_CT:x309` | Insurance and reinsurance undertakings |
| `eba_CT:x308` | Data reporting service providers |
| `eba_CT:x307` | Managers of alternative investment funds |
| `eba_CT:x318` | Non-financial entity: Other than ICT intra-group service provider |
| `eba_CT:x317` | Non-financial entity: ICT intra-group service provider |
| `eba_CT:x310` | Issuers of asset-referenced tokens |

#### b_01.01.0050 — Competent Authority

- Type: Alphanumeric
- Required: Mandatory in case of reporting
- CSV header: `c0050`
- CISO Assistant field: Entity (main) > Competent Authority (DORA section)

#### b_01.01.0060 — Date of the reporting

- Type: Date
- Required: Mandatory in case of reporting
- CSV header: `c0060`
- CISO Assistant field: — (Auto: current date at export time)

---

### 4.2 RT.01.02 — List of entities within the scope of the register of information

> One row per entity within scope (all entities except branches).

#### b_01.02.0010 — LEI of the entity

- Type: Alphanumeric (LEI pattern, 20 characters)
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Entity > Legal Identifiers > LEI

#### b_01.02.0020 — Name of the entity

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Entity > Name

#### b_01.02.0030 — Country of the entity

- Type: Country (LISTCOUNTRY)
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Entity > Country
- Export: prefixed with `eba_GA:`

#### b_01.02.0040 — Type of entity

- Type: Closed set (LIST0101040, 24 entries)
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: Entity > Entity Type (DORA section)
- Values: see [RT.01.01 b_01.01.0040](#b_01010040--type-of-entity) — same table. Full list in [Appendix A — LIST0101040](#list0101040--entity-type).

#### b_01.02.0050 — Hierarchy of the entity within the group

- Type: Closed set (LIST0102050, 5 entries)
- Required: Mandatory
- CSV header: `c0050`
- CISO Assistant field: Entity > Entity Hierarchy (DORA section)

| Code | Label |
|---|---|
| `eba_RP:x53` | Ultimate parent |
| `eba_RP:x551` | Parent other than ultimate parent |
| `eba_RP:x56` | Subsidiary |
| `eba_RP:x21` | Entities other than entities of the group |
| `eba_RP:x210` | Outsourcing |

#### b_01.02.0060 — LEI of the direct parent undertaking

- Type: Alphanumeric (LEI pattern)
- Required: Mandatory
- CSV header: `c0060`
- CISO Assistant field: Entity > Parent entity > Legal Identifiers > LEI

#### b_01.02.0070 — Date of last update

- Type: Date
- Required: Mandatory
- CSV header: `c0070`
- CISO Assistant field: — (Auto: entity `updated_at` timestamp; `9999-12-31` if missing)

#### b_01.02.0080 — Date of integration in the Register of information

- Type: Date
- Required: Mandatory
- CSV header: `c0080`
- CISO Assistant field: — (Auto: entity `created_at` timestamp; `9999-12-31` if missing)

#### b_01.02.0090 — Date of deletion in the Register of information

- Type: Date
- Required: Mandatory
- CSV header: `c0090`
- CISO Assistant field: — (Auto: `9999-12-31` for active entities)

#### b_01.02.0100 — Currency

- Type: Currency (LISTCURRENCY)
- Required: Mandatory
- CSV header: `c0100`
- CISO Assistant field: Entity > Currency
- Export: prefixed with `eba_CU:` (e.g. `eba_CU:EUR`)

#### b_01.02.0110 — Value of total assets

- Type: Numeric
- Required: Mandatory if the entity is a financial entity
- CSV header: `c0110`
- CISO Assistant field: Entity > Value of total assets (DORA section)

---

### 4.3 RT.01.03 — List of branches

> One row per branch entity. Branches = child entities without `dora_provider_person_type` set.

#### b_01.03.0010 — Identification code of the branch

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Entity (branch) > Legal Identifiers
- Note: first available identifier (LEI > EUID > VAT > DUNS)

#### b_01.03.0020 — LEI of the financial entity head office of the branch

- Type: Alphanumeric (LEI pattern)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Entity (branch) > Parent entity > Legal Identifiers > LEI

#### b_01.03.0030 — Name of the branch

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Entity (branch) > Name

#### b_01.03.0040 — Country of the branch

- Type: Country (LISTCOUNTRY)
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: Entity (branch) > Country
- Export: prefixed with `eba_GA:`

---

### 4.4 RT.02.01 — Contractual arrangements: general information

> One row per contract linked to solutions associated with business function assets.

#### b_02.01.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID
- Note: falls back to internal UUID if empty

#### b_02.01.0020 — Type of contractual arrangement

- Type: Closed set (LIST0201020, 3 entries)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Contract > Contract type

| Code | Label |
|---|---|
| `eba_CO:x1` | Standalone arrangement |
| `eba_CO:x2` | Overarching arrangement |
| `eba_CO:x3` | Subsequent or associated arrangement |

#### b_02.01.0030 — Overarching contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Contract > Overarching Contract > Reference ID

#### b_02.01.0040 — Currency of the amount

- Type: Currency (LISTCURRENCY)
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: Contract > Currency
- Export: prefixed with `eba_CU:`

#### b_02.01.0050 — Annual expense or estimated cost

- Type: Numeric
- Required: Mandatory
- CSV header: `c0050`
- CISO Assistant field: Contract > Annual expense

---

### 4.5 RT.02.02 — Contractual arrangements: specific information

> One row per contract × solution × business function combination.

#### b_02.02.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID

#### b_02.02.0020 — LEI of the entity making use of the ICT service(s)

- Type: Alphanumeric (LEI pattern)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Contract > Beneficiary Entity > Legal Identifiers > LEI

#### b_02.02.0030 — Identification code of the ICT third-party service provider

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Contract > Provider Entity > Legal Identifiers
- Note: first available identifier (LEI > EUID > VAT > DUNS)

#### b_02.02.0040 — Type of code to identify the provider

- Type: Auto
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: — (automatically determined based on identifier type used: LEI, EUID, VAT, DUNS)

#### b_02.02.0050 — Function identifier

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0050`
- CISO Assistant field: Asset (business function) > Reference ID

#### b_02.02.0060 — Type of ICT services

- Type: Closed set (LISTANNEXIII, 19 entries)
- Required: Mandatory
- CSV header: `c0060`
- CISO Assistant field: Solution > ICT Service Type (DORA Assessment section)

| Code | Label |
|---|---|
| `eba_TA:S01` | ICT project management |
| `eba_TA:S02` | ICT Development |
| `eba_TA:S03` | ICT help desk and first level support |
| `eba_TA:S04` | ICT security management services |
| `eba_TA:S05` | Provision of data |
| `eba_TA:S06` | Data analysis |
| `eba_TA:S07` | ICT, facilities and hosting services (excluding Cloud services) |
| `eba_TA:S08` | Computation |
| `eba_TA:S09` | Non-Cloud Data storage |
| `eba_TA:S10` | Telecom carrier |
| `eba_TA:S11` | Network infrastructure |
| `eba_TA:S12` | Hardware and physical devices |
| `eba_TA:S13` | Software licencing (excluding SaaS) |
| `eba_TA:S14` | ICT operation management (including maintenance) |
| `eba_TA:S15` | ICT Consulting |
| `eba_TA:S16` | ICT Risk management |
| `eba_TA:S17` | Cloud services: IaaS |
| `eba_TA:S18` | Cloud services: PaaS |
| `eba_TA:S19` | Cloud services: SaaS |

#### b_02.02.0070 — Start date of the contractual arrangement

- Type: Date
- Required: Mandatory
- CSV header: `c0070`
- CISO Assistant field: Contract > Start date

#### b_02.02.0080 — End date of the contractual arrangement

- Type: Date
- Required: Mandatory
- CSV header: `c0080`
- CISO Assistant field: Contract > End date
- Note: `9999-12-31` if not set (open-ended contract)

#### b_02.02.0090 — Reason of the termination or ending

- Type: Closed set (LIST0202090, 6 entries)
- Required: Mandatory if the contractual arrangement is terminated
- CSV header: `c0090`
- CISO Assistant field: Contract > Termination reason

| Code | Label |
|---|---|
| `eba_CO:x4` | Termination not for cause: Expired and not renewed |
| `eba_CO:x5` | Termination for cause: Provider in breach of applicable law, regulations or contractual provisions |
| `eba_CO:x6` | Termination for cause: Identified impediments of the provider capable of altering the supported function |
| `eba_CO:x7` | Termination for cause: Provider's weaknesses regarding the management and security of sensitive data or information |
| `eba_CO:x8` | Termination: As requested by the competent authority |
| `eba_CO:x9` | Other reasons for termination |

#### b_02.02.0100 — Notice period for the financial entity

- Type: Numeric (days)
- Required: Mandatory if the ICT service is supporting a critical or important function
- CSV header: `c0100`
- CISO Assistant field: Contract > Notice period for entity (days)

#### b_02.02.0110 — Notice period for the ICT third-party service provider

- Type: Numeric (days)
- Required: Mandatory if the ICT service is supporting a critical or important function
- CSV header: `c0110`
- CISO Assistant field: Contract > Notice period for provider (days)

#### b_02.02.0120 — Country of the governing law

- Type: Country (LISTCOUNTRY)
- Required: Mandatory if the ICT service is supporting a critical or important function
- CSV header: `c0120`
- CISO Assistant field: Contract > Governing law country
- Export: prefixed with `eba_GA:`

#### b_02.02.0130 — Country of provision of the ICT services

- Type: Country (LISTCOUNTRY)
- Required: Mandatory if the ICT service is supporting a critical or important function
- CSV header: `c0130`
- CISO Assistant field: Contract > Provider Entity > Country
- Export: prefixed with `eba_GA:`

#### b_02.02.0140 — Storage of data

- Type: Yes/No (LISTBINARY, 2 entries)
- Required: Mandatory if the ICT service is supporting a critical or important function
- CSV header: `c0140`
- CISO Assistant field: Solution > Storage of data (DORA Assessment section)
- Export: model field is a BooleanField; converted to `eba_BT:x28` (Yes) when True, `eba_BT:x29` (No) when False

| Code | Label |
|---|---|
| `eba_BT:x28` | Yes |
| `eba_BT:x29` | No |

#### b_02.02.0150 — Location of the data at rest (storage)

- Type: Country (LISTCOUNTRY)
- Required: Mandatory if ’Yes’ is reported in RT.02.02.0140
- CSV header: `c0150`
- CISO Assistant field: Solution > Location of data at rest
- Export: prefixed with `eba_GA:`

#### b_02.02.0160 — Location of management of the data (processing)

- Type: Country (LISTCOUNTRY)
- Required: Mandatory if the ICT service is based on or foresees data processing
- CSV header: `c0160`
- CISO Assistant field: Solution > Location of data processing
- Export: prefixed with `eba_GA:`

#### b_02.02.0170 — Sensitiveness of the data stored

- Type: Closed set (LIST0202170, 3 entries)
- Required: Mandatory if the ICT third-party service provider stores data and if the ICT service is supporting a critical or important function or material part thereof
- CSV header: `c0170`
- CISO Assistant field: Solution > Data Sensitiveness (DORA Assessment section)

| Code | Label |
|---|---|
| `eba_ZZ:x791` | Low |
| `eba_ZZ:x792` | Medium |
| `eba_ZZ:x793` | High |

#### b_02.02.0180 — Level of reliance on the ICT service

- Type: Closed set (LIST0202180, 4 entries)
- Required: Mandatory if the ICT service is supporting a critical or important function or material part thereof
- CSV header: `c0180`
- CISO Assistant field: Solution > Level of Reliance (DORA Assessment section)

| Code | Label |
|---|---|
| `eba_ZZ:x794` | Not significant |
| `eba_ZZ:x795` | Low reliance |
| `eba_ZZ:x796` | Material reliance |
| `eba_ZZ:x797` | Full reliance |

---

### 4.6 RT.02.03 — Intra-group contractual arrangements

> One row per intra-group contract (`is_intragroup=True`) that has an overarching contract.

#### b_02.03.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract (subordinate) > Reference ID

#### b_02.03.0020 — Contractual arrangement linked to RT.02.03.0010

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Contract (subordinate) > Overarching Contract > Reference ID

#### b_02.03.0030 — Link

- Type: Boolean
- Required: Not applicable
- CSV header: `c0030`
- CISO Assistant field: — (Auto: always `true`)

---

### 4.7 RT.03.01 — Entities signing contracts (receivers)

> One row per contract. The main entity is the signing entity for all contracts.

#### b_03.01.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID

#### b_03.01.0020 — LEI of the entity signing the contractual arrangement

- Type: Alphanumeric (LEI pattern)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: — (Auto: main entity identifier for all contracts)
- Note: uses identifier resolution (see [Section 3.4](#34-identifier-resolution)), not LEI-only

#### b_03.01.0030 — Link

- Type: Boolean
- Required: Not applicable
- CSV header: `c0030`
- CISO Assistant field: — (Auto: always `true`)

---

### 4.8 RT.03.02 — ICT service providers signing contracts

> One row per non-intra-group contract with a provider entity.

#### b_03.02.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID

#### b_03.02.0020 — Identification code of ICT third-party service provider

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Contract > Provider Entity > Legal Identifiers
- Note: first available identifier (LEI > EUID > VAT > DUNS)

#### b_03.02.0030 — Type of code to identify the provider

- Type: Auto
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: — (automatically determined based on identifier type used)

---

### 4.9 RT.03.03 — Entities providing services (intra-group)

> One row per intra-group contract.

#### b_03.03.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID

#### b_03.33.0020 — LEI of the entity providing ICT services

- Type: Alphanumeric (LEI pattern)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: — (Auto: provider entity LEI for intra-group contracts)
- Note: The column code `b_03.33.0020` (with `33` instead of `03`) is a known typo in the official EBA XLS Master Template. Our export faithfully reproduces it for compatibility. Do not "fix" it to `b_03.03.0020`.

#### b_03.03.0031 — Link

- Type: Boolean
- Required: Not applicable
- CSV header: `c0031`
- CISO Assistant field: — (Auto: always `true`)

---

### 4.10 RT.04.01 — Entities making use of ICT services

> One row per contract for the beneficiary entity, plus one additional row per branch of that beneficiary.

> **Note**: The export deduplicates rows by (contract reference, entity identifier, branch code) combination to avoid reporting the same entity–contract pair twice.

#### b_04.01.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID

#### b_04.01.0020 — LEI of the entity making use of the ICT service(s)

- Type: Alphanumeric (LEI pattern)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Contract > Beneficiary Entity > Legal Identifiers > LEI

#### b_04.01.0030 — Nature of the entity

- Type: Closed set (LIST0401030, 2 entries)
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: — (Auto: computed based on whether the entity is a branch)

| Code | Label |
|---|---|
| `eba_ZZ:x838` | branch of a financial entity |
| `eba_ZZ:x839` | not a branch |

#### b_04.01.0040 — Identification code of the branch

- Type: Alphanumeric
- Required: Mandatory if the entity making use of the ICT service(s) is a branch of a financial entity (RT.04.01.0030)
- CSV header: `c0040`
- CISO Assistant field: Entity (branch) > Legal Identifiers
- Note: only filled for branch rows

---

### 4.11 RT.05.01 — ICT third-party service providers

> One row per unique provider entity, aggregated across all non-intra-group contracts.

#### b_05.01.0010 — Identification code of ICT third-party service provider

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Entity (provider) > Legal Identifiers
- Note: first available identifier (LEI > EUID > VAT > DUNS)

#### b_05.01.0020 — Type of code to identify the provider

- Type: Auto
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: — (automatically determined based on identifier type used)

#### b_05.01.0030 — Name of the ICT third-party service provider

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Entity (provider) > Name

#### b_05.01.0040 — Type of person of the provider

- Type: Closed set (LIST0501040, 2 entries)
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: Entity (provider) > Person Type (DORA section)

| Code | Label |
|---|---|
| `eba_CT:x212` | Legal person, excluding individual acting in a business capacity |
| `eba_CT:x213` | Individual acting in a business capacity |

#### b_05.01.0050 — Country of the provider's headquarters

- Type: Country (LISTCOUNTRY)
- Required: Mandatory
- CSV header: `c0050`
- CISO Assistant field: Entity (provider) > Country
- Export: prefixed with `eba_GA:`

#### b_05.01.0060 — Currency

- Type: Currency (LISTCURRENCY)
- Required: Mandatory if RT.05.01.0070 is reported
- CSV header: `c0060`
- CISO Assistant field: Contract / Entity (main) > Currency
- Export: prefixed with `eba_CU:`. Fallback chain: contract currency → main entity currency → empty.

#### b_05.01.0070 — Total annual expense or estimated cost

- Type: Numeric
- Required: Mandatory if the ICT third-party service provider is a direct ICT third-party service provider
- CSV header: `c0070`
- CISO Assistant field: — (Auto: sum of `Annual expense` across all contracts with this provider)

#### b_05.01.0080 — Identification code of the provider's ultimate parent undertaking

- Type: Alphanumeric
- Required: Mandatory if the ICT third-party service provider is not the ultimate parent undertaking
- CSV header: `c0080`
- CISO Assistant field: Entity (provider) > Parent entity > Legal Identifiers
- Note: first available identifier of parent entity

#### b_05.01.0090 — Type of code to identify the provider's ultimate parent undertaking

- Type: Auto
- Required: Mandatory if the ICT third-party service provider is not the ultimate parent undertaking
- CSV header: `c0090`
- CISO Assistant field: — (automatically determined based on identifier type used for parent)

---

### 4.12 RT.05.02 — ICT service supply chains

> One row per contract × solution combination. Non-intra-group contracts only.

#### b_05.02.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID

#### b_05.02.0020 — Type of ICT services

- Type: Closed set (LISTANNEXIII, 19 entries)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Solution > ICT Service Type
- Values: see [RT.02.02 b_02.02.0060](#b_02020060--type-of-ict-services) — same table. Full list in [Appendix A — LISTANNEXIII](#listannexiii--ict-service-type).

#### b_05.02.0030 — Identification code of the ICT third-party service provider

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Contract > Provider Entity > Legal Identifiers
- Note: first available identifier

#### b_05.02.0040 — Type of code to identify the provider

- Type: Auto
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: — (automatically determined)

#### b_05.02.0050 — Rank

- Type: Numeric
- Required: Mandatory
- CSV header: `c0050`
- CISO Assistant field: — (Auto: always `1` — sub-contracting chains not modelled)

#### b_05.02.0060 — Identification code of the recipient of sub-contracted ICT services

- Type: Alphanumeric
- Required: Mandatory Not applicable for rank 1
- CSV header: `c0060`
- CISO Assistant field: — (Auto: empty for rank 1)

#### b_05.02.0070 — Type of code to identify the recipient

- Type: Auto
- Required: Mandatory Not applicable for rank 1
- CSV header: `c0070`
- CISO Assistant field: — (Auto: empty for rank 1)

---

### 4.13 RT.06.01 — Functions identification

> One row per asset marked as a business function (`is_business_function=True`).

#### b_06.01.0010 — Function Identifier

- Type: Alphanumeric (pattern: F1, F2, … Fn)
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Asset (business function) > Reference ID

#### b_06.01.0020 — Licensed activity

- Type: Closed set (LIST0601020, 128 entries)
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Asset (business function) > Licensed activity (DORA section)
- Note: model field is `dora_licenced_activity` (British spelling, matching EBA Annex 2)

##### Non-Life Insurance (8 entries)

| Code | Label |
|---|---|
| `eba_TA:x185` | Non-Life Insurance: Classes 1 and 2: 'Accident and Health Insurance' |
| `eba_TA:x186` | Non-Life Insurance: Classes 1 (fourth indent), 3, 7 and 10: 'Motor Insurance' |
| `eba_TA:x187` | Non-Life Insurance: Classes 1 (fourth indent), 4, 6, 7 and 12: 'Marine and Transport Insurance' |
| `eba_TA:x188` | Non-Life Insurance: Classes 1 (fourth indent), 5, 7 and 11: 'Aviation Insurance' |
| `eba_TA:x189` | Non-Life Insurance: Classes 8 and 9: 'Insurance against Fire and other Damage to Property' |
| `eba_TA:x190` | Non-Life Insurance: Classes 10, 11, 12 and 13: 'Liability Insurance' |
| `eba_TA:x191` | Non-Life Insurance: Classes 14 and 15: 'Credit and Suretyship Insurance' |
| `eba_TA:x192` | Non-Life Insurance: All classes, at the choice of the Member States, which shall notify the other Member States and the Commission of their choice |

##### Life Insurance (9 entries)

| Code | Label |
|---|---|
| `eba_TA:x193` | Life Insurance: The life insurance referred to in points (a)(i), (ii) and (iii) of Article 2(3) excluding those referred to in II and III |
| `eba_TA:x194` | Life Insurance: Marriage assurance, birth assurance |
| `eba_TA:x195` | Life Insurance: The insurance referred to in points (a)(i) and (ii) of Article 2(3), which are linked to investment funds |
| `eba_TA:x196` | Life Insurance: Permanent health insurance, referred to in point (a)(iv) of Article 2(3) |
| `eba_TA:x197` | Life Insurance: Tontines, referred to in point (b)(i) of Article 2(3) |
| `eba_TA:x198` | Life Insurance: Capital redemption operations, referred to in point (b)(ii) of Article 2(3) |
| `eba_TA:x199` | Life Insurance: Management of group pension funds, referred to in point (b)(iii) and (iv) of Article 2(3) |
| `eba_TA:x200` | Life Insurance: The operations referred to in point (b)(v) of Article 2(3) |
| `eba_TA:x201` | Life Insurance: The operations referred to in Article 2(3)(c) |

##### Banking and credit (9 entries)

| Code | Label |
|---|---|
| `eba_TA:x162` | Taking deposits and other repayable funds |
| `eba_TA:x163` | Lending activities |
| `eba_TA:x164` | Financial leasing |
| `eba_TA:x165` | Issuing and administering other means of payment |
| `eba_TA:x166` | Guarantees and commitments |
| `eba_TA:x167` | Guarantees and commitments related to securities lending and borrowing, within the meaning of point 6 of Annex I to Directive 2013/36/EU |
| `eba_TA:x168` | Trading for own account or for account of customers |
| `eba_TA:x169` | Participation in securities issues and the provision of services relating to such issues |
| `eba_TA:x143` | Granting credits or loans to investors |

##### Payment services (10 entries)

| Code | Label |
|---|---|
| `eba_TA:x28` | Payment services |
| `eba_TA:x180` | Issuing electronic money |
| `eba_TA:x220` | Services enabling cash to be placed on a payment account as well as all the operations required for operating a payment account |
| `eba_TA:x221` | Services enabling cash withdrawals from a payment account as well as all the operations required for operating a payment account |
| `eba_TA:x222` | Execution of payment transactions, including transfers of funds on a payment account with the user's payment service provider or with another payment service provider |
| `eba_TA:x223` | Execution of payment transactions where the funds are covered by a credit line for a payment service user |
| `eba_TA:x224` | Issuing of payment instruments and/or acquiring of payment transactions |
| `eba_TA:x225` | Money remittance |
| `eba_TA:x226` | Payment initiation services |
| `eba_TA:x227` | Account information services |

##### Investment services (18 entries)

| Code | Label |
|---|---|
| `eba_TA:x133` | Reception and transmission of orders |
| `eba_TA:x134` | Execution of orders on behalf of clients |
| `eba_TA:x136` | Portfolio management |
| `eba_TA:x137` | Investment advice |
| `eba_TA:x138` | Underwriting of financial instruments and/or placing of financial instruments on a firm commitment basis |
| `eba_TA:x139` | Placing of financial instruments without a firm commitment basis |
| `eba_TA:x140` | Operation of an MTF |
| `eba_TA:x141` | Operation of an OTF |
| `eba_TA:x144` | Advice to undertakings on capital structure, industrial strategy and related matters and advice and services relating to mergers and the purchase of undertakings |
| `eba_TA:x146` | Investment research and financial analysis |
| `eba_TA:x147` | Services related to underwriting |
| `eba_TA:x170` | Advisory services |
| `eba_TA:x171` | Money broking |
| `eba_TA:x172` | Portfolio management and advice |
| `eba_TA:x173` | Dealing on own account |
| `eba_TA:x204` | Investment services related to the underlying of the derivatives |
| `eba_TA:x230` | Operation of a Regulated Market |
| `eba_TA:x274` | investment advice concerning one or more of the instruments listed in Annex I, Section C to Directive 2004/39/EC |

##### Safekeeping and administration (5 entries)

| Code | Label |
|---|---|
| `eba_TA:x174` | Safekeeping and administration of securities |
| `eba_TA:x175` | Safekeeping and administration of financial instruments for the account of clients |
| `eba_TA:x176` | safe-keeping and administration in relation to shares or units of collective investment undertakings |
| `eba_TA:x177` | non-core services (safekeeping and administration in relation to units of collective investment undertakings) |
| `eba_TA:x178` | Safe custody services |

##### Crypto-assets (11 entries)

| Code | Label |
|---|---|
| `eba_TA:x181` | reception and transmission of orders for crypto-assets on behalf of clients |
| `eba_TA:x182` | Portfolio management on crypto-assets |
| `eba_TA:x228` | Providing custody and administration of crypto-assets on behalf of clients |
| `eba_TA:x229` | operation of a trading platform for crypto-assets |
| `eba_TA:x231` | exchange of crypto-assets for funds |
| `eba_TA:x232` | exchange of crypto-assets for other crypto-assets |
| `eba_TA:x233` | execution of orders for crypto-assets on behalf of clients |
| `eba_TA:x234` | placing of crypto-assets |
| `eba_TA:x235` | providing advice on crypto-assets |
| `eba_TA:x236` | providing transfer services for crypto-assets on behalf of clients |
| `eba_TA:x237` | issuance of asset-referenced tokens |

##### Asset management and funds (12 entries)

| Code | Label |
|---|---|
| `eba_TA:x183` | management of portfolios of investments (AIFMD) |
| `eba_TA:x184` | management of portfolios of investments (UCITSD) |
| `eba_TA:x265` | maintenance of unit-/shareholder register |
| `eba_TA:x266` | unit/shares issues and redemptions |
| `eba_TA:x267` | maintenance of unit-holder register |
| `eba_TA:x268` | unit issues and redemptions |
| `eba_TA:x269` | contract settlements (including certificate dispatch) |
| `eba_TA:x270` | distribution of income |
| `eba_TA:x271` | record keeping |
| `eba_TA:x272` | Marketing |
| `eba_TA:x273` | services necessary to meet the fiduciary duties of the AIFM |
| `eba_TA:x275` | Ancillary services |

##### Insurance distribution (2 entries)

| Code | Label |
|---|---|
| `eba_TA:x202` | insurance distribution |
| `eba_TA:x203` | reinsurance distribution |

##### CSD and settlement (18 entries)

| Code | Label |
|---|---|
| `eba_TA:x238` | notary service |
| `eba_TA:x239` | central maintenance service |
| `eba_TA:x240` | settlement service |
| `eba_TA:x241` | Organising a securities lending mechanism, as agent among participants of a securities settlement system |
| `eba_TA:x242` | collateral management services |
| `eba_TA:x243` | general collateral management services |
| `eba_TA:x244` | Establishing CSD links, providing, maintaining or operating securities accounts in relation to the settlement service, collateral management, other ancillary services |
| `eba_TA:x245` | Settlement matching, instruction routing, trade confirmation, trade verification |
| `eba_TA:x246` | Services related to shareholders' registers |
| `eba_TA:x247` | Supporting the processing of corporate actions, including tax, general meetings and information services |
| `eba_TA:x248` | New issue services, including allocation and management of ISIN codes and similar codes |
| `eba_TA:x249` | Instruction routing and processing, fee collection and processing and related reporting |
| `eba_TA:x253` | Providing cash accounts to, and accepting deposits from, participants in a securities settlement system and holders of securities accounts, within the meaning of point 1 of Annex I to Directive 2013/36/EU |
| `eba_TA:x254` | Providing cash credit for reimbursement no later than the following business day, cash lending to pre-finance corporate actions and lending securities to holders of securities accounts, within the meaning of point 2 of Annex I to Directive 2013/36/EU |
| `eba_TA:x255` | Payment services involving processing of cash and foreign exchange transactions, within the meaning of point 4 of Annex I to Directive 2013/36/EU |
| `eba_TA:x256` | Treasury activities involving foreign exchange and transferable securities related to managing participants' long balances |
| `eba_TA:x257` | Any other NCA-permitted non-banking-type ancillary services not specified in Annex of Regulation (EU) No 909/2014 (CSDR) - Section B |
| `eba_TA:x258` | Any other NCA-permitted Banking-type ancillary services not specified in Annex of Regulation (EU) No 909/2014 (CSDR) - Section C |

##### Other activities (26 entries)

| Code | Label |
|---|---|
| `eba_TA:x104` | Foreign exchange services |
| `eba_TA:x179` | Credit reference services |
| `eba_TA:x205` | Retirement-benefit related operations and activities arising therefrom |
| `eba_TA:x206` | issuance of credit ratings |
| `eba_TA:x207` | administering the arrangements for determining a benchmark |
| `eba_TA:x208` | collecting, analysing or processing input data for the purpose of determining a benchmark |
| `eba_TA:x209` | determining a benchmark through the application of a formula or other method of calculation or by an assessment of input data provided for that purpose |
| `eba_TA:x210` | publication of benchmark |
| `eba_TA:x211` | Provision of crowdfunding services |
| `eba_TA:x212` | ancillary non-securitisation services |
| `eba_TA:x213` | ancillary securitisation services |
| `eba_TA:x214` | collection and maintenance of the records of derivatives (non-SFTs) |
| `eba_TA:x215` | collection and maintenance of the records of SFTs |
| `eba_TA:x216` | collection and maintenance of the records of securitisations |
| `eba_TA:x217` | activity as approved publication arrangement |
| `eba_TA:x218` | activity as consolidated tape provider |
| `eba_TA:x219` | activity as approved reporting mechanism |
| `eba_TA:x250` | Providing regulatory reporting |
| `eba_TA:x251` | Providing information, data and statistics to market/census bureaus or other governmental or inter-governmental entities |
| `eba_TA:x252` | Providing IT services |
| `eba_TA:x259` | interposition between counterparties |
| `eba_TA:x260` | risk management |
| `eba_TA:x261` | legal and fund management accounting services |
| `eba_TA:x262` | customer inquiries |
| `eba_TA:x263` | valuation and pricing, including tax returns |
| `eba_TA:x264` | regulatory compliance monitoring |

#### b_06.01.0030 — Function name

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: Asset (business function) > Name

#### b_06.01.0040 — LEI of the financial entity

- Type: Alphanumeric (LEI pattern)
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: — (Auto: main entity LEI)

#### b_06.01.0050 — Criticality or importance assessment

- Type: Closed set (LIST0601050, 3 entries)
- Required: Mandatory
- CSV header: `c0050`
- CISO Assistant field: Asset (business function) > Criticality assessment (DORA section)

| Code | Label |
|---|---|
| `eba_BT:x28` | Yes |
| `eba_BT:x29` | No |
| `eba_BT:x21` | Assessment not performed |

#### b_06.01.0060 — Reasons for criticality or importance

- Type: Alphanumeric (max 300 characters)
- Required: Optional
- CSV header: `c0060`
- CISO Assistant field: Asset (business function) > Criticality justification (DORA section)

#### b_06.01.0070 — Date of the last assessment of criticality or importance

- Type: Date
- Required: Mandatory
- CSV header: `c0070`
- CISO Assistant field: — (Auto: asset `updated_at` timestamp; `9999-12-31` if missing)

#### b_06.01.0080 — Recovery time objective of the function

- Type: Numeric (in hours)
- Required: Mandatory
- CSV header: `c0080`
- CISO Assistant field: Asset (business function) > disaster_recovery_objectives > objectives > rto > value

#### b_06.01.0090 — Recovery point objective of the function

- Type: Numeric (in hours)
- Required: Mandatory
- CSV header: `c0090`
- CISO Assistant field: Asset (business function) > disaster_recovery_objectives > objectives > rpo > value

#### b_06.01.0100 — Impact of discontinuing the function

- Type: Closed set (LIST0601100, 4 entries)
- Required: Mandatory
- CSV header: `c0100`
- CISO Assistant field: Asset (business function) > Discontinuing Impact (DORA section)

| Code | Label |
|---|---|
| `eba_ZZ:x791` | Low |
| `eba_ZZ:x792` | Medium |
| `eba_ZZ:x793` | High |
| `eba_ZZ:x799` | Assessment not performed |

---

### 4.14 RT.07.01 — Assessment of the ICT services

> One row per contract × solution combination. Non-intra-group contracts only.

#### b_07.01.0010 — Contractual arrangement reference number

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0010`
- CISO Assistant field: Contract > Reference ID

#### b_07.01.0020 — Identification code of the ICT third-party service provider

- Type: Alphanumeric
- Required: Mandatory
- CSV header: `c0020`
- CISO Assistant field: Contract > Provider Entity > Legal Identifiers
- Note: first available identifier (LEI > EUID > VAT > DUNS)

#### b_07.01.0030 — Type of code to identify the provider

- Type: Auto
- Required: Mandatory
- CSV header: `c0030`
- CISO Assistant field: — (automatically determined based on identifier type used)

#### b_07.01.0040 — Type of ICT services

- Type: Closed set (LISTANNEXIII, 19 entries)
- Required: Mandatory
- CSV header: `c0040`
- CISO Assistant field: Solution > ICT Service Type (DORA Assessment section)
- Values: see [RT.02.02 b_02.02.0060](#b_02020060--type-of-ict-services) — same table. Full list in [Appendix A — LISTANNEXIII](#listannexiii--ict-service-type).

#### b_07.01.0050 — Substitutability of the ICT third-party service provider

- Type: Closed set (LIST0701050, 4 entries)
- Required: Mandatory
- CSV header: `c0050`
- CISO Assistant field: Solution > Substitutability (DORA Assessment section)

| Code | Label |
|---|---|
| `eba_ZZ:x959` | Not substitutable |
| `eba_ZZ:x962` | Easily substitutable |
| `eba_ZZ:x961` | Medium complexity in terms of substitutability |
| `eba_ZZ:x960` | Highly complex substitutability |

#### b_07.01.0060 — Reason if not substitutable or difficult to substitute

- Type: Closed set (LIST0701060, 3 entries)
- Required: Mandatory in case “not substitutable” or “highly complex substitutability” is selected in RT.07.01.0050
- CSV header: `c0060`
- CISO Assistant field: Solution > Non-Substitutability Reason (DORA Assessment section)

| Code | Label |
|---|---|
| `eba_ZZ:x963` | Lack of real alternatives |
| `eba_ZZ:x964` | Difficulties in migrating or reintegrating |
| `eba_ZZ:x965` | Lack of real alternatives and difficulties in migrating or reintegrating |

#### b_07.01.0070 — Date of the last audit on the ICT third-party service provider

- Type: Date
- Required: Mandatory
- CSV header: `c0070`
- CISO Assistant field: — (Auto: solution `updated_at` timestamp)
- Note: empty string if `updated_at` is null (unlike b_06.01.0070 which uses `9999-12-31`). See [Section 3.3](#33-sentinel-values).

#### b_07.01.0080 — Existence of an exit plan

- Type: Yes/No (LISTBINARY, 2 entries)
- Required: Mandatory
- CSV header: `c0080`
- CISO Assistant field: Solution > Exit Plan (DORA Assessment section)
- Full list in [Appendix A — LISTBINARY](#listbinary--yesno).

#### b_07.01.0090 — Possibility of reintegration of the contracted ICT service

- Type: Closed set (LIST0701090, 3 entries)
- Required: Mandatory
- CSV header: `c0090`
- CISO Assistant field: Solution > Reintegration Possibility (DORA Assessment section)

| Code | Label |
|---|---|
| `eba_ZZ:x798` | Easy |
| `eba_ZZ:x966` | Difficult |
| `eba_ZZ:x967` | Highly complex |

#### b_07.01.0100 — Impact of discontinuing the ICT services

- Type: Closed set (LIST0601100, 4 entries)
- Required: Mandatory
- CSV header: `c0100`
- CISO Assistant field: Solution > Discontinuing Impact (DORA Assessment section)
- Values: see [RT.06.01 b_06.01.0100](#b_06010100--impact-of-discontinuing-the-function) — same table. Full list in [Appendix A — LIST0601100](#list0601100--discontinuing-impact).

#### b_07.01.0110 — Are there alternative ICT third-party service providers identified?

- Type: Closed set (LIST0601050, 3 entries)
- Required: Mandatory
- CSV header: `c0110`
- CISO Assistant field: Solution > Alternative Providers Identified (DORA Assessment section)
- Values: see [RT.06.01 b_06.01.0050](#b_06010050--criticality-or-importance-assessment) — same table. Full list in [Appendix A — LIST0601050](#list0601050--yesnoassessment-not-performed).

#### b_07.01.0120 — Identification of alternative ICT TPP

- Type: Alphanumeric (free text)
- Required: Optional
- CSV header: `c0120`
- CISO Assistant field: Solution > Alternative Providers (DORA Assessment section)

---

### 4.15 RT.99.01 — Aggregation

> One row of aggregated counts. Currently a **placeholder** — headers only, no data rows generated.
>
> In the EBA XLS template, this sheet (`b_99.01`) is titled "Definitions from Entities making use of the ICT Services" and is structured as a cross-tabulation definitions sheet with grouped category headers (Row 2) and sub-option names (Row 4). The Instructions sheet marks all its fields as "Not applicable".

| Column | Description | Source |
|---|---|---|
| b_99.01.0010 | Standalone arrangement count | Count of contracts with type = `eba_CO:x1` |
| b_99.01.0020 | Overarching arrangement count | Count of contracts with type = `eba_CO:x2` |
| b_99.01.0030 | Subsequent or associated arrangement count | Count of contracts with type = `eba_CO:x3` |
| b_99.01.0040 | Data sensitiveness: Low | Count of solutions with `eba_ZZ:x791` |
| b_99.01.0050 | Data sensitiveness: Medium | Count of solutions with `eba_ZZ:x792` |
| b_99.01.0060 | Data sensitiveness: High | Count of solutions with `eba_ZZ:x793` |
| b_99.01.0070 | Impact discontinuing function: Low | Count of business functions with `eba_ZZ:x791` |
| b_99.01.0080 | Impact discontinuing function: Medium | Count of business functions with `eba_ZZ:x792` |
| b_99.01.0090 | Impact discontinuing function: High | Count of business functions with `eba_ZZ:x793` |
| b_99.01.0100 | Substitutability: Not substitutable | Count of solutions with `eba_ZZ:x959` |
| b_99.01.0110 | Substitutability: Highly complex | Count of solutions with `eba_ZZ:x960` |
| b_99.01.0120 | Substitutability: Medium complexity | Count of solutions with `eba_ZZ:x961` |
| b_99.01.0130 | Substitutability: Easily substitutable | Count of solutions with `eba_ZZ:x962` |
| b_99.01.0140 | Reintegration: Easy | Count of solutions with `eba_ZZ:x798` |
| b_99.01.0150 | Reintegration: Difficult | Count of solutions with `eba_ZZ:x966` |
| b_99.01.0160 | Reintegration: Highly complex | Count of solutions with `eba_ZZ:x967` |
| b_99.01.0170 | Impact discontinuing ICT: Low | Count of solutions with `eba_ZZ:x791` |
| b_99.01.0180 | Impact discontinuing ICT: Medium | Count of solutions with `eba_ZZ:x792` |
| b_99.01.0190 | Impact discontinuing ICT: High | Count of solutions with `eba_ZZ:x793` |

---

## 5. Export metadata files

In addition to the 15 CSV template files, the DORA RoI export ZIP contains four metadata files required by the XBRL CSV reporting format.

### 5.1 `reports/FilingIndicators.csv`

Lists all 15 template IDs with a `reported` flag set to `true`, indicating each template is included in the export.

| Column | Description |
|---|---|
| `templateID` | Template identifier (e.g. `B_01.01`, `B_02.02`, … `B_99.01`) |
| `reported` | Always `true` for all 15 templates |

Template IDs: `B_01.01`, `B_01.02`, `B_01.03`, `B_02.01`, `B_02.02`, `B_02.03`, `B_03.01`, `B_03.02`, `B_03.03`, `B_04.01`, `B_05.01`, `B_05.02`, `B_06.01`, `B_07.01`, `B_99.01`.

### 5.2 `reports/parameters.csv`

Report metadata and configuration parameters.

| Parameter | Value | Description |
|---|---|---|
| `entityID` | `rs:{LEI}.CON` | Main entity LEI wrapped in XBRL entity format (falls back to `rs:UNKNOWN.CON`) |
| `refPeriod` | `2025-03-31` | Reference reporting period (currently a hardcoded placeholder) |
| `baseCurrency` | `iso4217:{currency}` | ISO 4217 currency code of the main entity (e.g. `iso4217:EUR`) |
| `decimalsInteger` | `0` | Decimal precision for integer values |
| `decimalsMonetary` | `-3` | Decimal precision for monetary values (thousands) |

### 5.3 `META-INF/reportPackage.json`

XBRL report package metadata. Contains a single JSON object:

```json
{
  "documentInfo": {
    "documentType": "https://xbrl.org/report-package/2023"
  }
}
```

### 5.4 `reports/report.json`

XBRL CSV report metadata. Required by EBA DPM Technical Check rule 505 ("Each report must contain a report.json"). Contains the document type and a reference to the DORA taxonomy module:

```json
{
  "documentInfo": {
    "documentType": "https://xbrl.org/2021/xbrl-csv",
    "extends": [
      "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/dora/4.0/mod/dora.json"
    ]
  }
}
```

---

## Appendix A — Codification tables

All 16 codification tables from `backend/core/dora.py` are listed below. The EBA XLS "Drop down" sheet contains 18 lists total; the two additional lists — **LISTCOUNTRY** (~251 entries, ISO 3166-1 alpha-2) and **LISTCURRENCY** (~166 entries, ISO 4217) — are standard ISO enumerations and are not maintained in `dora.py`. See [Section 3.2](#32-iso-standards) for their export format.

### LIST0101040 — Entity Type

**Python constant**: `DORA_ENTITY_TYPE_CHOICES` (24 entries)

| Code | Label |
|---|---|
| `eba_CT:x12` | Credit institutions |
| `eba_CT:x599` | Investment firms |
| `eba_CT:x643` | Central counterparties (CCPs) |
| `eba_CT:x639` | Asset management companies |
| `eba_CT:x301` | Account information service providers |
| `eba_CT:x302` | Electronic money institutions |
| `eba_CT:x303` | Crypto-asset service providers |
| `eba_CT:x304` | Central security depository |
| `eba_CT:x305` | Trading venues |
| `eba_CT:x306` | Trade repositories |
| `eba_CT:x300` | Payment institution |
| `eba_CT:x316` | Other financial entity |
| `eba_CT:x315` | Securitisation repository |
| `eba_CT:x314` | Crowdfunding service providers |
| `eba_CT:x313` | Administrator of critical benchmarks |
| `eba_CT:x312` | Credit rating agency |
| `eba_CT:x311` | Institutions for occupational retirement provision |
| `eba_CT:x320` | Insurance intermediaries, reinsurance intermediaries and ancillary insurance intermediaries |
| `eba_CT:x309` | Insurance and reinsurance undertakings |
| `eba_CT:x308` | Data reporting service providers |
| `eba_CT:x307` | Managers of alternative investment funds |
| `eba_CT:x318` | Non-financial entity: Other than ICT intra-group service provider |
| `eba_CT:x317` | Non-financial entity: ICT intra-group service provider |
| `eba_CT:x310` | Issuers of asset-referenced tokens |

### LIST0102050 — Entity Hierarchy

**Python constant**: `DORA_ENTITY_HIERARCHY_CHOICES` (5 entries)

| Code | Label |
|---|---|
| `eba_RP:x53` | Ultimate parent |
| `eba_RP:x551` | Parent other than ultimate parent |
| `eba_RP:x56` | Subsidiary |
| `eba_RP:x21` | Entities other than entities of the group |
| `eba_RP:x210` | Outsourcing |

### LIST0201020 — Contractual Arrangement Type

**Python constant**: `DORA_CONTRACTUAL_ARRANGEMENT_CHOICES` (3 entries)

| Code | Label |
|---|---|
| `eba_CO:x1` | Standalone arrangement |
| `eba_CO:x2` | Overarching arrangement |
| `eba_CO:x3` | Subsequent or associated arrangement |

### LIST0202090 — Termination Reason

**Python constant**: `TERMINATION_REASON_CHOICES` (6 entries)

| Code | Label |
|---|---|
| `eba_CO:x4` | Termination not for cause: Expired and not renewed |
| `eba_CO:x5` | Termination for cause: Provider in breach of applicable law, regulations or contractual provisions |
| `eba_CO:x6` | Termination for cause: Identified impediments of the provider capable of altering the supported function |
| `eba_CO:x7` | Termination for cause: Provider's weaknesses regarding the management and security of sensitive data or information |
| `eba_CO:x8` | Termination: As requested by the competent authority |
| `eba_CO:x9` | Other reasons for termination |

### LISTANNEXIII — ICT Service Type

**Python constant**: `DORA_ICT_SERVICE_CHOICES` (19 entries)

| Code | Label |
|---|---|
| `eba_TA:S01` | ICT project management |
| `eba_TA:S02` | ICT Development |
| `eba_TA:S03` | ICT help desk and first level support |
| `eba_TA:S04` | ICT security management services |
| `eba_TA:S05` | Provision of data |
| `eba_TA:S06` | Data analysis |
| `eba_TA:S07` | ICT, facilities and hosting services (excluding Cloud services) |
| `eba_TA:S08` | Computation |
| `eba_TA:S09` | Non-Cloud Data storage |
| `eba_TA:S10` | Telecom carrier |
| `eba_TA:S11` | Network infrastructure |
| `eba_TA:S12` | Hardware and physical devices |
| `eba_TA:S13` | Software licencing (excluding SaaS) |
| `eba_TA:S14` | ICT operation management (including maintenance) |
| `eba_TA:S15` | ICT Consulting |
| `eba_TA:S16` | ICT Risk management |
| `eba_TA:S17` | Cloud services: IaaS |
| `eba_TA:S18` | Cloud services: PaaS |
| `eba_TA:S19` | Cloud services: SaaS |

### LISTBINARY — Yes/No

**Python constant**: `DORA_BINARY_CHOICES` (2 entries)

| Code | Label |
|---|---|
| `eba_BT:x28` | Yes |
| `eba_BT:x29` | No |

### LIST0202170 — Data Sensitiveness

**Python constant**: `DORA_SENSITIVENESS_CHOICES` (3 entries)

| Code | Label |
|---|---|
| `eba_ZZ:x791` | Low |
| `eba_ZZ:x792` | Medium |
| `eba_ZZ:x793` | High |

### LIST0202180 — Level of Reliance

**Python constant**: `DORA_RELIANCE_CHOICES` (4 entries)

| Code | Label |
|---|---|
| `eba_ZZ:x794` | Not significant |
| `eba_ZZ:x795` | Low reliance |
| `eba_ZZ:x796` | Material reliance |
| `eba_ZZ:x797` | Full reliance |

### LIST0401030 — Entity Nature

**Python constant**: `DORA_ENTITY_NATURE_CHOICES` (2 entries)

| Code | Label |
|---|---|
| `eba_ZZ:x838` | branch of a financial entity |
| `eba_ZZ:x839` | not a branch |

### LIST0501040 — Provider Person Type

**Python constant**: `DORA_PROVIDER_PERSON_TYPE_CHOICES` (2 entries)

| Code | Label |
|---|---|
| `eba_CT:x212` | Legal person, excluding individual acting in a business capacity |
| `eba_CT:x213` | Individual acting in a business capacity |

### LIST0601020 — Licensed Activity

**Python constant**: `DORA_LICENSED_ACTIVITY_CHOICES` (128 entries)

See [RT.06.01 b_06.01.0020](#b_06010020--licensed-activity) for the full table organized by category.

### LIST0601050 — Yes/No/Assessment not performed

**Python constant**: `DORA_YES_NO_ASSESSMENT_CHOICES` (3 entries)

| Code | Label |
|---|---|
| `eba_BT:x28` | Yes |
| `eba_BT:x29` | No |
| `eba_BT:x21` | Assessment not performed |

### LIST0601100 — Discontinuing Impact

**Python constant**: `DORA_DISCONTINUING_IMPACT_CHOICES` (4 entries)

| Code | Label |
|---|---|
| `eba_ZZ:x791` | Low |
| `eba_ZZ:x792` | Medium |
| `eba_ZZ:x793` | High |
| `eba_ZZ:x799` | Assessment not performed |

### LIST0701050 — Substitutability

**Python constant**: `DORA_SUBSTITUTABILITY_CHOICES` (4 entries)

| Code | Label |
|---|---|
| `eba_ZZ:x959` | Not substitutable |
| `eba_ZZ:x962` | Easily substitutable |
| `eba_ZZ:x961` | Medium complexity in terms of substitutability |
| `eba_ZZ:x960` | Highly complex substitutability |

### LIST0701060 — Non-Substitutability Reason

**Python constant**: `DORA_NON_SUBSTITUTABILITY_REASON_CHOICES` (3 entries)

| Code | Label |
|---|---|
| `eba_ZZ:x963` | Lack of real alternatives |
| `eba_ZZ:x964` | Difficulties in migrating or reintegrating |
| `eba_ZZ:x965` | Lack of real alternatives and difficulties in migrating or reintegrating |

### LIST0701090 — Reintegration Possibility

**Python constant**: `DORA_REINTEGRATION_POSSIBILITY_CHOICES` (3 entries)

| Code | Label |
|---|---|
| `eba_ZZ:x798` | Easy |
| `eba_ZZ:x966` | Difficult |
| `eba_ZZ:x967` | Highly complex |
