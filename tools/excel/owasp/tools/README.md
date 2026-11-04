# OWASP Top 10 framework builder

This directory contains a three-step builder for CISO Assistant:

1. `owasp_top10_export_json.py` extracts the official Markdown source and translations, using English file-level fallbacks when needed.
2. `owasp_top10_build_excel.py` creates the CISO Assistant XLSX library.
3. `owasp_top10_framework_builder.py` orchestrates the download, extraction, XLSX build, YAML conversion, and cleanup.

The default release is 2025. The parser is also compatible with the 2021 source layout.

## Usage

From the `intuitem` workspace root:

```powershell
.\.venv\Scripts\python.exe .\ciso-assistant-community\tools\excel\owasp\tools\owasp_top10_framework_builder.py
```

Build the 2021 release:

```powershell
.\.venv\Scripts\python.exe .\ciso-assistant-community\tools\excel\owasp\tools\owasp_top10_framework_builder.py -y 2021
```

Generate a distinguishable Excel file without replacing an existing workbook:

```powershell
.\.venv\Scripts\python.exe .\ciso-assistant-community\tools\excel\owasp\tools\owasp_top10_framework_builder.py --output-suffix relative-links-fixed --skip-yaml
```

This produces, for example,
`owasp-top-10-web-2025-relative-links-fixed.xlsx` while preserving
`owasp-top-10-web-2025.xlsx`.

Use an already extracted checkout:

```powershell
.\.venv\Scripts\python.exe .\ciso-assistant-community\tools\excel\owasp\tools\owasp_top10_framework_builder.py --source-root C:\path\to\Top10-master
```

The generated XLSX, YAML, and relative-link conversion log files are written to
the parent `owasp` directory. The final summary reports the number and list of
exported languages, the default language, English file fallbacks, any languages
that were skipped, and the path to the detailed `.log` file.

The console output follows the other framework builders: numbered step banners,
emoji status markers, an aligned summary, explicit warnings, and cleanup messages.

## Extraction rules

- English is the default locale.
- Exported language identifiers always use their two-letter code. For example,
  `pt-BR` becomes `pt` and `zh-Hant` becomes `zh`. When multiple source locales
  share the same code, the most complete source is selected and the duplicate is
  reported as skipped.
- A locale is exported when at least half of its ten category pages are available. Languages below that threshold are skipped entirely.
- A missing `index.md` or category page uses the complete English equivalent.
- Copyright is extracted once from the English `About_OWASP.md` file and is not translated.
- A category page that does not contain all sections needed by the workbook uses the complete English category page instead of mixing languages inside one threat.
- Every fallback and skipped language is reported in the final summary.
- Threat reference identifiers include the release year, for example `A01:2025`.
- The threat `description` contains the complete Description section without its title.
- The threat `annotation` contains `Score table`, `How to prevent`, and `Example attack scenarios` in that order, followed by the source-page link.
- English annotations use the canonical section titles above. Translated
  annotations preserve the corresponding section titles from each source page.
  When a complete category page falls back to English, its section titles also
  remain in English.
- Generated labels and sentences, including `Source` and the final references/CWE sentence, are translated for every exported language.
- Generated links target the published OWASP Top 10 website. Markdown filenames map directly to page paths without the `.md` extension; English pages are at the year root, while translated pages retain their full source locale such as `pt-BR` or `zh-Hant`.
- Markdown and embedded HTML tables are preserved.
- Soft-wrapped 2021 prose is normalized for English, German, Spanish,
  Indonesian, Italian, Japanese, and Portuguese. Markdown tables, headings,
  distinct list items, code blocks, HTML blocks, and explicit line breaks remain
  unchanged.
- Markdown links to repository-relative paths are replaced with bold link text;
  absolute URLs and same-page anchors are preserved. The console summary shows
  the conversion count and log path. The generated `*-relative-links.log` file
  lists every removed relative target with its threat `ref_id`, locale, source
  file, section, original link, and bold replacement.
- Worksheet gridlines remain visible.
- For 2021, the threat base URN is `urn:intuitem:risk:threat`.
- For later releases, the threat base URN is derived from the year-specific library URN.

Source repository: <https://github.com/OWASP/Top10>

Published website: <https://top10.owasp.org/>
