---
description: Excel self-assessment import and export aligned with Belgium's Centre for Cybersecurity
---

# CCB CyFun

The [Centre for Cybersecurity Belgium](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework) (CCB) publishes the **CyberFundamentals** framework as a self-assessment Excel workbook with a specific layout: one sheet per NIST CSF function (GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER), rows pre-populated with controls, and answer cells where the responder records their documentation and implementation maturity scores.

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

1. Load the **CCB CyFun 2025** framework library.
2. Run an audit against that framework as usual — assess each requirement, attach evidence, link applied controls.
3. From the audit's **Export** menu, choose **CyFun self-assessment**. The platform fills the official CCB template using the assessment data and downloads it.

The **CyFun self-assessment** option only appears when the audit is based on the **CyFun 2025** framework — for any other framework it isn't offered, so you can't accidentally produce a malformed workbook.

### Before you export

The export writes each requirement's **score** into the official template, so two audit settings have to line up first — both on the audit's edit form under **More** (see [Customize your audit](../../guides/customize-audit.md)). Audits created by the CyFun import already have these set; this only matters for audits created manually:

- **Make the score visible.** The **Score** field defaults to _Hidden_ in [field visibility](../../guides/customize-audit.md#field-visibility). Switch it on (and **Documentation score** if you use it) so the score is recorded and lands in the workbook.
- **Use _Average of averages_ scoring.** Set the [score calculation method](../../guides/customize-audit.md#score-calculation-method) to **Average of averages** — that's the roll-up logic the CyFun framework expects, grouping requirements by category and averaging the category averages.

### What lands in the workbook

- Each requirement's **documentation score** and **implementation score** are written to the appropriate sheet and row; **Not applicable** results are written as `N/A`.
- Observations from requirement assessments populate the comments column.
- The official template scaffolding (cover page, formulas, summary sheet) is preserved untouched.

## Related

- [CyFun framework on the CCB website](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework)
- [Data import wizard](../../configuration/data-import.md)
- [Audits concept](../../concepts/audits.md)
