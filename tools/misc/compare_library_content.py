#!/usr/bin/env python3
"""Compare le contenu normalisé de deux bibliothèques YAML ou Excel v2.

Un fichier ``.xlsx`` est converti temporairement avec le convertisseur v2 du
projet avant la comparaison. Le comparateur accepte donc aussi bien deux YAML
qu'un YAML et son classeur source.

Exemple :

    python tools/compare_library_content.py \
        backend/library/libraries/adobe-ccf-v5.yaml \
        tools/excel/adobe/adobe-ccf-v5.xlsx

La normalisation charge le YAML, ce qui convertit notamment ``\\xE9`` et
``\\u00e9`` en ``é``. Elle normalise aussi Unicode (NFC) et les fins de ligne,
mais ne masque aucune différence de valeur, de type, de liste ou de structure.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as datetime_module
import importlib.util
import io
import re
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


YAML_EXTENSIONS = {".yaml", ".yml"}
EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm"}
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
CONVERTER_PATH = PROJECT_ROOT / "backend" / "scripts" / "convert_library_v2.py"
IGNORED_CONVERTER_KEYS = {"convert_library_version"}
BULLET_OR_NUMBERED_LINE = re.compile(r"^(?:[-*•◦▪—]|\d+[.)])\s*")


@dataclass(frozen=True)
class Difference:
    path: str
    reason: str
    left: Any = None
    right: Any = None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare deux bibliothèques YAML ou Excel après normalisation."
    )
    parser.add_argument("left", type=Path, help="Premier fichier YAML ou Excel v2")
    parser.add_argument("right", type=Path, help="Second fichier YAML ou Excel v2")
    parser.add_argument(
        "--compat",
        type=int,
        default=0,
        help="Mode de compatibilité du convertisseur pour un Excel (défaut : 0)",
    )
    parser.add_argument(
        "--max-differences",
        type=int,
        default=100,
        help="Nombre maximal de divergences détaillées (défaut : 100)",
    )
    parser.add_argument(
        "--include-converter-metadata",
        action="store_true",
        help="Compare aussi la métadonnée technique convert_library_version.",
    )
    parser.add_argument(
        "--fail-on-difference",
        action="store_true",
        help="Retourne le code 1 si au moins une divergence est trouvée.",
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as yaml_file:
            return yaml.safe_load(yaml_file)
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Impossible de lire le YAML '{path}': {error}") from error


def load_converter_module() -> Any:
    if not CONVERTER_PATH.is_file():
        raise ValueError(f"Convertisseur v2 introuvable : {CONVERTER_PATH}")

    module_spec = importlib.util.spec_from_file_location(
        "ciso_library_v2_converter", CONVERTER_PATH
    )
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Impossible de charger le convertisseur : {CONVERTER_PATH}")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def convert_excel_to_data(path: Path, compat_mode: int) -> Any:
    """Convertit un Excel v2 dans un fichier temporaire, puis charge son YAML."""

    converter = load_converter_module()
    with tempfile.TemporaryDirectory(prefix="compare_library_content_") as temp_dir:
        converted_yaml = Path(temp_dir) / f"{path.stem}.yaml"
        # Le convertisseur affiche sa progression ; le comparateur n'affiche que
        # son propre rapport afin de garder un résultat directement exploitable.
        with contextlib.redirect_stdout(io.StringIO()):
            converter.create_library(
                str(path),
                str(converted_yaml),
                compat_mode=compat_mode,
                verbose=False,
            )
        return load_yaml(converted_yaml)


def load_source(path: Path, compat_mode: int) -> tuple[Any, str]:
    if not path.is_file():
        raise ValueError(f"Fichier introuvable : {path}")

    suffix = path.suffix.casefold()
    if suffix in YAML_EXTENSIONS:
        return load_yaml(path), "YAML"
    if suffix in EXCEL_EXTENSIONS:
        return convert_excel_to_data(path, compat_mode), "Excel v2 converti temporairement en YAML"
    raise ValueError(
        f"Format non pris en charge pour '{path}'. Formats acceptés : "
        f"{', '.join(sorted(YAML_EXTENSIONS | EXCEL_EXTENSIONS))}"
    )


def normalise_text(value: str) -> str:
    """Supprime les différences d'encodage sans modifier le sens du texte."""

    line_endings_normalised = value.replace("\r\n", "\n").replace("\r", "\n")
    unicode_normalised = unicodedata.normalize("NFC", line_endings_normalised)
    readable_spaces = unicode_normalised.replace("\u00a0", " ").replace("\u202f", " ")
    lines = [line.strip() for line in readable_spaces.split("\n")]

    paragraphs: list[list[str]] = []
    current_paragraph: list[str] = []
    for line in lines:
        if line:
            current_paragraph.append(line)
        elif current_paragraph:
            paragraphs.append(current_paragraph)
            current_paragraph = []
    if current_paragraph:
        paragraphs.append(current_paragraph)

    normalised_paragraphs: list[str] = []
    for paragraph in paragraphs:
        result = paragraph[0]
        for line in paragraph[1:]:
            # Les listes restent lisibles, mais les lignes ordinaires séparées
            # uniquement par le sérialiseur YAML sont jointes comme un texte.
            separator = (
                "\n"
                if BULLET_OR_NUMBERED_LINE.match(result.split("\n")[-1])
                or BULLET_OR_NUMBERED_LINE.match(line)
                else " "
            )
            result = f"{result}{separator}{line}"
        normalised_paragraphs.append(result)

    return "\n\n".join(normalised_paragraphs)


