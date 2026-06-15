#!/usr/bin/env python3
"""
CNIL PIA Knowledge Base - JSON Referential Exporter
===================================================

Exports the PIA knowledge base entries and all available i18n translations
from the LINCnil/pia repository into one consolidated JSON file.

Outputs
-------
- `bdc_repo.json`

Run
---
python cnil_BDC_export_referentiels_json.py --repo-root <path-to-pia-repo>
python cnil_BDC_export_referentiels_json.py --repo-root <path-to-pia-repo> --force-source-locale
"""

import argparse
import json
import re
import sys
from html import unescape
from pathlib import Path
from typing import Any


KNOWLEDGE_BASE_FILE = Path("src") / "assets" / "files" / "pia_knowledge-base.json"
I18N_DIR = Path("src") / "assets" / "i18n"
DEFAULT_LOCALE = "fr"

SOURCE_LABELS = {
    "ar": "المصدر",
    "bg": "Източник",
    "cs": "Zdroj",
    "da": "Kilde",
    "de": "Quelle",
    "el": "Πηγή",
    "en": "Source",
    "es": "Fuente",
    "et": "Allikas",
    "fi": "Lähde",
    "fr": "Source",
    "hr": "Izvor",
    "hu": "Forrás",
    "it": "Fonte",
    "lt": "Šaltinis",
    "lv": "Avots",
    "nl": "Bron",
    "no": "Kilde",
    "pl": "Źródło",
    "pt": "Fonte",
    "ro": "Sursă",
    "sl": "Vir",
    "sv": "Källa",
}

EMPTY_SOURCE_VALUES = {
    "aucun",
    "aucune",
    "none",
    "n/a",
    "na",
    "-",
}

EN_FALLBACK_NAME = "CNIL - PIA's knowledge base"
EN_FALLBACK_DESCRIPTION = (
    "It provides contextual assistance in carrying out the analysis and is based on "
    "the GDPR, the security guide and the CNIL's PIA guides"
)

METADATA_NAME_TRANSLATIONS = {
    "ar": "CNIL - قاعدة معارف PIA",
    "cs": "CNIL - Znalostní báze PIA",
    "da": "CNIL - PIA-vidensbase",
    "el": "CNIL - Βάση γνώσεων PIA",
    "es": "CNIL - Base de conocimientos PIA",
    "et": "CNIL - PIA teadmistebaas",
    "fi": "CNIL - PIA-tietopankki",
    "hr": "CNIL - Baza znanja PIA",
    "hu": "CNIL - PIA tudásbázis",
    "lt": "CNIL - PIA žinių bazė",
    "lv": "CNIL - PIA zināšanu bāze",
    "no": "CNIL - PIA-kunnskapsbase",
    "ro": "CNIL - Baza de cunoștințe PIA",
    "sl": "CNIL - Zbirka znanja PIA",
    "sv": "CNIL - PIA-kunskapsbas",
}

METADATA_DESCRIPTION_TRANSLATIONS = {
    "ar": "توفر مساعدة سياقية عند إجراء التحليل، وتستند إلى اللائحة العامة لحماية البيانات (GDPR) ودليل الأمن وأدلة PIA الصادرة عن CNIL.",
    "cs": "Poskytuje kontextovou pomoc při provádění analýzy a vychází z GDPR, bezpečnostní příručky a příruček PIA od CNIL.",
    "da": "Den giver kontekstuel hjælp til at gennemføre analysen og bygger på GDPR, sikkerhedsvejledningen og CNIL's PIA-vejledninger.",
    "el": "Παρέχει βοήθεια με βάση τα συμφραζόμενα για τη διενέργεια της ανάλυσης και βασίζεται στον GDPR, στον οδηγό ασφάλειας και στους οδηγούς PIA της CNIL.",
    "es": "Proporciona ayuda contextual para realizar el análisis y se basa en el RGPD, la guía de seguridad y las guías PIA de la CNIL.",
    "et": "See pakub analüüsi tegemisel kontekstipõhist abi ning tugineb GDPR-ile, turvajuhendile ja CNIL-i PIA juhenditele.",
    "fi": "Se tarjoaa kontekstuaalista tukea analyysin tekemiseen ja perustuu GDPR:ään, turvallisuusoppaaseen sekä CNILin PIA-oppaisiin.",
    "hr": "Pruža kontekstualnu pomoć pri provedbi analize i temelji se na GDPR-u, sigurnosnom vodiču i CNIL-ovim PIA vodičima.",
    "hu": "Kontextuális segítséget nyújt az elemzés elvégzéséhez, és a GDPR-on, a biztonsági útmutatón, valamint a CNIL PIA útmutatóin alapul.",
    "lt": "Ji teikia kontekstinę pagalbą atliekant analizę ir remiasi BDAR, saugumo vadovu bei CNIL PIA vadovais.",
    "lv": "Tā sniedz kontekstuālu palīdzību analīzes veikšanā un balstās uz GDPR, drošības rokasgrāmatu un CNIL PIA rokasgrāmatām.",
    "no": "Den gir kontekstuell hjelp til å gjennomføre analysen og bygger på GDPR, sikkerhetsveiledningen og CNILs PIA-veiledninger.",
    "pl": "Zapewnia kontekstową pomoc w przeprowadzaniu analizy i opiera się na RODO, przewodniku bezpieczeństwa oraz przewodnikach PIA CNIL.",
    "ro": "Oferă asistență contextuală pentru realizarea analizei și se bazează pe GDPR, ghidul de securitate și ghidurile PIA ale CNIL.",
    "sl": "Zagotavlja kontekstualno pomoč pri izvedbi analize ter temelji na GDPR, varnostnem vodniku in smernicah PIA organizacije CNIL.",
    "sv": "Den ger kontextuellt stöd för att genomföra analysen och bygger på GDPR, säkerhetsguiden och CNIL:s PIA-guider.",
}


