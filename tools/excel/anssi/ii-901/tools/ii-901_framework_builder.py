#!/usr/bin/env python3
"""
Build the II 901 framework workbook from the source PDF.

The parser intentionally focuses on "Annexe 1 - Règles pour les entités situées
hors du champ d'application de la PSSIE" and stops before Annexe 2. It relies on
PyMuPDF text blocks because the source PDF contains scanned-looking layout cues:
centered blue section banners, italic objective labels/descriptions, left-aligned
subtitles, and recommendation IDs.
"""


import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import fitz
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


SCRIPT_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = SCRIPT_DIR.parent
DEFAULT_PDF = FRAMEWORK_DIR / "ii_901_cir_39217.pdf"
DEFAULT_OUTPUT = FRAMEWORK_DIR / "ii-901.xlsx"

FRAMEWORK_REF_ID = "II-901"
URN_ROOT = "ii-901_annexe-1"
FRAMEWORK_NAME = (
    "II n° 901/SGDSN/ANSSI - Instruction interministérielle n° 901 relative à la protection "
    "des systèmes d'information sensibles (Annexe 1)"
)
FRAMEWORK_DESCRIPTION = (
    """La présente instruction définit les objectifs et les règles relatifs à la protection des systèmes d'information sensibles, notamment ceux traitant des informations portant la mention *Diffusion Restreinte*.

La présente instruction s'adresse à l'ensemble des personnes physiques ou morales intervenant dans ces systèmes.

Le respect des règles contribue à garantir la continuité des activités de l'entité qui met en œuvre le système d'information, à protéger l'image de cette entité, à prévenir la compromission d'informations sensibles et à assurer la sécurité des personnes et des biens.

Ces règles peuvent être précisées au cas par cas en s'appuyant sur les normes techniques existantes et sur les guides techniques et les recommandations de l'Agence nationale de la sécurité des systèmes d'information (ANSSI)."""
)

CONTENT_SHEET = "II-901_content"
CONTENT_COLUMNS = [
    "assessable",
    "depth",
    "ref_id",
    "name",
    "description",
]

LIBRARY_META_ROWS: tuple[tuple[str, str], ...] = (
    ("type", "library"),
    ("urn", f"urn:intuitem:risk:library:{URN_ROOT}"),
    ("version", "1"),
    ("locale", "fr"),
    ("ref_id", FRAMEWORK_REF_ID),
    ("name", FRAMEWORK_NAME),
    ("description", FRAMEWORK_DESCRIPTION),
    ("copyright", "SGDSN / ANSSI"),
    ("provider", "ANSSI"),
    ("packager", "intuitem"),
)

FRAMEWORK_META_ROWS: tuple[tuple[str, str], ...] = (
    ("type", "framework"),
    ("base_urn", f"urn:intuitem:risk:req_node:{URN_ROOT}"),
    ("urn", f"urn:intuitem:risk:framework:{URN_ROOT}"),
    ("ref_id", FRAMEWORK_REF_ID),
    ("name", FRAMEWORK_NAME),
    ("description", FRAMEWORK_DESCRIPTION),
)

SECTION_NAMES_BY_ORDER: tuple[str, ...] = (
    "Politique, organisation, gouvernance",
    "Ressources humaines",
    "Gestion des biens",
    "Intégration de la SSI dans le cycle de vie des systèmes d'information",
    "Sécurité physique",
    "Sécurité des réseaux",
    "Architecture des systèmes d'information",
    "Exploitation des systèmes d'information",
    "Sécurité du poste de travail",
    "Traitement des incidents",
    "Continuité d'activité",
    "Conformité, audit, inspection, contrôle",
)


