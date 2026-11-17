#!/usr/bin/env python3
"""Build a CISO Assistant library workbook from an ASD ISM PDF and annex Excel file.

The Excel file is the canonical source for the requirement hierarchy, IDs, wording,
revision dates and applicability flags. The PDF is used to locate the Principles and
Controls chapters without hard-coded page numbers, validate control coverage, and
extract explanatory descriptions for control topics.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import fitz
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


LIBRARY_SUFFIX = "asd-ism_09-26"
FRAMEWORK_REF_ID = "ASD-ISM_09-26"
FRAMEWORK_NAME = "ASD Information Security Manual (ISM) (September 2026)"
SOURCE_URL = "https://www.cyber.gov.au/ism/2026-09"
LIBRARY_DESCRIPTION = (
    "The purpose of the Information security manual (ISM) is to outline a cyber "
    "security framework that an organisation can apply, using their risk management "
    "framework, to protect their information technology (IT) and operational technology "
    "(OT) systems from cyber threats.\n\n"
    f"Source: {SOURCE_URL}"
)
COPYRIGHT = (
    "© Commonwealth of Australia 2026\n"
    "With the exception of the Coat of Arms and where otherwise stated, all material "
    "presented in this publication is provided under a Creative Commons Attribution 4.0 "
    "International license.\nhttps://creativecommons.org/licenses/by/4.0/"
)
PRINCIPLES_DESCRIPTION = (
    "The purpose of the cyber security principles within the ISM is to provide strategic "
    "guidance on how an organisation can protect their IT and OT systems from cyber "
    "threats. These cyber security principles are grouped into six functions: govern, "
    "identify, protect, detect, respond and recover. An organisation should be able to "
    "demonstrate that the cyber security principles are being adhered to within their "
    "organisation."
)
CONTROLS_DESCRIPTION = (
    "The purpose of the cyber security guidelines within the ISM is to support the cyber "
    "security principles by providing practical guidance on how an organisation can protect "
    "their IT and OT systems from cyber threats. An organisation should consider the cyber "
    "security guidelines that are relevant to each of the systems they operate."
)

CONTENT_HEADERS = [
    "assessable",
    "depth",
    "ref_id",
    "name",
    "description",
    "annotation",
    "implementation_groups",
]

IMPLEMENTATION_GROUPS = [
    (
        "PRINCIPLE",
        "Cyber Security Principles",
        "The principles apply to all classifications. To reproduce the corresponding "
        "ASD scope, select both the classification and Principles.",
    ),
    ("CONTROL", "Cyber Security Guidelines (Controls)", ""),
    ("NC", '[NC] Controls applicable for "Non-Classified" System', ""),
    ("OS", '[OS] Controls applicable for "Official: Sensitive" System', ""),
    ("P", '[P] Controls applicable for "Protected" System', ""),
    ("S", '[S] Controls applicable for "Secret" System', ""),
    ("TS", '[TS] Controls applicable for "Top Secret" System', ""),
    ("ML1", "[ML1] Essential 8 Maturity Level 1 (Controls)", ""),
    ("ML2", "[ML2] Essential 8 Maturity Level 2 (Controls)", ""),
    ("ML3", "[ML3] Essential 8 Maturity Level 3 (Controls)", ""),
]
CLASSIFICATION_GROUPS = ("NC", "OS", "P", "S", "TS")
MATURITY_GROUPS = ("ML1", "ML2", "ML3")
EXCEL_LIST_MARKER_PATTERN = re.compile(
    r"(?m)^([ \t]*)(?:[•◦‣⁃▪▫●○][ \t]*|[‐‑‒–—−][ \t]+)"
)


@dataclass(frozen=True)
class Principle:
    function: str
    identifier: str
    topic: str
    description: str


@dataclass(frozen=True)
class Control:
    guideline: str
    section: str
    topic: str
    identifier: str
    revision: str
    updated: str
    description: str
    groups: tuple[str, ...]


@dataclass(frozen=True)
class OutlineItem:
    level: int
    title: str
    page_index: int


@dataclass(frozen=True)
class PdfBlock:
    page_index: int
    rect: fitz.Rect
    text: str


def clean_text(value: object) -> str:
    """Return source text with list markers converted to Markdown list markers."""
    if value is None:
        return ""
    text = str(value).strip()
    return EXCEL_LIST_MARKER_PATTERN.sub(r"\1- ", text)


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def read_sheet_rows(workbook_path: Path, sheet_name: str) -> list[dict[str, str]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet_name]
        values = worksheet.iter_rows(values_only=True)
        raw_headers = [clean_text(value) for value in next(values)]
        # ASD's Controls template intentionally retains an empty trailing column.
        # Ignore blank headers, while still rejecting duplicate named columns.
        headers = [header for header in raw_headers if header]
        if len(headers) != len(set(headers)):
            raise ValueError(f"{sheet_name!r} contains duplicate header values.")
        rows = []
        header_columns = [index for index, header in enumerate(raw_headers) if header]
        for row in values:
            record = {
                raw_headers[index]: clean_text(row[index] if index < len(row) else None)
                for index in header_columns
            }
            if any(record.values()):
                rows.append(record)
        return rows
    finally:
        workbook.close()


def find_source_sheets(workbook_path: Path) -> tuple[str, str]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        principles = next(
            (name for name in workbook.sheetnames if name.casefold().startswith("principles")),
            None,
        )
        controls = next(
            (name for name in workbook.sheetnames if name.casefold().startswith("controls")),
            None,
        )
    finally:
        workbook.close()

    if not principles or not controls:
        raise ValueError(
            "The source workbook must contain sheets starting with 'Principles' and 'Controls'."
        )
    return principles, controls


def load_principles(workbook_path: Path) -> list[Principle]:
    sheet_name, _ = find_source_sheets(workbook_path)
    rows = read_sheet_rows(workbook_path, sheet_name)
    required = {"Function", "Identifier", "Topic", "Description"}
    missing = required.difference(rows[0] if rows else set())
    if missing:
        raise ValueError(f"Principles sheet is missing columns: {', '.join(sorted(missing))}.")

    principles = [
        Principle(
            function=row["Function"],
            identifier=row["Identifier"],
            topic=row["Topic"],
            description=row["Description"],
        )
        for row in rows
    ]
    identifiers = [principle.identifier for principle in principles]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("The Principles sheet contains duplicate Identifier values.")
    return principles


def load_controls(workbook_path: Path) -> list[Control]:
    _, sheet_name = find_source_sheets(workbook_path)
    rows = read_sheet_rows(workbook_path, sheet_name)
    required = {
        "Guideline",
        "Section",
        "Topic",
        "Identifier",
        "Revision",
        "Updated",
        "Description",
        *CLASSIFICATION_GROUPS,
        *MATURITY_GROUPS,
    }
    missing = required.difference(rows[0] if rows else set())
    if missing:
        raise ValueError(f"Controls sheet is missing columns: {', '.join(sorted(missing))}.")

    controls = []
    for row in rows:
        applicable_groups = [
            group
            for group in (*CLASSIFICATION_GROUPS, *MATURITY_GROUPS)
            if row[group].casefold() == "yes"
        ]
        controls.append(
            Control(
                guideline=row["Guideline"],
                section=row["Section"],
                topic=row["Topic"],
                identifier=row["Identifier"],
                revision=row["Revision"],
                updated=row["Updated"],
                description=row["Description"],
                groups=tuple(("CONTROL", *applicable_groups)),
            )
        )

    identifiers = [control.identifier for control in controls]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("The Controls sheet contains duplicate Identifier values.")
    return controls


def page_text(document: fitz.Document, page_index: int) -> str:
    text = document.load_page(page_index).get_text("text")
    text = re.sub(r"(?m)^Information security manual \| September \d{4}\s*$", "", text)
    text = re.sub(r"(?m)^\d+\s*$", "", text)
    return text


def detect_source_pages(document: fitz.Document) -> tuple[int, int, int]:
    """Detect relevant chapters by their headings and control marker, never fixed pages."""
    pages = [page_text(document, index) for index in range(document.page_count)]
    principle_page = next(
        (
            index
            for index, text in enumerate(pages)
            if re.search(r"(?im)^Cyber security principles\s*$", text)
            and "The cyber security principles" in text
        ),
        None,
    )
    if principle_page is None:
        raise ValueError("Unable to find the 'Cyber security principles' chapter in the PDF.")

    control_pages = [
        index
        for index in range(principle_page + 1, len(pages))
        if "Control:" in pages[index]
    ]
    if not control_pages:
        raise ValueError("Unable to find PDF pages containing the 'Control:' marker.")
    return principle_page, min(control_pages), max(control_pages)


def outline_items(document: fitz.Document) -> list[OutlineItem]:
    return [
        OutlineItem(level=level, title=title.strip(), page_index=page - 1)
        for level, title, page in document.get_toc(simple=True)
        if title.strip()
    ]


def build_topic_outline_index(
    items: list[OutlineItem], control_start: int, control_end: int
) -> dict[tuple[str, str, str], int]:
    """Index level-three PDF headings by their guideline, section and topic."""
    index: dict[tuple[str, str, str], int] = {}
    guideline = ""
    section = ""
    for position, item in enumerate(items):
        if item.page_index < control_start or item.page_index > control_end:
            continue
        if item.level == 1 and item.title.startswith("Guidelines for "):
            guideline = item.title
            section = ""
        elif item.level == 2 and guideline:
            section = item.title
        elif item.level == 3 and guideline and section:
            key = (normalize_key(guideline), normalize_key(section), normalize_key(item.title))
            index.setdefault(key, position)
    return index


def build_section_context_outline_index(
    items: list[OutlineItem], control_start: int, control_end: int
) -> dict[tuple[str, str], int]:
    """Index a section's optional level-three Context heading in the PDF outline."""
    index: dict[tuple[str, str], int] = {}
    guideline = ""
    section = ""
    for position, item in enumerate(items):
        if item.page_index < control_start or item.page_index > control_end:
            continue
        if item.level == 1 and item.title.startswith("Guidelines for "):
            guideline = item.title
            section = ""
        elif item.level == 2 and guideline:
            section = item.title
        elif item.level == 3 and guideline and section and normalize_key(item.title) == "context":
            index.setdefault((normalize_key(guideline), normalize_key(section)), position)
    return index


