---
name: ciso-assistant-bootstrap
description: |
  Bootstrap CISO Assistant for new users by guiding them through initial setup. Use when:
  (1) User wants to set up CISO Assistant from scratch
  (2) User mentions "bootstrap", "initial setup", "getting started", or "onboarding" with CISO Assistant
  (3) User needs help creating their organizational structure, loading frameworks, or configuring risk assessments

  Covers: domains/folders, perimeters, industry-based framework selection, assets, risk assessment type (qualitative vs quantitative), third-party entities and solutions, and compliance vs risk focus.
---

# CISO Assistant Bootstrap

Guide users through CISO Assistant initial setup using MCP server tools.

## Prerequisites

Before starting:

1. **Verify MCP server connectivity** - Check that `ciso-assistant` MCP server is available in your tools. Test with:
   ```
   get_folders()  # Should return a list of folders
   ```

2. **If MCP tools are not available:**
   - Ask user to verify MCP server is configured in their Claude Code settings
   - Check `.mcp.json` or MCP configuration includes `ciso-assistant` server
   - Ensure `API_URL` and `TOKEN` environment variables are set
   - As a last resort, fall back to direct API calls (see Fallback section)

3. **Backend must be running** - CISO Assistant backend at the configured `API_URL`

## Bootstrap Flow

**Always use MCP tools as the primary method.** They provide:
- Automatic name-to-ID resolution (no need to track UUIDs)
- Better error handling with guidance
- Consistent response formatting

### 1. Gather Information

Ask the user about:

**Organization Structure**
- Domain name(s) and hierarchy (e.g., "IT Security", "Compliance", "Operations")
- Perimeter(s) for each domain (assessment scopes)

**Focus Area**
- Compliance-focused (framework audits)
- Risk-focused (risk assessments)
- Both

**Industry** (for framework recommendations)
- See [references/frameworks-by-industry.md](references/frameworks-by-industry.md) for mapping

**Risk Assessment Type** (if risk-focused or both)
- Qualitative (matrix-based): most common approach, uses probability/impact scales (3x3, 4x4, 5x5)
- Quantitative: advanced monetary modeling with distributions, Monte Carlo simulations

**Assets**
- Primary assets (PR): core business assets (data, applications, processes)
- Supporting assets (SP): infrastructure supporting primary assets

**Third Parties** (if applicable)
- Critical vendors/suppliers (entities)
- Solutions they provide
- Criticality level (0-4)

### 2. Create Resources via MCP (Order Matters)

Execute MCP tools in this order:

```
1. create_folder(name, description)
   └─ 2. create_perimeter(name, description, folder)
         └─ 3. create_asset(name, description, asset_type, folder)
         └─ 4. import_stored_library(library_urn)
         └─ 5a. create_risk_assessment(name, risk_matrix, perimeter)
         └─ 5b. create_compliance_assessment(name, framework, perimeter)
         └─ 6. create_entity(name, folder, ...)
               └─ 7. create_solution(name, provider_entity, criticality, assets)
```

**Note:** MCP tools accept names directly (e.g., `folder="My Domain"`) - no need to look up IDs first.

### 3. Key MCP Tools

**Organization:**
- `create_folder(name, description, parent_folder)` - Create domain
- `create_perimeter(name, description, folder)` - Create assessment scope

**Assets:**
- `create_asset(name, description, asset_type, folder)` - asset_type: "PR" or "SP"

**Frameworks:**
- `get_stored_libraries(object_type="framework")` - List available frameworks
- `import_stored_library(library_urn)` - Load framework (e.g., "urn:intuitem:risk:library:iso27001-2022")

**Risk Assessment (Qualitative):**
- `get_risk_matrices()` - List available matrices
- `create_risk_assessment(name, risk_matrix, perimeter)` - Create assessment

**Risk Assessment (Quantitative):**
- `create_quantitative_risk_study(name, distribution_model, loss_threshold, ...)` - Create study

**Compliance:**
- `create_compliance_assessment(name, framework, perimeter)` - Create audit

**TPRM:**
- `create_entity(name, folder, description, country, currency, default_dependency, default_maturity, default_trust)` - Create vendor
- `create_solution(name, provider_entity, criticality, assets)` - Create service
- `create_representative(email, entity, first_name, last_name, role)` - Create contact

### 4. Example Bootstrap Session

```
User: "I want to set up CISO Assistant for my healthcare startup"

1. Verify MCP connectivity:
   get_folders()  # Confirm MCP server responds

2. Ask clarifying questions:
   - "What domains do you need? (e.g., IT, Compliance, Operations)"
   - "Are you focused on compliance, risk management, or both?"
   - "Do you prefer qualitative (matrix-based) or quantitative risk assessment?"
   - "What are your critical assets? (applications, databases, etc.)"
   - "Do you have critical third-party vendors to track?"

3. Based on healthcare industry, recommend:
   - HIPAA-related frameworks
   - ISO 27001:2022
   - NIST CSF 2.0

4. Create resources via MCP tools:
   create_folder("HealthTech Corp", "Main organization domain")
   create_perimeter("Production Environment", "Production systems scope", folder="HealthTech Corp")
   create_asset("Patient Portal", "Main patient-facing application", "PR", folder="HealthTech Corp")
   create_asset("AWS Infrastructure", "Cloud hosting", "SP", folder="HealthTech Corp")
   import_stored_library("urn:intuitem:risk:library:iso27001-2022")
   create_compliance_assessment("ISO 27001 Audit 2025", framework="ISO 27001:2022", perimeter="Production Environment")
   create_entity("AWS", folder="HealthTech Corp", description="Cloud provider")
   create_solution("Cloud Hosting", provider_entity="AWS", criticality=3, assets=["AWS Infrastructure"])
```

## Risk Matrix Selection

For qualitative assessments, help user choose:

| Matrix | Use Case |
|--------|----------|
| 3x3 | Simple, quick assessments |
| 4x4 | Balanced granularity |
| 5x5 | Detailed, enterprise-grade |

Use `get_risk_matrices()` to list available options.

## Validation

After setup, verify with MCP tools:
- `get_folders()` - Confirm domains created
- `get_perimeters(folder)` - Confirm scopes
- `get_assets(folder)` - Confirm assets
- `get_loaded_libraries()` - Confirm frameworks loaded
- `get_entities(folder)` - Confirm third parties

## Fallback: Direct API Calls

**Only use if MCP tools are unavailable.** Requires manual UUID tracking.

Read token from `.mcp.json` or ask user for it, then:

```bash
# Create folder
curl -X POST "http://localhost:8000/api/folders/" \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Domain", "description": "..."}'

# Create perimeter (requires folder UUID from previous response)
curl -X POST "http://localhost:8000/api/perimeters/" \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "common", "folder": "<folder_uuid>"}'

# Similar pattern for other endpoints:
# POST /api/assets/
# POST /api/stored-libraries/<urn>/import/
# POST /api/risk-assessments/
# POST /api/compliance-assessments/
# POST /api/entities/
# POST /api/solutions/
```