ANNEXE_1_RE = re.compile(r"annexe\s+1", re.IGNORECASE)
ANNEXE_2_RE = re.compile(r"annexe\s+2", re.IGNORECASE)
OBJECTIVE_RE = re.compile(r"^obje", re.IGNORECASE)
RECOMMENDATION_RE = re.compile(
    r"^\s*(?P<raw_id>[A-Z0-9][A-Z0-9\s-]{1,55}[A-Z0-9])\s*:\s*(?P<body>.+)$",
    re.IGNORECASE,
)
PAGE_NUMBER_RE = re.compile(r"^\d{1,2}$")
LIST_MARKER_RE = re.compile(r"^(?:[•▪■]\s*|-\s*)")


@dataclass(slots=True)
class TextBlock:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    fonts: tuple[str, ...]

    @property
    def is_italic(self) -> bool:
        return any("Italic" in font for font in self.fonts)


@dataclass(slots=True)
class ContentRow:
    assessable: str | None
    depth: int
    ref_id: str | None
    name: str | None
    description: str | None = None
    last_description_block: TextBlock | None = None

    def as_tuple(self) -> tuple[str | int | None, ...]:
        return (
            self.assessable,
            self.depth,
            self.ref_id,
            self.name,
            self.description,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the II 901 framework XLSX from the source PDF."
    )
    parser.add_argument("input", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print detected sections, objectives, and recommendation count.",
    )
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"\s+", " ", text)
    text = text.replace("1 '", "l'").replace("1'", "l'")
    text = re.sub(r"\b1\s+([aeiouhAÉÈÊÎÏÔÛÙÜYy])", r"l'\1", text)
    text = text.replace("J'", "l'")
    text = text.replace("J ournalisation", "Journalisation")
    text = text.replace("et! 'usage", "et l'usage")
    text = re.sub(r"\b([cdjlmnst])\s+'\s*", r"\1'", text)
    text = re.sub(r"\b(qu|jusqu|lorsqu|puisqu)\s+'\s*", r"\1'", text)
    text = re.sub(r"\b([cdjlmnst])'\s+", r"\1'", text)
    text = re.sub(r"\b(qu|jusqu|lorsqu|puisqu)'\s+", r"\1'", text)
    text = re.sub(r"\bJe\b", "le", text)
    text = text.replace("ANS SI", "ANSSI").replace("A NS SI", "ANSSI")
    text = text.replace("PSS I", "PSSI")
    text = text.replace("re sponsabilités", "responsabilités")
    text = text.replace("arrivees", "arrivées")
    text = text.replace("tracabilité", "traçabilité")
    text = text.replace("VISiteurs", "visiteurs")
    text = text.replace("sécurisa/ion", "sécurisation")
    text = text.replace("a/Laques", "attaques")
    text = text.replace("altaques", "attaques")
    text = text.replace("incidenls", "incidents")
    text = text.replace("en étal", "en état")
    text = text.replace("elles tester", "et les tester")
    text = text.replace(" el configurer", " et configurer")
    text = text.replace("Config ur er", "Configurer")
    text = text.replace("locau x", "locaux")
    text = text.replace("rése au", "réseau")
    text = text.replace("mmtmtser", "minimiser")
    text = text.replace("Jabellisé", "labellisé")
    text = text.replace("châmes", "chaînes")
    text = text.replace("sa uvegardes", "sauvegardes")
    text = text.replace("autocornmutateurs", "autocommutateurs")
    text = text.replace("extemalisation", "externalisation")
    text = text.replace("àjour", "à jour")
    text = text.replace("conna.Jtre", "connaître")
    text = text.replace("défmi", "défini")
    text = text.replace("v1gueur", "vigueur")
    text = text.replace("dans La mesure", "dans la mesure")
    text = text.replace("arc-en- ciel", "arc-en-ciel")
    text = text.replace(
        "d'informations sensibles doivent être effectuées selon une préalablement, "
        "garantissant un contrôle par l'utilisateur, du l'impressionjusqu'à la "
        "récupération du support imprimé. Les impressions procédure définie "
        "déclenchement de",
        "Les impressions d'informations sensibles doivent être effectuées selon "
        "une procédure définie préalablement, garantissant un contrôle par "
        "l'utilisateur, du déclenchement de l'impression jusqu'à la récupération "
        "du support imprimé.",
    )
    return text.strip()