def display_path(path: Path, base_dir: Path) -> str:
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_by_dotted_path(payload: Any, dotted_path: str, default: Any = "") -> Any:
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return default
    return current


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def strip_html_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


def _replace_anchor(match: re.Match[str]) -> str:
    attrs = match.group(1)
    label = html_to_markdown(match.group(2), compact=True)
    href_match = re.search(r"""href\s*=\s*["']([^"']+)["']""", attrs, re.I)
    if not href_match:
        return label
    href = unescape(href_match.group(1).strip())
    if not label:
        return href
    if label == href:
        return label
    return f"[{label}]({href})"


def html_to_markdown(value: Any, compact: bool = False) -> str:
    text = as_text(value).replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return ""

    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<a\b([^>]*)>(.*?)</a>", _replace_anchor, text, flags=re.I | re.S)

    for level in range(6, 0, -1):
        text = re.sub(
            rf"<h{level}\b[^>]*>(.*?)</h{level}>",
            lambda m, lvl=level: "\n\n" + ("#" * lvl) + " " + html_to_markdown(m.group(1), compact=True) + "\n\n",
            text,
            flags=re.I | re.S,
        )

    text = re.sub(
        r"<(strong|b)\b[^>]*>(.*?)</\1>",
        lambda m: "**" + html_to_markdown(m.group(2), compact=True) + "**",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r"<(em|i)\b[^>]*>(.*?)</\1>",
        lambda m: "*" + html_to_markdown(m.group(2), compact=True) + "*",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r"<li\b[^>]*>(.*?)</li>",
        lambda m: "\n- " + html_to_markdown(m.group(1), compact=True),
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|section|article|ul|ol|table|tr)\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<(p|div|section|article|ul|ol|table|tr|td|th)\b[^>]*>", "\n", text, flags=re.I)
    text = strip_html_tags(text)
    text = unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    if compact:
        text = re.sub(r"\s+", " ", text)
    else:
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def category_key(category_path: Any) -> str:
    value = as_text(category_path).strip()
    prefix = "knowledge_base.category."
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value.split(".")[-1] if value else ""


def load_i18n_files(repo_root: Path) -> dict[str, dict[str, Any]]:
    i18n_dir = repo_root / I18N_DIR
    if not i18n_dir.exists():
        raise FileNotFoundError(f"i18n directory not found: {i18n_dir}")

    locales: dict[str, dict[str, Any]] = {}
    for path in sorted(i18n_dir.glob("*.json")):
        locales[path.stem] = read_json(path)
    if DEFAULT_LOCALE not in locales:
        raise ValueError(f"Default locale '{DEFAULT_LOCALE}' not found in {i18n_dir}")
    return locales


def source_label(locale: str) -> str:
    base = locale.split("-")[0].split("_")[0].lower()
    return SOURCE_LABELS.get(base, "Source")


def annotation_for_locale(locale: str, source: str) -> str:
    source = html_to_markdown(source)
    if not source:
        return ""
    return f"{source_label(locale)} : {source}"


def metadata_name_from_locale(payload: dict[str, Any]) -> str:
    name = html_to_markdown(
        get_by_dotted_path(payload, "knowledge_base.default_knowledge_base", ""),
        compact=True,
    )
    if not name:
        return ""
    name = name.replace("CNIL", "PIA")
    return f"CNIL - {name}"


def metadata_description_from_locale(payload: dict[str, Any]) -> str:
    description = html_to_markdown(
        get_by_dotted_path(payload, "onboarding.entry.step6.description", "")
    )
    paragraphs = [p.strip() for p in description.split("\n\n") if p.strip()]
    return paragraphs[0] if paragraphs else ""


def replace_english_metadata_fallbacks(
    framework_names: dict[str, str],
    framework_descriptions: dict[str, str],
) -> None:
    for locale, translated_name in METADATA_NAME_TRANSLATIONS.items():
        if framework_names.get(locale) == EN_FALLBACK_NAME:
            framework_names[locale] = translated_name

    for locale, translated_description in METADATA_DESCRIPTION_TRANSLATIONS.items():
        if framework_descriptions.get(locale) == EN_FALLBACK_DESCRIPTION:
            framework_descriptions[locale] = translated_description


