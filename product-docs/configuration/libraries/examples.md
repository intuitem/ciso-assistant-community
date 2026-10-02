---
description: Explore the available library Excel examples
---

# Excel examples

If the workbook structure feels unfamiliar, start by exploring one of these completed examples. Download a file and open it in Excel or LibreOffice to see how its sheets fit together.

Both workbooks include an `info` sheet that explains the example. It is for reference only and is not required library content. For the shared workbook structure, see [Excel file anatomy](excel-file-anatomy.md).

## Example framework

[Download `example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx)

This broad example shows a framework with a hierarchy of sections and assessable requirements, plus several optional supporting objects. It is useful when you want to see how framework requirements, scoring, answers, implementation groups, threats, and reference controls can be represented in one library.

Here are the object types you will find in this example:

| Sheets | What they contain |
| --- | --- |
| `library_meta` | The library's identity and shared metadata. |
| `fwk_meta`, `fwk_content` | Framework metadata and its hierarchy of sections and requirements. The content also illustrates questions, requirement-level scoring, implementation groups, and references to threats and controls. |
| `imp_grp_meta`, `imp_grp_content` | Implementation group definitions. |
| `answ_meta`, `answ_content` | Answer types and reusable answer choices for framework questions. |
| `scr_meta`, `scr_content` | The framework's main scoring scale. |
| `scr_binary_meta`, `scr_binary_content` | An additional score definition that can be used for specific requirements. It is another score set, not a separate object type. |
| `thrt_meta`, `thrt_content` | A sample threat catalogue. |
| `ref_ctrl_meta`, `ref_ctrl_content` | A sample reference control catalogue. |
| `urn_pref_meta`, `urn_pref_content` | URN prefixes the framework can use to reference internal or external threats and reference controls. |

## Example questionnaire

[Download `example_questionnaire.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_questionnaire.xlsx)

A questionnaire in CISO Assistant is still a **framework**. This example focuses on requirements assessed through questions and demonstrates more advanced questionnaire behavior, including conditional questions, implementation groups, answer-choice scoring and compliance results, and translations.

Here are the object types you will find in this example:

| Sheets | What they contain |
| --- | --- |
| `library_meta` | The library's identity and shared metadata. |
| `fwk_meta`, `fwk_content` | Framework metadata and requirements. Questions are written directly in the framework content; the example also includes conditional-question fields. |
| `imp_grp_meta`, `imp_grp_content` | Implementation groups used to scope questionnaire requirements and choices. |
| `answ_meta`, `answ_content` | Reusable answer types and choices, with examples of scoring, compliance results, colors, and translations. |

### Which one should I check first?

Start with the framework example to understand the general workbook structure and see several library objects together. Then, explore the questionnaire example if your framework will guide users through structured questions and answers. It shows conditional questions and how answer choices can affect scores and compliance results.
