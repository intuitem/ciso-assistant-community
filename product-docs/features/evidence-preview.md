---
description: View attachment content without downloading it
---

# Evidence preview

Most evidence attachments can be read directly in CISO Assistant, without downloading them first. This matters during an audit review, where you may be checking dozens of attachments in a row.

## Where to find it

Open an evidence and scroll to the attachment card below the details — the preview is rendered under the attachment name, next to the **Download** button. The same card appears on an individual evidence revision, so you can inspect what a past version actually contained.

Evidence tables show the **file name** rather than a preview. Previews are deliberately rendered on the detail page only: a thumbnail in a table row is too small to read, and rendering one per row would download every attachment on the page.

## Supported formats

| Type | Formats | Rendered as |
|---|---|---|
| Spreadsheets | `.xlsx`, `.csv` | Interactive table with one tab per sheet |
| Documents | `.docx` | Formatted document |
| Markdown | `.md` | Formatted text |
| Plain text | `.txt`, `.log`, `.json`, `.yaml`, `.yml`, `.toml`, `.xml`, `.eml` | Raw text |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg` | Image |
| PDF | `.pdf` | Embedded document viewer |
| Video | `.mp4`, `.mov` | Player with controls |

Anything else — including legacy Office formats (`.doc`, `.xls`, `.ppt`) and OpenDocument files (`.odt`, `.ods`) — shows **No preview available.** and can still be downloaded.

### Spreadsheets

Spreadsheet previews keep the formatting that makes a workbook readable: cell fills and font styling, borders, merged cells, column widths, frozen header rows, and number formats — so a currency column still reads as currency and a date still reads as a date. Where a workbook has several sheets, each one gets a tab above the preview; hidden sheets are skipped.

Formulas display their last calculated value, exactly as a spreadsheet application shows them on open. Charts, embedded images and pivot tables are not rendered — download the file to see those.

### Documents

Word documents keep headings, bold and italic text, lists and tables. Links are shown as plain text rather than clickable links, and remote images are not loaded — a preview never reaches out to an external server, so opening a supplier's document cannot signal back to whoever sent it.

## Size limits

Large files are not rendered in full, to keep the page responsive:

- Text and Markdown files above 5 MB, and documents and spreadsheets above 10 MB, show **File is too large to preview. Download it to view its content.**
- Long files are cut off at 5 000 lines; spreadsheets at 2 000 rows, 100 columns and 50 sheets per file. When that happens the preview shows **Preview truncated. Download the file to see everything.**

In both cases the attachment itself is untouched — **Download** always gives you the complete file.

## Related

- [Evidence](../concepts/evidence.md)
- [Evidences from clipboard](evidences-from-clipboard.md)