def heading_offset(text: str, title: str, minimum: int = 0) -> int | None:
    """Find a heading on a page, preferring a standalone line over inline references."""
    # PDF text extraction often wraps a long heading between words. Matching its
    # whitespace flexibly preserves the heading while avoiding fixed page layouts.
    flexible_title = re.escape(title).replace(r"\ ", r"\s+")
    standalone = re.compile(rf"(?im)^\s*{flexible_title}\s*$")
    match = standalone.search(text, minimum)
    if match:
        return match.start()
    position = text.casefold().find(title.casefold(), minimum)
    return position if position >= 0 else None


def normalized_block_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def page_blocks(document: fitz.Document, page_index: int) -> list[PdfBlock]:
    """Return ordered text blocks, excluding the recurring page header and footer."""
    blocks = []
    for block in sorted(document.load_page(page_index).get_text("blocks"), key=lambda item: (item[1], item[0])):
        text = clean_text(block[4])
        normalized = normalized_block_text(text)
        if not normalized:
            continue
        if re.fullmatch(r"Information security manual \| September \d{4}\s+\d+", normalized):
            continue
        blocks.append(PdfBlock(page_index=page_index, rect=fitz.Rect(block[:4]), text=text))
    return blocks


def heading_block_index(blocks: list[PdfBlock], title: str, minimum: int = 0) -> int | None:
    """Locate a PDF outline heading even when its words are wrapped across lines."""
    expected = normalized_block_text(title).casefold()
    for index, block in enumerate(blocks[minimum:], start=minimum):
        actual = normalized_block_text(block.text).casefold()
        if actual == expected:
            return index
    for index, block in enumerate(blocks[minimum:], start=minimum):
        if expected in normalized_block_text(block.text).casefold():
            return index
    return None


