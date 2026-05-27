---
description: Excel self-assessment export aligned with Belgium's Centre for Cybersecurity
---

# CCB CyFun

The [Centre for Cybersecurity Belgium](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework) (CCB) publishes the **CyberFundamentals** framework as a self-assessment Excel workbook with a specific layout: one sheet per NIST CSF function (GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER), rows pre-populated with controls, and answer cells where the responder records their posture.

CISO Assistant can export an existing CyFun audit directly into that workbook so you can submit the file to the CCB without retyping any data.

## How it works

1. Load the **CCB CyFun 2025** framework library (essential, important, or key, depending on your scope).
2. Run an audit against that framework as usual — assess each requirement, attach evidence, link applied controls.
3. From the audit detail page, choose **Export → CyFun Excel**. The platform fills the official CCB template using the assessment data and downloads it.

The export is restricted to audits whose framework URN matches the CyFun 2025 framework — exporting an audit on a different framework returns an error rather than producing a malformed workbook.

## What lands in the workbook

- Each CyFun requirement's status and score are written to the appropriate sheet and row.
- Free-text notes from requirement assessments populate the comments column.
- The official template scaffolding (cover page, formulas, summary sheet) is preserved untouched.

## Related

- [CyFun framework on the CCB website](https://atwork.safeonweb.be/tools-resources/cyberfundamentals-framework)
- [Audits concept](../../concepts/audits.md)