def clean_ref_id(raw_id: str) -> str:
    ref_id = re.sub(r"\s+", "", raw_id.upper())
    ref_id = ref_id.replace("–", "-").replace("—", "-")
    ref_id = ref_id.replace("DEY-", "DEV-")
    ref_id = ref_id.replace("POT-", "PDT-")
    ref_id = ref_id.replace("TL-", "TI-")
    ref_id = ref_id.replace("T1-", "TI-")
    ref_id = ref_id.replace("-YERIF", "-VERIF")
    ref_id = ref_id.replace("SECX-DIST", "SEC-DIST")
    ref_id = ref_id.replace("SERY", "SERV")
    ref_id = ref_id.replace("OESACTIV", "DESACTIV")
    ref_id = ref_id.replace("-FIL T", "-FILT")
    ref_id = ref_id.replace("FILT-APPL", "FILT-APPL")
    return ref_id


def clean_name(text: str) -> str:
    text = clean_text(text)
    text = text.strip(" .")
    for index, char in enumerate(text):
        if char.isalpha():
            return f"{text[:index]}{char.upper()}{text[index + 1:]}"
    return text


def clean_multiline_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        cleaned = clean_text(line)
        if line.lstrip().startswith("* "):
            cleaned = f"{' ' * indent}{cleaned}"
        cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines)


def strip_list_marker(text: str) -> str:
    return LIST_MARKER_RE.sub("", text).strip()


