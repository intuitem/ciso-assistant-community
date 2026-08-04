#!/usr/bin/env python3
"""Add official French CyFun 2025 metadata and texts to a copied workbook.

The input workbook is always supplied with ``--input``.  This allows the French
columns to be appended to a workbook that already contains another language,
such as ``cyfun2025_nl.xlsx``, without modifying that source file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz

import cyfun2025_framework_NL as base


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ENGLISH_PDF = BASE_DIR / "CyFun2025_Booklet_ESSENTIAL_E.pdf"
DEFAULT_FRENCH_PDF = BASE_DIR / "CyFun2025_Booklet-ESSENTIAL_F_pr3.pdf"

FRENCH_FUNCTION_NAMES = {
    "GV": "Gouverner",
    "ID": "Identifier",
    "PR": "Protéger",
    "DE": "Détecter",
    "RS": "Répondre",
    "RC": "Rétablir",
}

FRENCH_CATEGORY_NAMES = {
    "GV.OC": "Contexte organisationnel",
    "GV.RM": "Stratégie de gestion des risques",
    "GV.RR": "Rôles, responsabilités et pouvoirs",
    "GV.PO": "Politique",
    "GV.OV": "Supervision",
    "GV.SC": "Gestion des risques liés à la chaîne d’approvisionnement cyber",
    "ID.AM": "Gestion des actifs",
    "ID.RA": "Évaluation des risques",
    "ID.IM": "Amélioration",
    "PR.AA": "Gestion des identités, authentification et contrôle d’accès",
    "PR.AT": "Sensibilisation et formation",
    "PR.DS": "Sécurité des données",
    "PR.PS": "Sécurité des plateformes",
    "PR.IR": "Résilience de l’infrastructure technologique",
    "DE.CM": "Surveillance continue",
    "DE.AE": "Analyse des événements indésirables",
    "RS.MA": "Gestion des incidents",
    "RS.AN": "Analyse des incidents",
    "RS.CO": "Rapports et communication sur les réponses aux incidents",
    "RS.MI": "Limitations des incidents",
    "RC.RP": "Exécution du plan de rétablissement après incident",
    "RC.CO": "Communication relative au rétablissement après incident",
}

IG_FRENCH_NAMES = {
    "B": "basic",
    "I": "important",
    "E": "essential",
    "BK": "basic - mesures clés",
    "IK": "important - mesures clés",
    "EK": "essential - mesures clés",
    "BG": "basic - aspects de management",
    "IG": "important - aspects de management",
    "EG": "essential - aspects de management",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract official French CyFun 2025 content and append [fr] columns "
            "to a copied workbook."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Workbook to copy, typically the previously generated Dutch workbook.",
    )
    parser.add_argument("--english-pdf", type=Path, default=DEFAULT_ENGLISH_PDF)
    parser.add_argument("--french-pdf", type=Path, default=DEFAULT_FRENCH_PDF)
    parser.add_argument(
        "--output",
        type=Path,
        help="Output workbook. Defaults to <input_stem>_fr.xlsx next to the input.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing output workbook.",
    )
    args = parser.parse_args()
    if args.output is None:
        args.output = args.input.with_name(
            f"{args.input.stem}_fr{args.input.suffix}"
        )
    # The shared extraction entry point uses this attribute name internally.
    args.dutch_pdf = args.french_pdf
    return args


def _find_category_page(
    document: fitz.Document, category_ref: str
) -> tuple[int, list[base.PdfBlock]]:
    """Locate the first real category page, excluding the table of contents."""
    for page_number, page in enumerate(document, start=1):
        blocks = list(base.iter_pdf_blocks(page, page_number))
        for block in blocks:
            match = base.REFERENCE_RE.match(block.text)
            if match is None:
                continue
            ref_id = base.normalized_pdf_reference(match)
            if not ref_id.startswith(f"{category_ref}-") or ref_id.count(".") != 1:
                continue
            if not (
                84 <= block.x0 <= 190
                and block.first_font.endswith("-Bold")
                and block.first_size >= 11.5
            ):
                continue
            return page_number, blocks
    raise ValueError(f"No French category page found for {category_ref}.")


def extract_french_sidebar_content(
    document: fitz.Document,
    expected_categories: set[str],
    expected_functions: set[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Extract French category descriptions despite malformed diagram labels.

    The pre-release French booklet contains several diagram inconsistencies:
    early category codes use parentheses instead of brackets, ID.IM overlaps the
    function label, and the RC.RP diagram is labelled RC.CO.  The category prose
    is nevertheless present in the upper panel of each first category page.
    """
    missing_functions = expected_functions - FRENCH_FUNCTION_NAMES.keys()
    missing_categories = expected_categories - FRENCH_CATEGORY_NAMES.keys()
    if missing_functions or missing_categories:
        raise ValueError(
            "Missing French heading labels: "
            f"functions={sorted(missing_functions)}, "
            f"categories={sorted(missing_categories)}."
        )

    category_descriptions: dict[str, str] = {}
    for category_ref in sorted(expected_categories):
        page_number, blocks = _find_category_page(document, category_ref)
        description_candidates = [
            block
            for block in blocks
            if block.x0 >= 280
            and block.y0 <= 260
            and block.x1 <= 570
            and block.first_size <= 12
            and len(base.clean_inline_text(block.text)) >= 40
        ]
        if description_candidates:
            description_block = max(
                description_candidates,
                key=lambda block: len(base.clean_inline_text(block.text)),
            )
            category_descriptions[category_ref] = base.clean_inline_text(
                description_block.text
            )
            continue

        inline_description = ""
        for marker in (f"[{category_ref}]", f"({category_ref})"):
            marker_block = next(
                (block for block in blocks if marker in block.text), None
            )
            if marker_block is None:
                continue
            inline_description = base.clean_inline_text(
                marker_block.text.split(marker, 1)[1]
            )
            if inline_description:
                break
        if not inline_description:
            raise ValueError(
                f"No French category description found for {category_ref} "
                f"on PDF page {page_number}."
            )
        category_descriptions[category_ref] = inline_description

    return (
        {ref_id: FRENCH_FUNCTION_NAMES[ref_id] for ref_id in expected_functions},
        {ref_id: FRENCH_CATEGORY_NAMES[ref_id] for ref_id in expected_categories},
        category_descriptions,
    )


def configure_french_extraction() -> None:
    base.LANGUAGE_CODE = "fr"
    base.LANGUAGE_NAME = "French"
    base.INTRODUCTION_HEADING = "INTRODUCTION"
    base.TRANSLATED_COLUMNS = tuple(
        base.localized_column(field_name)
        for field_name in ("name", "description", "annotation")
    )
    base.FORBIDDEN_LOCALIZED_SHEET_NAMES = {
        "requirements_content_fr",
        "controls_content_fr",
        "IG_content_fr",
        "scores_content_fr",
    }
    base.GUIDANCE_LABELS = ("Implementation guidance", "Guide de mise en œuvre")
    base.REFERENCES_LABELS = ("References", "Références")
    base.REFERENCE_TEXT_REPLACEMENTS = {
        # Typographical error in the official French pre-release booklet.
        "PPR.IR-01.4": "PR.IR-01.4",
    }
    base.EXPECTED_TARGET_BULLET_INDENTATIONS = {0, 4}
    base.IG_DUTCH_NAMES = IG_FRENCH_NAMES
    base.IG_REQUIRED_TERMS = (
        "basic",
        "important",
        "essential",
        "mesures clés",
        "aspects de management",
    )
    base.parse_arguments = parse_arguments
    base.extract_sidebar_content = extract_french_sidebar_content


def main() -> int:
    configure_french_extraction()
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
