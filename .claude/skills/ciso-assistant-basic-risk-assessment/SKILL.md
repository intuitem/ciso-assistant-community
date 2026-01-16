---
name: ciso-assistant-basic-risk-assessment
description: |
  Guide users through a basic risk assessment workflow in CISO Assistant, from asset identification to scenario creation. Use when:
  (1) User wants to start a risk assessment from scratch
  (2) User mentions "risk assessment", "identify risks", "threat scenarios", or "risk register"
  (3) User asks about qualitative vs quantitative risk approaches
  (4) User needs help identifying assets, threats, or creating risk scenarios

  Covers: risk approach selection (qualitative/quantitative), organizational context gathering, asset identification (primary/supporting), threat catalog usage, scenario generation from threat-asset combinations, risk assessment/study creation.
---

# CISO Assistant Basic Risk Assessment

Guide users through risk assessment setup using MCP server tools.

## Prerequisites

1. **Verify MCP server connectivity** - Test with `get_folders()`
2. **Backend must be running** - CISO Assistant backend at configured URL
3. **If MCP tools unavailable** - Fall back to direct API calls (see bootstrap skill)

---

## Key Principles

### Always Pass folder_id for Scoping

When creating objects, **always pass `folder_id`** to scope lookups and avoid ambiguity errors when objects with the same name exist in different folders.

```python
# CORRECT - folder_id scopes all lookups to ACME folder
create_risk_scenario(
  name="Ransomware on Customer Data",
  risk_assessment_id="ACME Risk Assessment 2025",
  folder_id="ACME",  # <- Scopes asset/threat lookups
  assets=["Customer Data"],
  threats=["Ransomware"],
  threat_library="urn:intuitem:risk:library:intuitem-common-catalog"
)
```

### Always Use threat_library for Threat Lookups

Threats exist in multiple libraries (intuitem catalog, MITRE ATT&CK, etc.). Always specify the library:

```python
threat_library="urn:intuitem:risk:library:intuitem-common-catalog"
```

### Include Relevance in Scenario Descriptions

Always explain **why** a scenario matters for this specific organization:

```
"Ransomware attack encrypting customer data, leading to service disruption.
Relevance: GDPR breach implications with mandatory 72-hour notification
and potential fines up to 4% of annual revenue."
```

---

## Workflow

### Step 1: Choose Risk Approach

Ask the user which approach they prefer:

| Approach | Description | Best For |
|----------|-------------|----------|
| **Qualitative** | Probability/impact scales (Low/Medium/High), 4x4 or 5x5 matrix | Initial assessments, stakeholder communication |
| **Quantitative** | Monetary values, Monte Carlo simulations, ALE calculations | Mature orgs, budget justification, executive reporting |

### Step 2: Gather Organizational Context

Ask about:
- **Industry**: healthcare, financial, tech/SaaS, retail, manufacturing, government
- **Size**: small (1-50), medium (50-500), large (500+)
- **Region**: for regulatory context (EU → GDPR, US healthcare → HIPAA, etc.)
- **Cloud**: AWS/Azure/GCP, SaaS-heavy or on-premise
- **Compliance**: specific requirements (HIPAA, PCI-DSS, GDPR, SOC2, ISO 27001)

### Step 3: Create Domain and Perimeter

```python
# 1. Create folder (domain)
create_folder(name="ACME", description="ACME Corp - Tech/SaaS, EU-based")

# 2. Create perimeter (assessment scope)
create_perimeter(name="ACME Platform", folder_id="ACME")
```

### Step 4: Identify and Create Assets

Use [references/typical-assets.md](references/typical-assets.md) to suggest assets based on context.

**Primary Assets (PR)** - Business value:
- Customer/employee data, financial records, source code, API keys/secrets

**Supporting Assets (SP)** - Infrastructure:
- Cloud infrastructure, databases, CI/CD pipeline, email, endpoints

```python
# Create assets - always pass folder_id
create_asset(name="Customer Data", description="Customer PII - GDPR relevant",
             asset_type="PR", folder_id="ACME")
create_asset(name="Production Database", description="Primary data storage",
             asset_type="SP", folder_id="ACME")
```

### Step 5: Import Threat Catalog

```python
# Import the intuitem common catalog (23 threats)
import_stored_library("urn:intuitem:risk:library:intuitem-common-catalog")

# Verify threats are available
get_threats(library="urn:intuitem:risk:library:intuitem-common-catalog")
```

### Step 6: Generate Scenario Suggestions

Use the **Threat-Asset Relevance Matrix** in [references/typical-assets.md](references/typical-assets.md) to suggest the most relevant threat-asset combinations.

