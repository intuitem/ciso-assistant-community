#!/usr/bin/env python3
"""Extract OWASP Top 10 Markdown sources into a normalized JSON document."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit


SOURCE_REPOSITORY = "https://github.com/OWASP/Top10"
PUBLISHED_SITE = "https://top10.owasp.org"
DEFAULT_LOCALE = "en"
EXPECTED_CATEGORY_IDS = [f"A{number:02d}" for number in range(1, 11)]
MIN_CATEGORY_PAGES = len(EXPECTED_CATEGORY_IDS) // 2
CATEGORY_FILE_RE = re.compile(r"^A(0[1-9]|10)_(\d{4}).*\.md$", re.IGNORECASE)
H1_RE = re.compile(r"^#(?!#)\s*(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H2_OR_H3_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)(?:\{[^}]*\})?")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<target>[^)]+)\)")
JINJA_RE = re.compile(r"\{\{.*?\}\}")
LOCALIZED_TEXT = {
    "ar": {
        "source": "المصدر",
        "references": "لمزيد من المعلومات حول المراجع وقائمة CWE المعيّنة:",
    },
    "cs": {
        "source": "Zdroj",
        "references": "Další informace o odkazech a seznamu namapovaných CWE:",
    },
    "de": {
        "source": "Quelle",
        "references": (
            "Weitere Informationen zu den Referenzen und zur Liste der "
            "zugeordneten CWEs:"
        ),
    },
    "en": {
        "source": "Source",
        "references": (
            "For more information about the references and the list of mapped CWEs:"
        ),
    },
    "es": {
        "source": "Fuente",
        "references": (
            "Para obtener más información sobre las referencias y la lista de "
            "CWE asociadas:"
        ),
    },
    "fa": {
        "source": "منبع",
        "references": (
            "برای اطلاعات بیشتر درباره منابع و فهرست CWEهای نگاشت‌شده:"
        ),
    },
    "fr": {
        "source": "Source",
        "references": (
            "Pour plus d’informations sur les références et la liste des CWE "
            "mappées :"
        ),
    },
    "id": {
        "source": "Sumber",
        "references": (
            "Untuk informasi lebih lanjut tentang referensi dan daftar CWE yang "
            "dipetakan:"
        ),
    },
    "it": {
        "source": "Fonte",
        "references": (
            "Per maggiori informazioni sui riferimenti e sull'elenco delle CWE "
            "mappate:"
        ),
    },
    "ja": {
        "source": "出典",
        "references": "参考資料およびマッピングされたCWEの一覧について、詳しくはこちら：",
    },
    "ko": {
        "source": "출처",
        "references": "참고 자료와 매핑된 CWE 목록에 대한 자세한 정보:",
    },
    "pt": {
        "source": "Fonte",
        "references": (
            "Para mais informações sobre as referências e a lista de CWEs mapeadas:"
        ),
    },
    "tr": {
        "source": "Kaynak",
        "references": (
            "Referanslar ve eşlenen CWE listesi hakkında daha fazla bilgi:"
        ),
    },
    "zh": {
        "source": "來源",
        "references": "有關參考資料及已對應 CWE 清單的更多資訊：",
    },
}


@dataclass(frozen=True)
class LogicalSection:
    """A logical H2 section, possibly introduced by consecutive H2 headings."""

    start: int
    content_start: int
    title: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def language_code(locale: str) -> str:
    """Return the two-letter language code used by CISO Assistant."""
    match = re.match(r"^[A-Za-z]{2}", locale)
    if match is None:
        raise ValueError(f"Could not derive a two-letter language code from '{locale}'")
    return match.group(0).lower()


def versioned_ref_id(ref_id: str, year: int) -> str:
    """Append the OWASP release year to a threat reference identifier."""
    return f"{ref_id}:{year}"


def localized_text(locale: str) -> dict[str, str]:
    """Return generated labels for a source locale or output language code."""
    code = language_code(locale)
    if code not in LOCALIZED_TEXT:
        raise ValueError(f"No generated-text translations are defined for '{code}'")
    return LOCALIZED_TEXT[code]


def published_page_url(year: int, locale: str, markdown_filename: str) -> str:
    """Map a repository Markdown path to its published OWASP Top 10 page."""
    page_slug = quote(Path(markdown_filename).stem, safe="-_")
    locale_path = "" if locale == DEFAULT_LOCALE else f"{quote(locale, safe='-')}/"
    return f"{PUBLISHED_SITE}/{year}/{locale_path}{page_slug}/"


def introduction_page_url(year: int, locale: str) -> str:
    """Return the published introduction page for a supported release."""
    introduction_files = {
        2021: "A00_2021_Introduction.md",
        2025: "0x00_2025-Introduction.md",
    }
    filename = introduction_files.get(year, f"0x00_{year}-Introduction.md")
    return published_page_url(year, locale, filename)


def clean_heading_title(raw: str) -> str:
    value = JINJA_RE.sub("", raw)
    value = MARKDOWN_IMAGE_RE.sub("", value)
    value = re.sub(r"\{:[^}]*\}", "", value)
    value = value.replace("**", "").replace("__", "").strip()
    return re.sub(r"\s+", " ", value).strip()


def clean_category_name(raw: str, ref_id: str, year: int) -> str:
    value = clean_heading_title(raw)
    value = re.sub(
        rf"^{re.escape(ref_id)}\s*:?\s*{year}\s*[-–—:]?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return value.strip(" -–—:")


def clean_markdown_block(lines: list[str]) -> str:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[start:end])


def markdown_link_target(raw_target: str) -> str:
    """Extract the destination from an inline Markdown link target."""
    value = raw_target.strip()
    if value.startswith("<"):
        closing = value.find(">")
        if closing > 0:
            return value[1:closing].strip()
    return value.split(maxsplit=1)[0] if value else ""


def is_relative_markdown_target(target: str) -> bool:
    """Return True for repository-local Markdown targets, not URLs or anchors."""
    value = target.strip()
    if not value or value.startswith(("#", "//")):
        return False
    url_candidate = value.lstrip("(")
    return not bool(urlsplit(url_candidate).scheme)


def replace_relative_markdown_links(
    markdown: str,
) -> tuple[str, list[dict[str, str]]]:
    """Replace repository-local Markdown links with bold link labels."""
    replacements: list[dict[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        label = match.group("label").strip()
        target = markdown_link_target(match.group("target"))
        if not is_relative_markdown_target(target):
            return match.group(0)
        replacements.append({"text": label, "path": target})
        if label.startswith("**") and label.endswith("**"):
            return label
        return f"**{label}**"

    return MARKDOWN_LINK_RE.sub(replace, markdown), replacements


def is_image_only(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("<img") and stripped.endswith("/>"):
        return True
    without_image = MARKDOWN_IMAGE_RE.sub("", stripped)
    without_attributes = re.sub(r"\{:[^}]*\}", "", without_image).strip()
    return not without_attributes


def _truncate_repeated_english_block(lines: list[str], year: int) -> list[str]:
    """Remove the appended English duplicate present in some 2021 translations."""
    if year != 2021:
        return lines

    headings_seen = 0
    for index, line in enumerate(lines):
        match = H2_RE.match(line)
        if not match:
            continue
        title = clean_heading_title(match.group(1)).strip(". ").casefold()
        if title == "factors" and headings_seen >= 5:
            return lines[:index]
        headings_seen += 1
    return lines


def logical_sections(lines: list[str], year: int) -> tuple[list[str], list[LogicalSection]]:
    lines = _truncate_repeated_english_block(lines, year)
    raw_headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = H2_RE.match(line)
        if match:
            raw_headings.append((index, clean_heading_title(match.group(1))))

    groups: list[dict[str, Any]] = []
    for index, title in raw_headings:
        if groups:
            previous_heading = int(groups[-1]["last_heading"])
            between = lines[previous_heading + 1 : index]
            if all(not item.strip() for item in between):
                groups[-1]["last_heading"] = index
                groups[-1]["titles"].append(title)
                continue
        groups.append(
            {
                "start": index,
                "last_heading": index,
                "titles": [title],
            }
        )

    sections = [
        LogicalSection(
            start=int(group["start"]),
            content_start=int(group["last_heading"]) + 1,
            title=" / ".join(group["titles"]),
        )
        for group in groups
    ]
    return lines, sections


def classify_section_title(title: str) -> str | None:
    normalized = clean_heading_title(title).strip(". ").casefold()
    aliases = {
        "score_table": ("score table", "factors", "جدول امتیازدهی"),
        "description": ("description", "توضیحات"),
        "prevention": (
            "how to prevent",
            "چگونه جلوگیری کنیم",
            "روش‌های پیشگیری",
            "مدیریت تغییرات و سخت‌سازی سیستم‌ها",
        ),
        "examples": (
            "example attack scenarios",
            "نمونه سناریوهای حمله",
            "مثال سناریوهای حمله",
            "مثال‌های سناریو حمله",
        ),
    }
    for section_key, candidates in aliases.items():
        if any(candidate in normalized for candidate in candidates):
            return section_key
    return None


def parse_category_page(path: Path, year: int, locale: str) -> dict[str, Any]:
    match = CATEGORY_FILE_RE.match(path.name)
    if not match or int(match.group(2)) != year:
        raise ValueError(f"Unexpected category filename: {path.name}")

    ref_id = f"A{match.group(1)}"
    lines = read_text(path).splitlines()
    h1_match = next(
        (match for line in lines if (match := H1_RE.match(line))), None
    )

    source_lines, sections = logical_sections(lines, year)
    if year == 2025 and locale == "fa":
        raw_headings: list[tuple[int, str | None]] = []
        semantic_positions: dict[str, int] = {}
        for line_index, line in enumerate(source_lines):
            heading_match = H2_OR_H3_RE.match(line)
            if not heading_match:
                continue
            section_key = classify_section_title(heading_match.group(1))
            raw_headings.append((line_index, section_key))
            if section_key and section_key not in semantic_positions:
                semantic_positions[section_key] = line_index

        def section_body(section_key: str) -> str | None:
            start_heading = semantic_positions.get(section_key)
            if start_heading is None:
                return None
            start = start_heading + 1
            if section_key == "score_table":
                end = semantic_positions.get("description", len(source_lines))
            elif section_key == "description":
                end = semantic_positions.get("prevention", len(source_lines))
            elif section_key == "prevention":
                end = semantic_positions.get("examples", len(source_lines))
            else:
                end = next(
                    (
                        line_index
                        for line_index, _ in raw_headings
                        if line_index > start_heading
                    ),
                    len(source_lines),
                )
            return clean_markdown_block(source_lines[start:end])

    else:
        indexes: dict[str, int] = {}
        for index, section in enumerate(sections):
            section_key = classify_section_title(section.title)
            if section_key and section_key not in indexes:
                indexes[section_key] = index

        if len(indexes) < 4:
            if year == 2025 and len(sections) >= 5:
                indexes.setdefault("score_table", 1)
                indexes.setdefault("description", 2)
                indexes.setdefault("prevention", 3)
                indexes.setdefault("examples", 4)
            elif year == 2021 and len(sections) >= 6:
                description_index = 1 if len(sections) == 6 else 2
                indexes.setdefault("score_table", 0)
                indexes.setdefault("description", description_index)
                indexes.setdefault("prevention", description_index + 1)
                indexes.setdefault("examples", len(sections) - 3)

        def section_body(section_key: str) -> str | None:
            start_index = indexes.get(section_key)
            if start_index is None or start_index >= len(sections):
                return None
            start = sections[start_index].content_start
            if (
                section_key == "prevention"
                and indexes.get("examples", -1) > start_index
            ):
                end = sections[indexes["examples"]].start
            elif start_index + 1 < len(sections):
                end = sections[start_index + 1].start
            else:
                end = len(source_lines)
            return clean_markdown_block(source_lines[start:end])

    normalized_sections: dict[str, str | None] = {}
    relative_links_removed: list[dict[str, str]] = []
    for section_key in ("score_table", "description", "prevention", "examples"):
        section = section_body(section_key)
        if section is None:
            normalized_sections[section_key] = None
            continue
        normalized, replacements = replace_relative_markdown_links(section)
        normalized_sections[section_key] = normalized
        relative_links_removed.extend(
            {
                "ref_id": ref_id,
                "locale": locale,
                "source_file": path.name,
                "section": section_key,
                **replacement,
            }
            for replacement in replacements
        )

    source_url = published_page_url(year, locale, path.name)
    return {
        "ref_id": ref_id,
        "name": (
            clean_category_name(h1_match.group(1), ref_id, year)
            if h1_match is not None
            else None
        ),
        "sections": normalized_sections,
        "relative_links_removed": relative_links_removed,
        "language": language_code(locale),
        "source_url": source_url,
        "source_file": path.name,
    }


def build_annotation(
    score_table: str,
    prevention: str,
    examples: str,
    source_url: str,
    locale: str,
) -> str:
    separator = "\n\n\n"
    references_label = localized_text(locale)["references"]
    return separator.join(
        [
            f"## Score table\n\n{score_table}",
            f"## How to prevent\n\n{prevention}",
            f"## Example attack scenarios\n\n{examples}",
            f"{references_label} {source_url}",
        ]
    )


def category_with_localized_boilerplate(
    category: dict[str, Any], locale: str, source_url: str
) -> dict[str, Any]:
    """Copy a category while localizing its generated annotation sentence."""
    localized = dict(category)
    sections = category["sections"]
    localized["annotation"] = build_annotation(
        sections["score_table"],
        sections["prevention"],
        sections["examples"],
        source_url,
        locale,
    )
    localized["source_url"] = source_url
    return localized


def complete_category(parsed: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    if not parsed.get("name"):
        missing.append("title")
    section_labels = {
        "score_table": "Score table",
        "description": "Description",
        "prevention": "How to prevent",
        "examples": "Example attack scenarios",
    }
    for section_key, label in section_labels.items():
        if not parsed["sections"].get(section_key):
            missing.append(label)
    if missing:
        raise ValueError(f"Missing required content: {', '.join(missing)}")

    sections = parsed["sections"]
    return {
        "ref_id": parsed["ref_id"],
        "name": parsed["name"],
        "description": sections["description"],
        "annotation": build_annotation(
            sections["score_table"],
            sections["prevention"],
            sections["examples"],
            parsed["source_url"],
            parsed["language"],
        ),
        "sections": sections,
        "source_url": parsed["source_url"],
        "source_file": parsed["source_file"],
        "relative_links_removed": parsed.get("relative_links_removed", []),
    }


def extract_intro_description(
    path: Path,
    year: int,
    locale: str,
    relative_links_removed: list[dict[str, str]] | None = None,
) -> str:
    lines = read_text(path).splitlines()
    paragraphs: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            paragraphs.append(" ".join(part.strip() for part in current).strip())
            current.clear()

    for line in lines[:100]:
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or stripped == "---"
            or is_image_only(stripped)
            or stripped.startswith("<img")
            or stripped.startswith("{:class=")
            or re.match(r"^(?:[-*+] |\d+\. )", stripped)
        ):
            flush()
            continue
        current.append(stripped)
    flush()

    paragraph_index = 1 if year == 2025 or locale == DEFAULT_LOCALE else 0
    if len(paragraphs) <= paragraph_index:
        raise ValueError(
            f"Could not find the introductory paragraph in {path.name} for {locale}"
        )
    paragraph, replacements = replace_relative_markdown_links(
        paragraphs[paragraph_index]
    )
    if relative_links_removed is not None:
        relative_links_removed.extend(
            {
                "ref_id": f"OWASP-top-10-Web_{year}",
                "locale": locale,
                "source_file": path.name,
                "section": "library_description",
                **replacement,
            }
            for replacement in replacements
        )
    source_label = localized_text(locale)["source"]
    source_url = introduction_page_url(year, locale)
    return f"{paragraph}\n\n{source_label}: {source_url}"


def localize_source_attribution(
    description: str,
    year: int,
    source_locale: str,
    output_locale: str,
) -> str:
    """Replace the generated source line while preserving fallback body text."""
    body, separator, _ = description.rpartition("\n\n")
    if not separator:
        body = description
    source_label = localized_text(output_locale)["source"]
    source_url = introduction_page_url(year, source_locale)
    return f"{body}\n\n{source_label}: {source_url}"


def extract_copyright(
    path: Path,
    year: int,
    locale: str,
    relative_links_removed: list[dict[str, str]] | None = None,
) -> str:
    lines = read_text(path).splitlines()
    heading_indexes = [index for index, line in enumerate(lines) if H2_RE.match(line)]
    if not heading_indexes:
        raise ValueError(f"No H2 section found in {path.name}")

    content = [
        line
        for line in lines[heading_indexes[-1] + 1 :]
        if not is_image_only(line) and not line.strip().startswith("<img")
    ]
    result = clean_markdown_block(content)
    if not result:
        raise ValueError(f"The copyright section is empty in {path.name}")
    normalized, replacements = replace_relative_markdown_links(result)
    if relative_links_removed is not None:
        relative_links_removed.extend(
            {
                "ref_id": f"OWASP-top-10-Web_{year}",
                "locale": locale,
                "source_file": path.name,
                "section": "copyright",
                **replacement,
            }
            for replacement in replacements
        )
    return normalized


def find_about_file(locale_dir: Path) -> Path | None:
    for path in sorted(locale_dir.glob("*.md")):
        if re.search(r"about[-_]owasp", path.name, flags=re.IGNORECASE):
            return path
    return None


def category_files(locale_dir: Path, year: int) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in sorted(locale_dir.glob("*.md")):
        match = CATEGORY_FILE_RE.match(path.name)
        if match and int(match.group(2)) == year:
            result[f"A{match.group(1)}"] = path
    return result


def extract_default_locale(locale_dir: Path, year: int) -> dict[str, Any]:
    locale = locale_dir.name
    relative_links_removed: list[dict[str, str]] = []
    index_path = locale_dir / "index.md"
    if not index_path.exists():
        raise ValueError("index.md is missing")

    about_path = find_about_file(locale_dir)
    if about_path is None:
        raise ValueError("About OWASP Markdown file is missing")

    files = category_files(locale_dir, year)
    missing = [ref_id for ref_id in EXPECTED_CATEGORY_IDS if ref_id not in files]
    if missing:
        raise ValueError(f"missing category files: {', '.join(missing)}")

    categories = [
        complete_category(parse_category_page(files[ref_id], year, locale))
        for ref_id in EXPECTED_CATEGORY_IDS
    ]
    return {
        "locale": locale,
        "library": {
            "name": f"OWASP Top 10 Web - {year}",
            "description": extract_intro_description(
                index_path, year, locale, relative_links_removed
            ),
            "copyright": extract_copyright(
                about_path, year, locale, relative_links_removed
            ),
        },
        "categories": categories,
        "relative_links_removed": relative_links_removed,
    }


def add_fallback(
    fallbacks: list[dict[str, Any]],
    locale: str,
    target: str,
    source_file: str,
    missing: list[str],
    reason: str,
) -> None:
    fallbacks.append(
        {
            "locale": locale,
            "target": target,
            "source_file": source_file,
            "missing": missing,
            "reason": reason,
            "fallback_locale": DEFAULT_LOCALE,
        }
    )


def extract_locale_with_fallback(
    locale_dir: Path,
    output_locale: str,
    year: int,
    english: dict[str, Any],
    fallbacks: list[dict[str, Any]],
) -> dict[str, Any]:
    locale = locale_dir.name
    relative_links_removed: list[dict[str, str]] = []
    index_path = locale_dir / "index.md"
    if index_path.exists():
        try:
            description = extract_intro_description(
                index_path, year, locale, relative_links_removed
            )
        except (OSError, ValueError) as exc:
            description = localize_source_attribution(
                english["library"]["description"], year, locale, output_locale
            )
            add_fallback(
                fallbacks,
                output_locale,
                "library description",
                index_path.name,
                ["introductory paragraph"],
                str(exc),
            )
    else:
        description = localize_source_attribution(
            english["library"]["description"], year, locale, output_locale
        )
        add_fallback(
            fallbacks,
            output_locale,
            "library description",
            "index.md",
            ["page"],
            "page is missing",
        )

    files = category_files(locale_dir, year)
    categories: list[dict[str, Any]] = []
    for index, ref_id in enumerate(EXPECTED_CATEGORY_IDS):
        english_category = english["categories"][index]
        path = files.get(ref_id)
        if path is None:
            categories.append(
                category_with_localized_boilerplate(
                    english_category,
                    output_locale,
                    published_page_url(year, locale, english_category["source_file"]),
                )
            )
            add_fallback(
                fallbacks,
                output_locale,
                ref_id,
                english_category["source_file"],
                ["page"],
                (
                    "category page is missing; name and source sections use English, "
                    "while generated boilerplate remains localized"
                ),
            )
            continue

        try:
            parsed = parse_category_page(path, year, locale)
            category = complete_category(parsed)
        except (OSError, ValueError) as exc:
            categories.append(
                category_with_localized_boilerplate(
                    english_category,
                    output_locale,
                    published_page_url(year, locale, path.name),
                )
            )
            add_fallback(
                fallbacks,
                output_locale,
                ref_id,
                path.name,
                ["file"],
                f"file is missing required content: {exc}",
            )
            continue

        categories.append(category)

    return {
        "locale": output_locale,
        "source_locale": locale,
        "library": {
            "name": f"OWASP Top 10 Web - {year}",
            "description": description,
        },
        "categories": categories,
        "relative_links_removed": relative_links_removed,
    }


def export_owasp_top10_json(
    source_root: Path,
    output_path: Path,
    year: int = 2025,
) -> dict[str, Any]:
    docs_root = source_root / str(year) / "docs"
    if not docs_root.exists():
        raise FileNotFoundError(f"OWASP docs directory not found: {docs_root}")

    locale_dirs = sorted(
        [path for path in docs_root.iterdir() if path.is_dir() and path.name != "assets"],
        key=lambda path: path.name.casefold(),
    )
    extracted: dict[str, dict[str, Any]] = {}
    skipped: dict[str, str] = {}
    fallbacks: list[dict[str, Any]] = []
    default_language = language_code(DEFAULT_LOCALE)

    english_dir = next(
        (path for path in locale_dirs if path.name == DEFAULT_LOCALE), None
    )
    if english_dir is None:
        raise ValueError(f"Default locale directory '{DEFAULT_LOCALE}' was not found")
    try:
        extracted[default_language] = extract_default_locale(english_dir, year)
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"Default locale '{DEFAULT_LOCALE}' could not be exported: {exc}"
        ) from exc

    candidates_by_language: dict[str, list[Path]] = {}
    for locale_dir in locale_dirs:
        if locale_dir == english_dir:
            continue
        candidates_by_language.setdefault(language_code(locale_dir.name), []).append(
            locale_dir
        )

    for output_locale, candidates in sorted(candidates_by_language.items()):
        ranked_candidates = sorted(
            candidates,
            key=lambda path: (
                -len(category_files(path, year)),
                path.name.casefold(),
            ),
        )
        locale_dir = ranked_candidates[0]
        locale = locale_dir.name
        for duplicate in ranked_candidates[1:]:
            skipped[duplicate.name] = (
                f"two-letter language code '{output_locale}' is already exported "
                f"from source locale '{locale}'"
            )
        available_pages = len(category_files(locale_dir, year))
        if available_pages < MIN_CATEGORY_PAGES:
            skipped[locale] = (
                f"only {available_pages}/{len(EXPECTED_CATEGORY_IDS)} category pages "
                f"are available; at least {MIN_CATEGORY_PAGES} are required"
            )
            continue
        extracted[output_locale] = extract_locale_with_fallback(
            locale_dir,
            output_locale,
            year,
            extracted[default_language],
            fallbacks,
        )

    locales = [default_language] + sorted(
        [locale for locale in extracted if locale != default_language],
        key=str.casefold,
    )
    threats: list[dict[str, Any]] = []
    for index in range(10):
        english = extracted[default_language]["categories"][index]
        translations = {
            locale: {
                "name": extracted[locale]["categories"][index]["name"],
                "description": extracted[locale]["categories"][index]["description"],
                "annotation": extracted[locale]["categories"][index]["annotation"],
                "source_url": extracted[locale]["categories"][index]["source_url"],
            }
            for locale in locales
        }
        threats.append(
            {
                "ref_id": versioned_ref_id(english["ref_id"], year),
                "source_file": english["source_file"],
                "translations": translations,
            }
        )

    relative_link_replacements: dict[tuple[str, ...], dict[str, str]] = {}
    for locale_data in extracted.values():
        reports = list(locale_data.get("relative_links_removed", []))
        for category in locale_data["categories"]:
            reports.extend(category.get("relative_links_removed", []))
        for report in reports:
            normalized_report = dict(report)
            if re.fullmatch(r"A(?:0[1-9]|10)", normalized_report["ref_id"]):
                normalized_report["ref_id"] = versioned_ref_id(
                    normalized_report["ref_id"], year
                )
            key = tuple(
                normalized_report[field]
                for field in (
                    "ref_id",
                    "locale",
                    "source_file",
                    "section",
                    "text",
                    "path",
                )
            )
            relative_link_replacements[key] = normalized_report

    relative_links_removed = sorted(
        relative_link_replacements.values(),
        key=lambda item: (
            item["ref_id"],
            item["locale"].casefold(),
            item["section"],
            item["path"],
            item["text"],
        ),
    )

    payload: dict[str, Any] = {
        "year": year,
        "source_repository": SOURCE_REPOSITORY,
        "published_site": PUBLISHED_SITE,
        "default_locale": default_language,
        "exported_locales": locales,
        "skipped_locales": skipped,
        "english_fallbacks": fallbacks,
        "relative_links_removed": relative_links_removed,
        "library": {
            "copyright": extracted[default_language]["library"]["copyright"],
            "translations": {
                locale: {
                    "name": extracted[locale]["library"]["name"],
                    "description": extracted[locale]["library"]["description"],
                }
                for locale in locales
            }
        },
        "threats": threats,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract an OWASP Top 10 year with English fallback for missing translations"
    )
    parser.add_argument("source_root", help="Path to the extracted OWASP/Top10 repository")
    parser.add_argument(
        "-y", "--year", type=int, default=2025, help="Release year (default: 2025)"
    )
    parser.add_argument(
        "--output",
        default="owasp-top-10-web-2025.json",
        help="Output JSON path",
    )
    return parser.parse_args()


def write_relative_links_log(
    relative_links: list[dict[str, str]], output_path: Path
) -> Path:
    """Write the detailed relative-link conversion report as a UTF-8 log."""
    lines = [
        "OWASP Top 10 relative links converted to bold",
        f"Count: {len(relative_links)}",
        "",
    ]

    for link in relative_links:
        lines.extend(
            [
                f"Ref ID: {link['ref_id']}",
                f"Locale: {link['locale']}",
                f"Section: {link['section']}",
                f"Source file: {link['source_file']}",
                f"Relative path: {link['path']}",
                f"Original: [{link['text']}]({link['path']})",
                f"Replacement: **{link['text']}**",
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    payload = export_owasp_top10_json(
        source_root=Path(args.source_root),
        output_path=Path(args.output),
        year=args.year,
    )
    locales = payload["exported_locales"]
    print(f"JSON generated: {args.output}")
    print(f"Languages exported: {len(locales)}")
    print(f"Languages: {', '.join(locales)}")
    if payload["english_fallbacks"]:
        print(f"English fallbacks applied: {len(payload['english_fallbacks'])}")
        for fallback in payload["english_fallbacks"]:
            print(
                f"- {fallback['locale']} / {fallback['target']} / "
                f"{fallback['source_file']}: {', '.join(fallback['missing'])} "
                f"({fallback['reason']})"
            )
    if payload["skipped_locales"]:
        print("Skipped languages:")
        for locale, reason in payload["skipped_locales"].items():
            print(f"- {locale}: {reason}")
    relative_links = payload["relative_links_removed"]
    print(f"Relative Markdown links converted to bold: {len(relative_links)}")
    relative_links_log = Path(args.output).with_name(
        f"{Path(args.output).stem}-relative-links.log"
    )
    write_relative_links_log(relative_links, relative_links_log)
    print(f"Relative link log: {relative_links_log}")


if __name__ == "__main__":
    main()
