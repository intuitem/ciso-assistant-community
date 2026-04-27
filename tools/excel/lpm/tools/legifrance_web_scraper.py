#!/usr/bin/env python3
"""Scrape a Legifrance annex and export it to a single-sheet Excel file."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from playwright.sync_api import sync_playwright


DEFAULT_SOURCE_URL = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000033063127"
DEFAULT_OUTPUT_PATH = "legifrance_annexe.xlsx"
DEFAULT_SHEET_NAME = "oiv_content"
DEFAULT_TIMEOUT_SECONDS = 45
RULE_DEPTH = 1
PARAGRAPH_DEPTH_OFFSET = 1
LIST_DEPTH_OFFSET = 2

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

HEADER_ROW = ("assessable", "depth", "ref_id", "name", "description")
RULE_TITLE_RE = re.compile(r"^(?P<ref_id>\d+)\.\s+(?P<name>.+)$")
ANNEX_HEADING_RE = re.compile(r"^annexe\b", re.IGNORECASE)
START_LINE_RE = re.compile(r"^1\.\s+")
STOP_LINE_RE = re.compile(r"^(liens relatifs|fait le\b)", re.IGNORECASE)


@dataclass
class ContentRow:
    assessable: str | None
    depth: int
    ref_id: int | None
    name: str | None
    description: str | None

    def as_excel_row(self) -> tuple[str | None, int, int | None, str | None, str | None]:
        return (
            self.assessable,
            self.depth,
            self.ref_id,
            self.name,
            self.description,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the Annex section from a Legifrance page and export it "
            "to an Excel file with a single sheet named 'oiv_content'."
        )
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SOURCE_URL,
        help="Legifrance URL to scrape.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help="Output Excel file path.",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    # Normalize whitespace so the exported Excel text stays stable.
    normalized = re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()
    return re.sub(r"\s+([,.)])", r"\1", normalized)


def is_protection_page(html: str) -> bool:
    # Detect a Cloudflare protection page instead of the expected legal text.
    lowered = html.lower()
    return (
        "just a moment" in lowered
        or "enable javascript and cookies to continue" in lowered
        or "__cf_chl_" in lowered
    )


def fetch_html_with_requests(url: str, timeout_seconds: float) -> str:
    # Fetch the page with plain HTTP when Legifrance allows it.
    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response.text


def fetch_html_with_playwright(url: str, timeout_seconds: float) -> str:
    # Fetch the rendered DOM in a browser to bypass protected pages.
    timeout_ms = int(timeout_seconds * 1000)

    with sync_playwright() as playwright:
        launch_kwargs: dict[str, object] = {"headless": True}
        firefox_path = Path(playwright.firefox.executable_path)
        if firefox_path.exists():
            launch_kwargs["executable_path"] = str(firefox_path)

        try:
            browser = playwright.firefox.launch(**launch_kwargs)
        except Exception as exc:
            raise RuntimeError(
                "Failed to launch Firefox with Playwright. "
                "Make sure the Playwright browsers are installed "
                "(for example with 'playwright install firefox')."
            ) from exc

        try:
            page = browser.new_page(locale="fr-FR")
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            page.wait_for_timeout(1000)
            return page.content()
        finally:
            browser.close()


def split_paragraph_lines(paragraph: Tag) -> list[str]:
    # Split one paragraph into logical lines by treating each <br> as a newline.
    working_soup = BeautifulSoup(str(paragraph), "html.parser")
    working_paragraph = working_soup.find("p")
    if working_paragraph is None:
        return []

    for br in working_paragraph.find_all("br"):
        br.replace_with("\n")

    text = working_paragraph.get_text(" ", strip=False)
    return [line for raw_line in text.splitlines() if (line := normalize_text(raw_line))]


def is_annex_heading(tag: Tag) -> bool:
    # Identify an HTML heading that matches the Annex section.
    return tag.name in {"h2", "h3", "h4"} and bool(
        ANNEX_HEADING_RE.match(normalize_text(tag.get_text(" ", strip=True)))
    )


def contains_annex_start(candidate: Tag) -> bool:
    # Check whether a candidate block contains the numbered Annex start.
    for paragraph in candidate.find_all("p"):
        for line in split_paragraph_lines(paragraph):
            if START_LINE_RE.match(line):
                return True
    return False


def iter_annex_candidates(sibling: Tag) -> list[Tag]:
    # Return plausible blocks near the Annex heading without hardcoding one selector.
    candidates: list[Tag] = []

    # Legifrance sometimes changes container depth, so we probe a few nearby levels.
    for selector in (
        "article.summary-preface div.content",
        "article div.content",
        "div.content",
    ):
        candidate = sibling.select_one(selector)
        if candidate is not None:
            candidates.append(candidate)

    candidates.append(sibling)

    unique_candidates: list[Tag] = []
    seen_ids: set[int] = set()
    for candidate in candidates:
        candidate_id = id(candidate)
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        unique_candidates.append(candidate)

    return unique_candidates


def find_annex_container(soup: BeautifulSoup) -> Tag | None:
    # Find the HTML container that actually holds the Annex content.
    for heading in soup.find_all(is_annex_heading):
        for sibling in heading.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            for candidate in iter_annex_candidates(sibling):
                if contains_annex_start(candidate):
                    return candidate
    return None


def iter_annex_paragraphs(annex_container: Tag) -> list[Tag]:
    # Keep every paragraph from the Annex content, including the last one:
    # on Legifrance, final compliance lines are sometimes stored in the last <p>.
    return annex_container.find_all("p")


def extract_annex_lines_from_html(html: str) -> list[str]:
    # Extract useful Annex lines starting from the first numbered rule "1.".
    soup = BeautifulSoup(html, "html.parser")
    annex_container = find_annex_container(soup)
    if annex_container is None:
        raise ValueError("Could not find the Annex section in the page.")

    lines: list[str] = []
    started = False

    for paragraph in iter_annex_paragraphs(annex_container):
        for line in split_paragraph_lines(paragraph):
            if STOP_LINE_RE.match(line):
                return lines

            if not started:
                if not START_LINE_RE.match(line):
                    continue
                started = True

            lines.append(line)

    if not lines:
        raise ValueError(
            "The Annex section was found, but no content starting from '1.' "
            "could be extracted."
        )

    return lines


def collect_annex_lines(url: str, timeout_seconds: float) -> tuple[list[str], str]:
    # Try 'requests' first, then fall back to Playwright when access is blocked.
    request_errors: list[str] = []

    try:
        # Keep 'requests' as the main path to avoid using a browser when unnecessary.
        html = fetch_html_with_requests(url, timeout_seconds)
        if is_protection_page(html):
            request_errors.append("the raw HTTP page is protected by Cloudflare")
        else:
            try:
                return extract_annex_lines_from_html(html), "requests"
            except ValueError as exc:
                request_errors.append(str(exc))
    except requests.RequestException as exc:
        request_errors.append(str(exc))

    try:
        html = fetch_html_with_playwright(url, timeout_seconds)
        return extract_annex_lines_from_html(html), "playwright"
    except Exception as exc:
        request_errors.append(str(exc))

    raise RuntimeError(
        "Legifrance extraction failed. Details: " + " | ".join(request_errors)
    )


def relative_depth(root_depth: int, offset: int) -> int:
    # Compute a depth from the current rule root node.
    return root_depth + offset


def resolve_bullet_depth(rule_depth: int, parent_stack: list[int]) -> int:
    # Compute one bullet depth relative to the current rule and parent bullet stack.
    if parent_stack:
        return parent_stack[-1] + 1
    return relative_depth(rule_depth, LIST_DEPTH_OFFSET)


def is_assessable_parent_bullet(line: str) -> bool:
    # Treat some parent bullets as assessable when they already contain a full sentence.
    trimmed_line = line.strip()
    if not (trimmed_line.startswith("-") and trimmed_line.endswith(":")):
        return False

    # Ignore the trailing ":" and look for at least one sentence ending with ".".
    content = trimmed_line[:-1].strip()
    return "." in content


def build_content_rows(lines: list[str]) -> list[ContentRow]:
    # Convert raw Annex lines into tabular rows for Excel export.
    rows: list[ContentRow] = []
    current_rule_depth = RULE_DEPTH
    parent_bullet_depths: list[int] = []

    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else None
        rule_match = RULE_TITLE_RE.match(line)
        if rule_match:
            rows.append(
                ContentRow(
                    assessable=None,
                    depth=current_rule_depth,
                    ref_id=int(rule_match.group("ref_id")),
                    name=rule_match.group("name"),
                    description=None,
                )
            )
            parent_bullet_depths.clear()
            continue

        if line.startswith("-"):
            is_parent_bullet = line.endswith(":")
            bullet_depth = resolve_bullet_depth(current_rule_depth, parent_bullet_depths)
            assessable = "x" if (not is_parent_bullet or is_assessable_parent_bullet(line)) else None
            rows.append(
                ContentRow(
                    assessable=assessable,
                    depth=bullet_depth,
                    ref_id=None,
                    name=None,
                    description=line,
                )
            )
            if is_parent_bullet:
                # The stack keeps hierarchy relative to the current level-1 rule.
                parent_bullet_depths.append(bullet_depth)
            elif parent_bullet_depths:
                keep_current_branch = bool(
                    next_line is not None
                    and next_line.startswith("-")
                    and not next_line.endswith(":")
                )
                if not keep_current_branch:
                    parent_bullet_depths.pop()
            continue

        rows.append(
            ContentRow(
                assessable="x",
                depth=relative_depth(current_rule_depth, PARAGRAPH_DEPTH_OFFSET),
                ref_id=None,
                name=None,
                description=line,
            )
        )
        parent_bullet_depths.clear()

    return rows


def write_workbook(rows: list[ContentRow], output_path: Path) -> None:
    # Build the output Excel file with a single 'oiv_content' sheet.
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = DEFAULT_SHEET_NAME
    worksheet.append(HEADER_ROW)

    for row in rows:
        worksheet.append(row.as_excel_row())

    worksheet.freeze_panes = "A2"

    header_font = Font(bold=True)
    wrapped_alignment = Alignment(vertical="top", wrap_text=True)

    for cell in worksheet[1]:
        cell.font = header_font
        cell.alignment = wrapped_alignment

    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrapped_alignment

    column_widths = {
        "A": 12,
        "B": 8,
        "C": 10,
        "D": 55,
        "E": 140,
    }
    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def main(url: str = DEFAULT_SOURCE_URL, output_path: str | Path = DEFAULT_OUTPUT_PATH) -> None:
    # Run the full extraction and Excel export workflow.
    resolved_output_path = Path(output_path).expanduser()

    print(f"⌛ Extracting web content from \"{url}\"...")
    annex_lines, extraction_mode = collect_annex_lines(url, DEFAULT_TIMEOUT_SECONDS)
    print(f"✅ Web extraction completed with {extraction_mode}. Collected {len(annex_lines)} raw lines.")

    content_rows = build_content_rows(annex_lines)
    
    print(f"⌛ Building Excel workbook at \"{resolved_output_path}\" with {len(content_rows)} content rows...")
    write_workbook(content_rows, resolved_output_path)

    print(f"✅ Excel build completed: {len(content_rows)} rows written to \"{resolved_output_path}\"")


if __name__ == "__main__":
    # Keep CLI parsing here so `main()` can be reused directly from another script.
    args = parse_args()
    main(args.url, args.output)
