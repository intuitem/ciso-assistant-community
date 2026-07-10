---
description: Excel self-assessment export aligned with Belgium's Centre for Cybersecurity
---

# CCB CyFun

The [Centre for Cybersecurity Belgium](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework) (CCB) publishes the **CyberFundamentals** framework as a self-assessment Excel workbook with a specific layout: one sheet per NIST CSF function (GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER), rows pre-populated with controls, and answer cells where the responder records their posture.

CISO Assistant can export an existing CyFun audit directly into that workbook so you can submit the file to the CCB without retyping any data.

## How it works

1. Load the **CCB CyFun 2025** framework library (essential, important, or key, depending on your scope).
2. Run an audit against that framework as usual — assess each requirement, attach evidence, link applied controls.
3. From the audit's **Export** menu, choose **CyFun self-assessment**. The platform fills the official CCB template using the assessment data and downloads it.

The **CyFun self-assessment** option only appears when the audit is based on the **CyFun 2025** framework — for any other framework it isn't offered, so you can't accidentally produce a malformed workbook.

## Before you export

The export writes each requirement's **score** into the official template, so two audit settings have to line up first — both on the audit's edit form under **More** (see [Customize your audit](../../guides/customize-audit.md)):

- **Make the score visible.** The **Score** field defaults to _Hidden_ in [field visibility](../../guides/customize-audit.md#field-visibility). Switch it on (and **Documentation score** if you use it) so the score is recorded and lands in the workbook.
- **Use _Average of averages_ scoring.** Set the [score calculation method](../../guides/customize-audit.md#score-calculation-method) to **Average of averages** — that's the roll-up logic the CyFun framework expects, grouping requirements by category and averaging the category averages.

## What lands in the workbook

- Each CyFun requirement's status and score are written to the appropriate sheet and row.
- Free-text notes from requirement assessments populate the comments column.
- The official template scaffolding (cover page, formulas, summary sheet) is preserved untouched.

## Related

- [CyFun framework on the CCB website](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework)
- [Audits concept](../../concepts/audits.md)