**Naming convention**: `[Threat] on [Asset]`
- "Ransomware on Customer Data"
- "Phishing targeting Employees"
- "Cloud Misconfiguration"

Present top 10-15 combinations and let user select which to create.

### Step 7: Create Assessment Container

**For Qualitative:**
```python
# Check available matrices
get_risk_matrices()

# Use matrix UUID to avoid ambiguity
create_risk_assessment(
  name="ACME Risk Assessment 2025",
  risk_matrix_id="<matrix-uuid>",  # Use UUID from get_risk_matrices()
  perimeter_id="ACME Platform",
  folder_id="ACME",
  status="in_progress"
)
```

**For Quantitative:**
```python
create_quantitative_risk_study(
  name="ACME Quantitative Risk Study 2025",
  folder_id="ACME",
  distribution_model="lognormal_ci90"
)
```

### Step 8: Create Risk Scenarios

**For Qualitative:**
```python
create_risk_scenario(
  name="Ransomware on Customer Data",
  description="Ransomware attack encrypting customer data. Relevance: GDPR breach with 72-hour notification requirement.",
  risk_assessment_id="ACME Risk Assessment 2025",
  folder_id="ACME",  # CRITICAL: scope lookups
  assets=["Customer Data"],
  threats=["Ransomware"],
  threat_library="urn:intuitem:risk:library:intuitem-common-catalog"
)
```

**For Quantitative:**
```python
create_quantitative_risk_scenario(
  name="Ransomware on Customer Data",
  description="Ransomware attack... Relevance: ...",
  quantitative_risk_study_id="ACME Quantitative Risk Study 2025",
  folder_id="ACME",
  assets=["Customer Data"],
  threats=["Ransomware"],
  threat_library="urn:intuitem:risk:library:intuitem-common-catalog"
)
```

### Step 9: Summary and Next Steps

After creating scenarios, summarize and guide on next steps:

**For Qualitative:**
1. Rate probability and impact for each scenario in the UI
2. Identify and link existing controls
3. Plan additional controls for high-risk scenarios
4. Review risk matrix visualization

**For Quantitative:**
1. Create hypotheses with probability and impact bounds
2. Run Monte Carlo simulations
3. Set risk tolerance curve
4. Analyze portfolio-level risk

---

## Quick Reference

### MCP Tools

| Category | Tool | Key Parameters |
|----------|------|----------------|
| **Setup** | `create_folder()` | name, description |
| | `create_perimeter()` | name, folder_id |
| **Assets** | `create_asset()` | name, description, asset_type, folder_id |
| | `get_assets()` | folder |
| **Threats** | `import_stored_library()` | urn_or_id |
| | `get_threats()` | library, folder, limit |
| **Qualitative** | `get_risk_matrices()` | - |
| | `create_risk_assessment()` | name, risk_matrix_id, perimeter_id, folder_id |
| | `create_risk_scenario()` | name, description, risk_assessment_id, folder_id, assets, threats, threat_library |
| **Quantitative** | `create_quantitative_risk_study()` | name, folder_id, distribution_model |
| | `create_quantitative_risk_scenario()` | name, quantitative_risk_study_id, folder_id, assets, threats, threat_library |

### Common Threat Library URN

```
urn:intuitem:risk:library:intuitem-common-catalog
```

### Threat Catalog Quick Reference

| Threat | Typical Target Assets |
|--------|----------------------|
| Ransomware | Customer Data, Databases, File Storage |
| Phishing | Employee Endpoints, Corporate Email |
| Data Breach/Leak | Customer Data, Source Code, API Keys |
| Cloud Security Threats | Cloud Infrastructure, SaaS Apps |
| API Security Threats | Application Code, API Gateway |
| Insider Threats | API Keys/Secrets, Source Code |
| Supply Chain Attacks | CI/CD Pipeline, Dependencies |
| Password Attacks | Corporate Email, Admin Accounts |
| System Outage | Production Database, Core Services |
| Regulatory Non-Compliance | Customer Data (GDPR/HIPAA/PCI) |
| Social Engineering | Employee Endpoints, Finance Team |

---

## Fallback: Direct API Calls

If MCP tools unavailable:
- `POST /api/folders/`
- `POST /api/perimeters/`
- `POST /api/assets/`
- `POST /api/stored-libraries/<urn>/import/`
- `POST /api/risk-assessments/`
- `POST /api/risk-scenarios/`
- `POST /api/crq/quantitative-risk-studies/`
- `POST /api/crq/quantitative-risk-scenarios/`