def collect_categories(locales: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    category_keys: set[str] = set()
    for payload in locales.values():
        categories = get_by_dotted_path(payload, "knowledge_base.category", {})
        if isinstance(categories, dict):
            category_keys.update(str(k) for k in categories)

    out: dict[str, dict[str, str]] = {}
    for key in sorted(category_keys):
        translations: dict[str, str] = {}
        for locale, payload in locales.items():
            value = get_by_dotted_path(payload, f"knowledge_base.category.{key}", "")
            value = html_to_markdown(value, compact=True)
            if value:
                translations[locale] = value
        out[key] = {
            "ref_id": key,
            "translations": translations,
        }
    return out


def build_entry(base_entry: dict[str, Any], locales: dict[str, dict[str, Any]]) -> dict[str, Any]:
    slug = as_text(base_entry.get("slug")).strip()
    if not slug:
        raise ValueError("A knowledge-base entry has no slug")

    name_path = as_text(base_entry.get("name")) or f"knowledge_base.slugs.{slug}.name"
    description_path = (
        as_text(base_entry.get("description"))
        or f"knowledge_base.slugs.{slug}.description"
    )
    source_path = f"knowledge_base.slugs.{slug}.source"
    cat_key = category_key(base_entry.get("category"))
    french_source = html_to_markdown(
        get_by_dotted_path(locales.get(DEFAULT_LOCALE, {}), source_path, "")
    )
    french_source_empty = (
        not french_source or french_source.strip().lower() in EMPTY_SOURCE_VALUES
    )

    translations: dict[str, dict[str, str]] = {}
    for locale, payload in locales.items():
        name = html_to_markdown(get_by_dotted_path(payload, name_path, ""), compact=True)
        description = html_to_markdown(get_by_dotted_path(payload, description_path, ""))
        source = html_to_markdown(get_by_dotted_path(payload, source_path, ""))
        if french_source_empty:
            source = ""
            annotation = ""
        else:
            annotation = annotation_for_locale(locale, source)
        if name or description or annotation:
            translations[locale] = {
                "name": name,
                "description": description,
                "source": source,
                "annotation": annotation,
                "category_name": html_to_markdown(
                    get_by_dotted_path(payload, f"knowledge_base.category.{cat_key}", ""),
                    compact=True,
                ),
            }

    return {
        "slug": slug,
        "filters": as_text(base_entry.get("filters")),
        "category": cat_key,
        "source_paths": {
            "name": name_path,
            "description": description_path,
            "source": source_path,
        },
        "translations": translations,
    }


def export_referentiels_json(
    repo_root: Path,
    out_dir: Path,
    output_file: str = "bdc_repo.json",
    force_source_locale: bool = False,
) -> Path:
    repo_root = repo_root.resolve()
    out_dir = out_dir.resolve()
    kb_path = repo_root / KNOWLEDGE_BASE_FILE
    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge-base file not found: {kb_path}")

    knowledge_base = read_json(kb_path)
    if not isinstance(knowledge_base, list):
        raise ValueError("pia_knowledge-base.json must contain a list of objects")

    locales = load_i18n_files(repo_root)
    framework_names = {
        locale: metadata_name_from_locale(payload)
        for locale, payload in locales.items()
    }
    framework_names = {
        locale: name for locale, name in framework_names.items() if name
    }
    framework_descriptions = {
        locale: metadata_description_from_locale(payload)
        for locale, payload in locales.items()
    }
    framework_descriptions = {
        locale: desc for locale, desc in framework_descriptions.items() if desc
    }
    if not force_source_locale:
        replace_english_metadata_fallbacks(framework_names, framework_descriptions)

    entries = [
        build_entry(entry, locales)
        for entry in knowledge_base
        if isinstance(entry, dict)
    ]

    output_path = out_dir / output_file
    dump_json(
        output_path,
        {
            "source": {
                "repository": "https://github.com/LINCnil/pia",
                "knowledge_base": str(KNOWLEDGE_BASE_FILE).replace("\\", "/"),
                "i18n": str(I18N_DIR).replace("\\", "/"),
            },
            "default_locale": DEFAULT_LOCALE,
            "locales": sorted(locales),
            "framework_names": framework_names,
            "framework_descriptions": framework_descriptions,
            "categories": collect_categories(locales),
            "knowledge_base": entries,
        },
    )
    return output_path


def main() -> None:
    try:
        parser = argparse.ArgumentParser(
            description="Export one consolidated JSON file from the CNIL PIA knowledge base."
        )
        parser.add_argument(
            "--repo-root",
            required=True,
            help="Path to the LINCnil/pia repository root",
        )
        parser.add_argument("--out-dir", default=".", help="Output directory")
        parser.add_argument("--output-file", default="bdc_repo.json")
        parser.add_argument(
            "-l",
            "--force-source-locale",
            action="store_true",
            help="Keep source locale metadata as-is, without English fallback translations.",
        )
        args = parser.parse_args()

        script_dir = Path(__file__).resolve().parent
        output_path = export_referentiels_json(
            repo_root=Path(args.repo_root),
            out_dir=Path(args.out_dir),
            output_file=args.output_file,
            force_source_locale=args.force_source_locale,
        )
        print(f'- JSON: "{display_path(output_path, script_dir)}"')
    except KeyboardInterrupt:
        print("❌ [ERROR] Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ [ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
