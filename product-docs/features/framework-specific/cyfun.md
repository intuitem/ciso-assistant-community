---
description: Excel self-assessment import and export aligned with Belgium's Centre for Cybersecurity
---

# CCB CyFun

The [Centre for Cybersecurity Belgium](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework) (CCB) publishes the **CyberFundamentals** framework as a self-assessment Excel workbook with a specific layout: rows pre-populated with controls, and answer cells where the responder records their documentation and implementation maturity scores. The CyFun 2025 tools come one per assurance level, with one sheet per NIST CSF function (GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER); the CyFun 2023 tool covers the three levels in one workbook, with one **Details** sheet per level.

CISO Assistant works with that workbook in both directions:

- **Export** an existing CyFun audit into the official template, ready to submit to the CCB without retyping any data.
- **Import** a filled self-assessment workbook to create a fully scored audit — useful when a customer or entity hands you their completed CyFun spreadsheet.

## Importing a filled workbook

The import accepts the official **CyFun 2025** self-assessment tools, in any of the three editions — **BASIC**, **IMPORTANT**, or **ESSENTIAL**. Nothing is inferred from the file name: the workbook is recognised by its sheets and headers, so renamed or re-saved copies work fine. The older CyFun 2023 workbook is not supported and is rejected with a clear error.

One import creates one new audit:

1. The **CyFun 2025** framework library is loaded automatically if it isn't already.
2. The assurance level is detected from the workbook content, and the audit's implementation group is set to match (basic, important, or essential), so the audit scopes to exactly the requirements of that edition.
3. For every requirement row, the **Documentation Score** and **Implementation Score** land on the matching requirement assessment, and scoring — including the documentation score — is switched on for the audit automatically. Global and per-category maturity scores are then computed by the platform as usual.
4. Rows marked `N/A` in the workbook become **Not applicable** results.
5. The **Comments and/or additional information** and **Assessor comments** cells are carried into the requirement's observation.

### From the Data Wizard (Pro)

Open **Extra** → **Data Wizard** in the sidebar, pick **CyFun self-assessment** as the model, select the target **Domain** (or a **Perimeter**), and upload the workbook. No framework selection is needed — it is derived from the file.

### From the CLI

```bash
uv run clica.py import-cyfun-assessment \
  --file CyFun2025_Self-Assessment_tool.xlsx \
  --folder "My domain" \
  --name "ACME CyFun self-assessment"
```

`--perimeter` can be used instead of `--folder`; `--name` is optional and defaults to a timestamped name. See the [data import wizard](../../configuration/data-import.md) page for CLI setup.

## Exporting an audit to the workbook

1. Load the **CCB CyFun 2025** framework library (or **CCB CyFun 2023** for an audit on the previous version).
2. Run an audit against that framework as usual — assess each requirement, attach evidence, link applied controls.
3. From the audit's **Export** menu, choose **CyFun self-assessment**. The platform fills the official CCB template using the assessment data and downloads it. It picks the template of the audit's assurance level from its implementation groups: **BASIC** when only BASIC groups are selected, **IMPORTANT** when the highest is an IMPORTANT group, **ESSENTIAL** otherwise (including when no group is selected). Each template lists only its level's requirements and applies its own N/A score and thresholds. A CyFun 2023 audit goes to the CCB's CyFun 2023 tool instead, where the export fills the sheet of the audit's level — **BASIC Details**, **IMPORTANT Details** or **ESSENTIAL Details** — picked the same way.

The **CyFun self-assessment** option only appears when the audit is based on the **CyFun 2025** or **CyFun 2023** framework — for any other framework it isn't offered, so you can't accidentally produce a malformed workbook.

### Before you export

The export writes each requirement's **score** into the official template, so a few audit settings have to line up first — all on the audit's edit form under **More** (see [Customize your audit](../../guides/customize-audit.md)). Audits created by the CyFun import already have these set; this only matters for audits created manually:

- **Make the score visible.** New CyFun audits show the **Score** and **Documentation score** fields to auditors and respondents by default. On audits created before that, they may still be _Hidden_ in [field visibility](../../guides/customize-audit.md#field-visibility): switch them on so the scores are recorded and land in the workbook.
- **Use _Average of averages_ scoring.** Set the [score calculation method](../../guides/customize-audit.md#score-calculation-method) to **Average of averages** — that's the roll-up logic the CyFun framework expects, grouping requirements by category and averaging the category averages. New CyFun audits are created with this method by default; audits created before that may still use **Average**. Scores are shown with two decimals, like the CCB workbook.
- **Count N/A like the CCB tools.** The CyFun 2025 self-assessment tools count each N/A requirement as **2.5** at the BASIC level and **3** at IMPORTANT and ESSENTIAL. New CyFun 2025 audits do the same by default: [Anchor N/A to target score](../../guides/customize-audit.md#anchor-na-to-target-score) is on, with a **Target score** of 2.5 when only BASIC implementation groups are selected and 3 otherwise. Audits created before that leave N/A requirements out of the score until you set these two fields. The CyFun 2023 tool has no N/A score — its averages leave N/A requirements out — so CyFun 2023 audits keep this option off.

### What lands in the workbook

- Each requirement's **documentation score** and **implementation score** are written to the appropriate sheet and row; **Not applicable** results are written as `N/A`.
- Observations from requirement assessments populate the comments column.
- The official template scaffolding (cover page, formulas, summary sheet) is preserved untouched.

## Checking the CCB conformity criteria

CyFun 2025 audits show, under **Outcomes**, whether they meet the conditions of the CCB's Conformity Assessment Scheme for their assurance level. The check follows the scores as you go:

|                                                                           | BASIC        | IMPORTANT    | ESSENTIAL                                                  |
| ------------------------------------------------------------------------- | ------------ | ------------ | ---------------------------------------------------------- |
| Total maturity                                                            | ≥ 2.5        | ≥ 3          | ≥ 3.5                                                      |
| Each key measure, including those of the lower levels                     | ≥ 2.5        | ≥ 3          | ≥ 3                                                        |
| Each category                                                             | –            | –            | ≥ 3                                                        |
| Requirements marked **Not applicable** (measures excluded from the scope) | at most 1    | at most 3    | at most 5                                                  |
| Never excluded                                                            | key measures | key measures | key measures and controls linked to the management aspects |

A key measure's maturity is the average of its documentation and implementation scores; the total and the categories use the audit's maturity score, as displayed. Each condition lights up green when it holds (total maturity, key measures, categories, exclusions; the category condition holds by default below ESSENTIAL), and **CCB conformity criteria met** when they all do. A completed, conformant audit is therefore all green, and a greyed condition shows what is missing.

This is a self-check: conformity is confirmed by the Conformity Assessment Body, from the official self-assessment tool's summary tab.

## Related

- [CyFun framework on the CCB website](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework)
- [Data import wizard](../../configuration/data-import.md)
- [Audits concept](../../concepts/audits.md)