def list_level(block: TextBlock) -> int:
    if block.x0 < 125:
        return 0
    return int((block.x0 - 125) // 45) + 1


def starts_new_paragraph(previous_block: TextBlock | None, block: TextBlock) -> bool:
    if previous_block is None:
        return False
    if previous_block.page != block.page:
        return True
    return block.y0 - previous_block.y1 > 4


def append_description_block(
    description: str | None, block: TextBlock, previous_block: TextBlock | None = None
) -> str:
    text = clean_text(block.text)
    if not text:
        return description or ""

    existing = description or ""
    lines = existing.splitlines()
    has_list = any(line.lstrip().startswith("* ") for line in lines)
    last_line = lines[-1] if lines else ""
    marker = LIST_MARKER_RE.match(text)
    explicit_list_item = marker is not None
    inferred_list_item = (
        block.x0 >= 155 and (has_list or last_line.rstrip().endswith(":"))
    )
    should_be_list_item = explicit_list_item or inferred_list_item

    if should_be_list_item:
        item_text = clean_text(strip_list_marker(text))
        level = max(1, list_level(block))
        prefix = f"{'  ' * (level - 1)}* "
        return clean_multiline_text(f"{existing}\n{prefix}{item_text}")

    if has_list and block.x0 >= 120 and lines:
        lines[-1] = clean_text(f"{last_line} {text}")
        return clean_multiline_text("\n".join(lines))

    if starts_new_paragraph(previous_block, block):
        return clean_multiline_text(f"{existing}\n{text}")

    return clean_multiline_text(" ".join(part for part in (existing, text) if part))


def is_noise(block: TextBlock) -> bool:
    if PAGE_NUMBER_RE.fullmatch(block.text):
        return True
    if block.y0 > 775:
        return True
    if block.y0 > 740 and re.match(r"^\d+\s+", block.text):
        return True
    if block.text.startswith("9 Ces règles sont adaptées"):
        return True
    return False


def is_annexe_heading(block: TextBlock, annexe_re: re.Pattern[str]) -> bool:
    text = block.text.strip()
    return bool(annexe_re.search(text)) and text.lower().startswith("annexe") and "..." not in text


def is_objective_marker(block: TextBlock) -> bool:
    compact = re.sub(r"[^a-z]", "", block.text.lower())
    return block.y1 - block.y0 < 24 and (
        compact.startswith("objecti")
        or compact.startswith("objectif")
        or compact.startswith("objecli")
        or compact.startswith("objectif")
        or OBJECTIVE_RE.match(block.text) is not None
    )


def split_recommendation(text: str) -> tuple[str, str, str] | None:
    match = RECOMMENDATION_RE.match(text)
    if not match:
        return None

    raw_id = match.group("raw_id")
    if "-" not in raw_id:
        return None

    ref_id = clean_ref_id(raw_id)
    body = clean_text(match.group("body"))
    title, separator, description = body.partition(". ")
    if not separator:
        return ref_id, clean_name(body), None
    return ref_id, clean_name(title), clean_text(description)


def is_heading(block: TextBlock) -> bool:
    if split_recommendation(block.text):
        return False
    if is_objective_marker(block):
        return False
    if block.text.startswith(("•", "-", "n ")):
        return False
    if block.x0 > 100:
        return False
    if block.text.endswith("."):
        return False
    return len(block.text) <= 180


def get_block_text(block: dict) -> tuple[str, tuple[str, ...]]:
    parts: list[str] = []
    fonts: list[str] = []
    for line in block.get("lines", []):
        line_parts: list[str] = []
        for span in line.get("spans", []):
            span_text = span.get("text", "")
            if span_text:
                line_parts.append(span_text)
                fonts.append(span.get("font", ""))
        if line_parts:
            parts.append("".join(line_parts))
    return clean_text(" ".join(parts)), tuple(fonts)


def extract_annexe_1_blocks(pdf_path: Path) -> list[TextBlock]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    blocks: list[TextBlock] = []
    in_annexe_1 = False

    for page_index, page in enumerate(doc, start=1):
        page_blocks: list[TextBlock] = []
        for raw_block in page.get_text("dict")["blocks"]:
            if raw_block.get("type") != 0:
                continue
            text, fonts = get_block_text(raw_block)
            if not text:
                continue
            x0, y0, x1, y1 = raw_block["bbox"]
            page_blocks.append(TextBlock(page_index, x0, y0, x1, y1, text, fonts))

        page_blocks.sort(key=lambda item: (item.y0, item.x0))
        for block in page_blocks:
            if in_annexe_1 and is_annexe_heading(block, ANNEXE_2_RE):
                return blocks
            if is_annexe_heading(block, ANNEXE_1_RE):
                in_annexe_1 = True
                continue
            if in_annexe_1 and not is_noise(block):
                blocks.append(block)

    return blocks


def next_significant_block(blocks: Sequence[TextBlock], start_index: int) -> TextBlock | None:
    for block in blocks[start_index + 1 :]:
        if not is_noise(block):
            return block
    return None


def is_section_banner(blocks: Sequence[TextBlock], index: int) -> bool:
    block = blocks[index]
    if split_recommendation(block.text) or is_objective_marker(block):
        return False
    next_block = next_significant_block(blocks, index)
    if not next_block or not is_objective_marker(next_block):
        return False
    if block.x0 < 120 or block.y1 - block.y0 > 25:
        return False
    return True


def append_to_previous_description(rows: list[ContentRow], block: TextBlock) -> None:
    if not rows:
        return
    previous = rows[-1]
    previous.description = append_description_block(
        previous.description, block, previous.last_description_block
    )
    previous.last_description_block = block


def collect_objective_description(
    blocks: Sequence[TextBlock], start_index: int
) -> tuple[str | None, TextBlock | None, int]:
    description: str | None = None
    last_description_block: TextBlock | None = None
    index = start_index + 1

    while index < len(blocks) and blocks[index].is_italic:
        if not is_noise(blocks[index]) and not is_objective_marker(blocks[index]):
            description = append_description_block(
                description, blocks[index], last_description_block
            )
            last_description_block = blocks[index]
        index += 1

    while index < len(blocks):
        block = blocks[index]
        if (
            is_noise(block)
            or is_objective_marker(block)
            or split_recommendation(block.text)
            or is_section_banner(blocks, index)
            or is_heading(block)
        ):
            break
        description = append_description_block(description, block, last_description_block)
        last_description_block = block
        index += 1

    return description, last_description_block, index


def parse_content_rows(blocks: Sequence[TextBlock], debug: bool = False) -> list[ContentRow]:
    rows: list[ContentRow] = []
    current_title_ref_id: str | None = None
    title_number = 0
    objective_number = 0
    section_number = 0

    index = 0
    while index < len(blocks):
        block = blocks[index]

        if is_section_banner(blocks, index):
            section_number += 1
            section_name = (
                SECTION_NAMES_BY_ORDER[section_number - 1]
                if section_number <= len(SECTION_NAMES_BY_ORDER)
                else clean_name(block.text)
            )
            rows.append(ContentRow(None, 1, None, section_name))
            current_title_ref_id = None
            title_number = 0
            if debug:
                print(f"section {section_number}: {section_name} (raw: {block.text})")
            index += 1
            continue

        if is_objective_marker(block):
            objective_number += 1
            title_number = 0
            current_title_ref_id = None
            description, last_description_block, next_index = collect_objective_description(
                blocks, index
            )
            rows.append(
                ContentRow(
                    None,
                    2,
                    str(objective_number),
                    f"Objectif {objective_number}",
                    description,
                    last_description_block,
                )
            )
            if debug:
                print(f"objective {objective_number}: {description}")
            index = next_index
            continue

        recommendation = split_recommendation(block.text)
        if recommendation:
            ref_id, name, description = recommendation
            rows.append(
                ContentRow(
                    "x",
                    4 if current_title_ref_id else 3,
                    ref_id,
                    name,
                    description,
                    block if description else None,
                )
            )
            index += 1
            continue

        if is_heading(block):
            title_number += 1
            current_title_ref_id = f"{objective_number}.{title_number}"
            rows.append(
                ContentRow(
                    None,
                    3,
                    current_title_ref_id,
                    clean_name(block.text),
                )
            )
            index += 1
            continue

        append_to_previous_description(rows, block)
        index += 1

    if debug:
        requirements = sum(1 for row in rows if row.assessable == "x")
        print(f"parsed rows: {len(rows)}")
        print(f"parsed requirements: {requirements}")
        print(f"parsed objectives: {objective_number}")

    return rows


def write_key_value_sheet(workbook: Workbook, sheet_name: str, rows: Iterable[tuple[str, str]]) -> None:
    worksheet = workbook.create_sheet(sheet_name)
    for row in rows:
        worksheet.append(row)
    worksheet.column_dimensions["A"].width = 32
    worksheet.column_dimensions["B"].width = 120
    worksheet["A1"].font = Font(bold=True)
    worksheet["B1"].font = Font(bold=True)


def write_content_sheet(workbook: Workbook, rows: Sequence[ContentRow]) -> None:
    worksheet = workbook.create_sheet(CONTENT_SHEET)
    worksheet.append(CONTENT_COLUMNS)

    for row in rows:
        worksheet.append(row.as_tuple())

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font

    widths = {
        "A": 12,
        "B": 10,
        "C": 22,
        "D": 55,
        "E": 120,
    }
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width

    for row in worksheet.iter_rows(min_row=1):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    for row in worksheet.iter_rows(min_row=2):
        depth = row[1].value
        if depth in (1, 2, 3):
            for cell in row:
                cell.font = Font(bold=True if depth in (1, 2) else False)

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = (
        f"A1:{get_column_letter(len(CONTENT_COLUMNS))}{worksheet.max_row}"
    )


def build_workbook(rows: Sequence[ContentRow], output_path: Path) -> None:
    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    write_key_value_sheet(workbook, "library_meta", LIBRARY_META_ROWS)
    write_key_value_sheet(workbook, "II-901_meta", FRAMEWORK_META_ROWS)
    write_content_sheet(workbook, rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def main() -> None:
    args = parse_args()
    blocks = extract_annexe_1_blocks(args.input)
    rows = parse_content_rows(blocks, debug=args.debug)
    build_workbook(rows, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