def blocks_between_outline_items(
    document: fitz.Document,
    items: list[OutlineItem],
    start_position: int,
    end_position: int | None = None,
) -> list[PdfBlock]:
    """Return paragraph blocks between an outline heading and the next heading."""
    start = items[start_position]
    if end_position is None:
        end_position = start_position + 1
    next_item = items[end_position] if end_position < len(items) else None
    last_page_index = next_item.page_index if next_item else document.page_count - 1
    result: list[PdfBlock] = []

    for page_index in range(start.page_index, last_page_index + 1):
        blocks = page_blocks(document, page_index)
        first_block = 0
        last_block = len(blocks)
        if page_index == start.page_index:
            start_block = heading_block_index(blocks, start.title)
            if start_block is None:
                return []
            first_block = start_block + 1
        if next_item and page_index == next_item.page_index:
            next_block = heading_block_index(
                blocks,
                next_item.title,
                first_block if page_index == start.page_index else 0,
            )
            if next_block is None:
                return []
            last_block = next_block
        result.extend(blocks[first_block:last_block])
    return result


def normalize_paragraph(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"(?m)^\s*\s*", "", text)
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def external_link_rectangles(page: fitz.Page) -> list[tuple[fitz.Rect, str]]:
    """Return only valid HTTP(S) links, not internal PDF navigation links."""
    links = []
    for link in page.get_links():
        uri = clean_text(link.get("uri"))
        parsed = urlparse(uri)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            links.append((fitz.Rect(link["from"]), uri))
    return links