def normalise_data(value: Any, include_converter_metadata: bool) -> Any:
    """Normalise récursivement les valeurs YAML pour une comparaison fiable."""

    if isinstance(value, str):
        return normalise_text(value)
    if isinstance(value, (datetime_module.datetime, datetime_module.date)):
        return value.isoformat()
    if isinstance(value, dict):
        normalised: dict[Any, Any] = {}
        for key, item in value.items():
            normalised_key = normalise_text(key) if isinstance(key, str) else key
            if (
                not include_converter_metadata
                and normalised_key in IGNORED_CONVERTER_KEYS
            ):
                continue
            if normalised_key in normalised:
                raise ValueError(
                    f"Deux clés deviennent identiques après normalisation : {normalised_key!r}"
                )
            normalised[normalised_key] = normalise_data(
                item, include_converter_metadata
            )
        return normalised
    if isinstance(value, list):
        return [normalise_data(item, include_converter_metadata) for item in value]
    if isinstance(value, tuple):
        return tuple(normalise_data(item, include_converter_metadata) for item in value)
    return value


def sort_key(value: Any) -> str:
    return repr(value)


def append_difference(
    differences: list[Difference],
    maximum: int,
    path: str,
    reason: str,
    left: Any = None,
    right: Any = None,
) -> bool:
    if len(differences) < maximum:
        differences.append(Difference(path, reason, left, right))
    return len(differences) >= maximum


def compare_values(
    left: Any,
    right: Any,
    path: str,
    differences: list[Difference],
    maximum: int,
) -> None:
    if len(differences) >= maximum:
        return

    if type(left) is not type(right):
        append_difference(
            differences,
            maximum,
            path,
            f"Type différent ({type(left).__name__} / {type(right).__name__})",
            left,
            right,
        )
        return

    if isinstance(left, dict):
        left_keys = set(left)
        right_keys = set(right)
        for key in sorted(left_keys - right_keys, key=sort_key):
            if append_difference(
                differences, maximum, f"{path}.{key}", "Clé absente à droite", left[key], None
            ):
                return
        for key in sorted(right_keys - left_keys, key=sort_key):
            if append_difference(
                differences, maximum, f"{path}.{key}", "Clé absente à gauche", None, right[key]
            ):
                return
        for key in sorted(left_keys & right_keys, key=sort_key):
            compare_values(left[key], right[key], f"{path}.{key}", differences, maximum)
            if len(differences) >= maximum:
                return
        return

    if isinstance(left, (list, tuple)):
        if len(left) != len(right):
            if append_difference(
                differences,
                maximum,
                path,
                f"Longueur différente ({len(left)} / {len(right)})",
                len(left),
                len(right),
            ):
                return
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            compare_values(left_item, right_item, f"{path}[{index}]", differences, maximum)
            if len(differences) >= maximum:
                return
        return

    if left != right:
        append_difference(differences, maximum, path, "Valeur différente", left, right)


def preview(value: Any, maximum_length: int = 180) -> str:
    displayed = repr(value)
    if len(displayed) > maximum_length:
        return f"{displayed[: maximum_length - 3]}..."
    return displayed


def write_report(
    left_path: Path,
    left_kind: str,
    right_path: Path,
    right_kind: str,
    differences: list[Difference],
    maximum: int,
) -> None:
    print("Comparaison de bibliothèques normalisées")
    print(f"- Gauche : {display_path(left_path)} ({left_kind})")
    print(f"- Droite : {display_path(right_path)} ({right_kind})")
    print(
        "- Normalisation : décodage YAML, Unicode NFC, espaces de fin, "
        "fins de ligne et lignes de continuation, ordre des clés"
    )

    if not differences:
        print("\n✅ Contenu et structure identiques après normalisation.")
        return

    print(f"\n❌ {len(differences)} divergence(s) affichée(s).")
    if len(differences) >= maximum:
        print(f"La limite de {maximum} divergences est atteinte.")
    for difference in differences:
        print(f"\n- {difference.path} — {difference.reason}")
        print(f"  gauche : {preview(difference.left)}")
        print(f"  droite : {preview(difference.right)}")


def main() -> int:
    arguments = parse_arguments()
    if arguments.max_differences < 1:
        print("Erreur : --max-differences doit être supérieur à 0.", file=sys.stderr)
        return 2

    try:
        left_data, left_kind = load_source(arguments.left.resolve(), arguments.compat)
        right_data, right_kind = load_source(arguments.right.resolve(), arguments.compat)
        normalised_left = normalise_data(
            left_data, arguments.include_converter_metadata
        )
        normalised_right = normalise_data(
            right_data, arguments.include_converter_metadata
        )
    except ValueError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 2

    differences: list[Difference] = []
    compare_values(normalised_left, normalised_right, "$", differences, arguments.max_differences)
    write_report(
        arguments.left,
        left_kind,
        arguments.right,
        right_kind,
        differences,
        arguments.max_differences,
    )
    return 1 if arguments.fail_on_difference and differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