def markdownify_linked_block(document: fitz.Document, block: PdfBlock) -> str:
    """Convert external linked words in a PDF block to Markdown hyperlinks."""
    page = document.load_page(block.page_index)
    is_bullet = bool(re.match(r"^\s*[•\uf0b7]\s*", block.text))
    links = external_link_rectangles(page)
    if not links:
        text = normalize_paragraph(block.text)
        text = re.sub(r"^[•\uf0b7]\s*", "", text)
        return f"- {text}" if is_bullet else text

    words = []
    for word in page.get_text("words"):
        word_rect = fitz.Rect(word[:4])
        if not word_rect.intersects(block.rect):
            continue
        uri = next(
            (target for link_rect, target in links if word_rect.intersects(link_rect)),
            "",
        )
        word_text = re.sub(r"^[•\uf0b7]\s*", "", word[4])
        if word_text:
            words.append((word_text, uri))
    if not words:
        text = normalize_paragraph(block.text)
        text = re.sub(r"^[•\uf0b7]\s*", "", text)
        return f"- {text}" if is_bullet else text

    groups: list[tuple[list[str], str]] = []
    for word, uri in words:
        if groups and groups[-1][1] == uri:
            groups[-1][0].append(word)
        else:
            groups.append(([word], uri))

    fragments = []
    for tokens, uri in groups:
        text = re.sub(r"(?<=\w)- (?=\w)", "-", " ".join(tokens))
        fragments.append(f"[{text}]({uri})" if uri else text)
    text = " ".join(fragments)
    return f"- {text}" if is_bullet else text


def is_wrapped_continuation(
    block: PdfBlock,
    previous_block: PdfBlock | None,
    previous_is_list_item: bool,
) -> bool:
    """Join text blocks split by PDF layout within a sentence or list item."""
    if previous_block is None:
        return False
    previous_text = normalize_paragraph(previous_block.text)
    if not previous_text or previous_text.endswith((".", "!", "?", ":")):
        return False
    if block.page_index == previous_block.page_index:
        vertical_gap = block.rect.y0 - previous_block.rect.y1
        if previous_is_list_item:
            return 0 <= vertical_gap <= 12 and block.rect.x0 >= previous_block.rect.x0 + 8
        return 0 <= vertical_gap <= 8 and abs(block.rect.x0 - previous_block.rect.x0) <= 3
    return (
        block.page_index == previous_block.page_index + 1
        and previous_block.rect.y1 >= 700
        and block.rect.y0 <= 120
    )


def join_markdown_blocks(document: fitz.Document, blocks: Iterable[PdfBlock]) -> str:
    """Format PDF paragraphs, compact lists, and wrapped bullet continuations."""
    result = ""
    previous_is_list_item = False
    previous_block: PdfBlock | None = None
    for pdf_block in blocks:
        block = markdownify_linked_block(document, pdf_block)
        if not block:
            continue
        is_list_item = block.startswith("- ")
        if not is_list_item and is_wrapped_continuation(
            pdf_block, previous_block, previous_is_list_item
        ):
            result += f" {block}"
            previous_block = pdf_block
            continue
        if result:
            separator = "\n" if previous_is_list_item and is_list_item else "\n\n"
            result += separator
        result += block
        previous_is_list_item = is_list_item
        previous_block = pdf_block
    return result


def extract_topic_descriptions(
    document: fitz.Document, controls: Iterable[Control]
) -> tuple[dict[tuple[str, str, str], str], list[str]]:
    """Extract topic introductions before the first Control marker from the PDF outline."""
    _, control_start, control_end = detect_source_pages(document)
    items = outline_items(document)
    topic_positions = build_topic_outline_index(items, control_start, control_end)
    descriptions: dict[tuple[str, str, str], str] = {}
    missing: list[str] = []

    seen_keys: set[tuple[str, str, str]] = set()
    for control in controls:
        key = (
            normalize_key(control.guideline),
            normalize_key(control.section),
            normalize_key(control.topic),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        outline_position = topic_positions.get(key)
        if outline_position is None:
            missing.append(" | ".join((control.guideline, control.section, control.topic)))
            continue
        blocks = blocks_between_outline_items(document, items, outline_position)
        introduction_blocks: list[PdfBlock] = []
        for block in blocks:
            if "Control:" in block.text:
                break
            if normalize_paragraph(block.text):
                introduction_blocks.append(block)
        introduction = join_markdown_blocks(document, introduction_blocks)
        if introduction:
            descriptions[key] = introduction
        else:
            missing.append(" | ".join((control.guideline, control.section, control.topic)))
    return descriptions, missing


def extract_section_contexts(
    document: fitz.Document, controls: Iterable[Control]
) -> dict[tuple[str, str], str]:
    """Extract optional Context text and format it as the parent section description."""
    _, control_start, control_end = detect_source_pages(document)
    items = outline_items(document)
    context_positions = build_section_context_outline_index(items, control_start, control_end)
    source_sections = {
        (normalize_key(control.guideline), normalize_key(control.section)) for control in controls
    }
    contexts: dict[tuple[str, str], str] = {}
    for key, outline_position in context_positions.items():
        if key not in source_sections:
            continue
        # The PDF table of contents has one known pattern where a Context paragraph
        # is incorrectly represented as a level-three outline title. Continue until
        # the next conventional section or topic title in that situation.
        context_end = outline_position + 1
        while context_end < len(items) and items[context_end].title.rstrip().endswith("."):
            context_end += 1
        paragraphs = [
            block
            for block in blocks_between_outline_items(
                document,
                items,
                outline_position,
                context_end,
            )
            if normalize_paragraph(block.text)
        ]
        if paragraphs:
            contexts[key] = join_markdown_blocks(document, paragraphs)
    return contexts


def validate_pdf_control_coverage(document: fitz.Document, controls: Iterable[Control]) -> tuple[set[str], set[str]]:
    """Compare the annex control IDs against the dynamically detected PDF control pages."""
    _, control_start, control_end = detect_source_pages(document)
    text = "\n".join(
        page_text(document, page_index)
        for page_index in range(control_start, control_end + 1)
    )
    pdf_identifiers = set(re.findall(r"Control:\s*(ISM[-‐‑–—]\d{4})", text))
    pdf_identifiers = {
        re.sub(r"[‐‑–—]", "-", identifier) for identifier in pdf_identifiers
    }
    excel_identifiers = {control.identifier for control in controls}
    return excel_identifiers.difference(pdf_identifiers), pdf_identifiers.difference(excel_identifiers)


def content_row(
    *,
    assessable: bool,
    depth: int,
    ref_id: str = "",
    name: str = "",
    description: str = "",
    annotation: str = "",
    groups: Iterable[str] = (),
) -> dict[str, str | int]:
    row: dict[str, str | int] = {header: "" for header in CONTENT_HEADERS}
    row.update(
        {
            "assessable": "x" if assessable else "",
            "depth": depth,
            "ref_id": ref_id,
            "name": name,
            "description": description,
            "annotation": annotation,
            "implementation_groups": ",".join(groups),
        }
    )
    return row


def build_content_rows(
    principles: list[Principle],
    controls: list[Control],
    topic_descriptions: dict[tuple[str, str, str], str],
    section_contexts: dict[tuple[str, str], str],
) -> list[dict[str, str | int]]:
    rows = [
        content_row(
            assessable=False,
            depth=1,
            name="Cyber Security Principles",
            description=PRINCIPLES_DESCRIPTION,
        )
    ]

    current_function = ""
    for principle in principles:
        if principle.function != current_function:
            current_function = principle.function
            prefix = principle.identifier.split("-", maxsplit=1)[0]
            rows.append(
                content_row(
                    assessable=False,
                    depth=2,
                    ref_id=prefix,
                    name=principle.function.capitalize(),
                )
            )
        rows.append(
            content_row(
                assessable=True,
                depth=3,
                ref_id=principle.identifier,
                name=principle.topic,
                description=principle.description,
                groups=("PRINCIPLE",),
            )
        )

    rows.append(
        content_row(
            assessable=False,
            depth=1,
            name="Cyber Security Guidelines",
            description=CONTROLS_DESCRIPTION,
        )
    )

    current_guideline = ""
    current_section = ""
    current_topic = ""
    for control in controls:
        if control.guideline != current_guideline:
            current_guideline = control.guideline
            current_section = ""
            current_topic = ""
            rows.append(
                content_row(
                    assessable=False,
                    depth=2,
                    name=control.guideline,
                )
            )
        if control.section != current_section:
            current_section = control.section
            current_topic = ""
            section_key = (normalize_key(control.guideline), normalize_key(control.section))
            rows.append(
                content_row(
                    assessable=False,
                    depth=3,
                    name=control.section,
                    description=section_contexts.get(section_key, ""),
                )
            )
        if control.topic != current_topic:
            current_topic = control.topic
            topic_key = (
                normalize_key(control.guideline),
                normalize_key(control.section),
                normalize_key(control.topic),
            )
            rows.append(
                content_row(
                    assessable=False,
                    depth=4,
                    name=control.topic,
                    description=topic_descriptions.get(topic_key, ""),
                )
            )
        rows.append(
            content_row(
                assessable=True,
                depth=5,
                ref_id=control.identifier,
                description=control.description,
                annotation=f"Revision : {control.revision} | Updated: {control.updated}",
                groups=control.groups,
            )
        )
    return rows


def write_key_value_sheet(worksheet, values: Iterable[tuple[str, str]]) -> None:
    for row_number, (key, value) in enumerate(values, start=1):
        worksheet.cell(row=row_number, column=1, value=key)
        worksheet.cell(row=row_number, column=2, value=value)


def write_content_sheet(worksheet, rows: list[dict[str, str | int]]) -> None:
    worksheet.append(CONTENT_HEADERS)
    for row in rows:
        worksheet.append([row[header] for header in CONTENT_HEADERS])


def format_sheet(worksheet, widths: dict[int, float]) -> None:
    header_fill = PatternFill("solid", fgColor="17365D")
    header_font = Font(color="FFFFFF", bold=True)
    if worksheet.max_row:
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
    worksheet.sheet_view.showGridLines = True
    for column_index, width in widths.items():
        worksheet.column_dimensions[get_column_letter(column_index)].width = width
    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def format_metadata_sheet(worksheet, widths: dict[int, float]) -> None:
    """Format a two-column metadata sheet without treating its first value as a header."""
    for column_index, width in widths.items():
        worksheet.column_dimensions[get_column_letter(column_index)].width = width
    worksheet.sheet_view.showGridLines = True
    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def build_workbook(
    output_path: Path,
    principles: list[Principle],
    controls: list[Control],
    topic_descriptions: dict[tuple[str, str, str], str],
    section_contexts: dict[tuple[str, str], str],
) -> None:
    workbook = Workbook()
    library = workbook.active
    library.title = "library_meta"
    framework_meta = workbook.create_sheet("ism_meta")
    framework_content = workbook.create_sheet("ism_content")
    groups_meta = workbook.create_sheet("imp_grp_meta")
    groups_content = workbook.create_sheet("imp_grp_content")

    library_urn = f"urn:intuitem:risk:library:{LIBRARY_SUFFIX}"
    framework_urn = f"urn:intuitem:risk:framework:{LIBRARY_SUFFIX}"
    base_urn = f"urn:intuitem:risk:req_node:{LIBRARY_SUFFIX}"
    write_key_value_sheet(
        library,
        [
            ("type", "library"),
            ("urn", library_urn),
            ("version", "1"),
            ("locale", "en"),
            ("ref_id", FRAMEWORK_REF_ID),
            ("name", FRAMEWORK_NAME),
            ("description", LIBRARY_DESCRIPTION),
            ("copyright", COPYRIGHT),
            ("provider", "Australian Signals Directorate (ASD)"),
            ("packager", "intuitem"),
        ],
    )
    write_key_value_sheet(
        framework_meta,
        [
            ("type", "framework"),
            ("urn", framework_urn),
            ("base_urn", base_urn),
            ("ref_id", FRAMEWORK_REF_ID),
            ("name", FRAMEWORK_NAME),
            ("description", LIBRARY_DESCRIPTION),
            ("implementation_groups_definition", "imp_grp"),
        ],
    )
    write_key_value_sheet(
        groups_meta,
        [("type", "implementation_groups"), ("name", "imp_grp")],
    )
    groups_content.append(["ref_id", "name", "description"])
    for ref_id, name, description in IMPLEMENTATION_GROUPS:
        groups_content.append([ref_id, name, description])

    content_rows = build_content_rows(
        principles,
        controls,
        topic_descriptions,
        section_contexts,
    )
    write_content_sheet(framework_content, content_rows)

    format_metadata_sheet(library, {1: 34, 2: 110})
    format_metadata_sheet(framework_meta, {1: 34, 2: 110})
    format_sheet(
        framework_content,
        {
            1: 12,
            2: 8,
            3: 18,
            4: 16,
            5: 95,
            6: 32,
            7: 36,
        },
    )
    format_metadata_sheet(groups_meta, {1: 34, 2: 40})
    format_sheet(groups_content, {1: 16, 2: 68, 3: 95})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def build_report(
    principles: list[Principle],
    controls: list[Control],
    missing_topics: list[str],
    section_contexts: dict[tuple[str, str], str],
    missing_pdf_ids: set[str],
    extra_pdf_ids: set[str],
) -> str:
    classification_counts = Counter(
        group for control in controls for group in control.groups if group in CLASSIFICATION_GROUPS
    )
    maturity_counts = Counter(
        group for control in controls for group in control.groups if group in MATURITY_GROUPS
    )
    lines = [
        f"Principles: {len(principles)}",
        f"Controls: {len(controls)}",
        f"Topic descriptions extracted: {len({(c.guideline, c.section, c.topic) for c in controls}) - len(missing_topics)}",
        f"Topics without PDF descriptions: {len(missing_topics)}",
        f"Section contexts extracted: {len(section_contexts)}",
        f"Control identifiers missing from PDF: {len(missing_pdf_ids)}",
        f"Extra control identifiers in PDF: {len(extra_pdf_ids)}",
        "Classification memberships: " + ", ".join(f"{group}={classification_counts[group]}" for group in CLASSIFICATION_GROUPS),
        "Essential Eight memberships: " + ", ".join(f"{group}={maturity_counts[group]}" for group in MATURITY_GROUPS),
    ]
    if missing_topics:
        lines.append("Topics without PDF descriptions:")
        lines.extend(f"- {topic}" for topic in missing_topics)
    if missing_pdf_ids:
        lines.append("Control IDs missing from PDF: " + ", ".join(sorted(missing_pdf_ids)))
    if extra_pdf_ids:
        lines.append("Extra control IDs in PDF: " + ", ".join(sorted(extra_pdf_ids)))
    return "\n".join(lines) + "\n"


def parse_arguments() -> argparse.Namespace:
    default_output = Path(__file__).resolve().with_name("asd-ism_09-26.xlsx")
    parser = argparse.ArgumentParser(
        description="Build a CISO Assistant ASD ISM library workbook from a PDF and annex Excel file."
    )
    parser.add_argument("pdf", type=Path, help="Source Information Security Manual PDF.")
    parser.add_argument("excel", type=Path, help="Source System security plan annex Excel file.")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=default_output,
        help=f"Output CISO Assistant library workbook (.xlsx). Default: {default_output.name}",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional plain-text validation report path.",
    )
    parser.add_argument(
        "--allow-missing-topic-descriptions",
        action="store_true",
        help="Create the workbook while reporting, rather than failing, if a topic description is not extracted.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.pdf.suffix.casefold() != ".pdf":
        raise ValueError("The first source argument must be a PDF file.")
    if arguments.excel.suffix.casefold() != ".xlsx":
        raise ValueError("The second source argument must be an XLSX file.")
    if arguments.output.suffix.casefold() != ".xlsx":
        raise ValueError("The output path must end in .xlsx.")
    if not arguments.pdf.is_file():
        raise FileNotFoundError(arguments.pdf)
    if not arguments.excel.is_file():
        raise FileNotFoundError(arguments.excel)

    principles = load_principles(arguments.excel)
    controls = load_controls(arguments.excel)
    document = fitz.open(arguments.pdf)
    try:
        topic_descriptions, missing_topics = extract_topic_descriptions(document, controls)
        section_contexts = extract_section_contexts(document, controls)
        missing_pdf_ids, extra_pdf_ids = validate_pdf_control_coverage(document, controls)
    finally:
        document.close()

    report = build_report(
        principles,
        controls,
        missing_topics,
        section_contexts,
        missing_pdf_ids,
        extra_pdf_ids,
    )
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(report, encoding="utf-8")
    print(report, end="")

    if missing_pdf_ids or extra_pdf_ids:
        raise ValueError("PDF and Excel control identifiers do not match. See the validation report.")
    if missing_topics and not arguments.allow_missing_topic_descriptions:
        raise ValueError("Some topic descriptions were not extracted. See the validation report.")

    build_workbook(
        arguments.output,
        principles,
        controls,
        topic_descriptions,
        section_contexts,
    )
    print(f"Created: {arguments.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
