#!/usr/bin/env python3
"""Compare les bibliothèques Excel des outils avec les bibliothèques YAML.

Le script cherche récursivement les fichiers Excel OpenXML dans ``tools`` et les
fichiers YAML dans ``backend/library/libraries``. Une paire directe est valide
lorsque les deux fichiers ont le même nom (sans extension), une seule fois de
chaque côté. Les fichiers sans paire de nom reçoivent ensuite une suggestion
fondée exclusivement sur l'URN de leur bibliothèque.

Usage courant depuis la racine de ciso-assistant-community :

    python tools/check_excel_yaml_library_consistency.py

Le rapport est affiché dans le terminal et écrit, par défaut, dans
``tools/excel_yaml_library_consistency_report.md``.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import yaml
from openpyxl import load_workbook


EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm"}
YAML_EXTENSIONS = {".yaml", ".yml"}
EXPECTED_UNPAIRED_PREFIXES = ("workflow-", "preset-")
ROOT_METADATA_PATTERN = re.compile(r"^(?P<key>urn|version)\s*:\s*(?P<value>.*)$")
ROOT_OBJECTS_PATTERN = re.compile(r"^objects\s*:")
MARKDOWN_LINK_PATTERN = re.compile(r"\[`(?P<label>[^`]+)`\]\([^)]*\)")
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
DEFAULT_TOOLS_DIR = SCRIPT_PATH.parent
DEFAULT_LIBRARIES_DIR = PROJECT_ROOT / "backend" / "library" / "libraries"
DEFAULT_REPORT_PATH = SCRIPT_PATH.parent / "excel_yaml_library_consistency_report.md"


@dataclass(frozen=True)
class LibraryFile:
    """Informations minimales nécessaires pour comparer une bibliothèque."""

    path: Path
    relative_path: str
    name_key: str
    urn: str | None
    version: str | None
    urn_error: str | None


@dataclass(frozen=True)
class DirectPairUrnIssue:
    """Une paire de fichiers de même nom dont les URN ne confirment pas le lien."""

    excel: LibraryFile
    yaml_file: LibraryFile
    reason: str


@dataclass(frozen=True)
class DirectPairVersionIssue:
    """Une paire de fichiers de même nom dont les versions divergent."""

    excel: LibraryFile
    yaml_file: LibraryFile


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare les noms de fichiers Excel et YAML de bibliothèques, puis "
            "suggère les associations par URN."
        )
    )
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=DEFAULT_TOOLS_DIR,
        help=f"Dossier à parcourir pour les Excel (défaut : {DEFAULT_TOOLS_DIR})",
    )
    parser.add_argument(
        "--libraries-dir",
        type=Path,
        default=DEFAULT_LIBRARIES_DIR,
        help=(
            "Dossier à parcourir pour les YAML "
            f"(défaut : {DEFAULT_LIBRARIES_DIR})"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Fichier Markdown à générer (défaut : {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--fail-on-inconsistency",
        action="store_true",
        help=(
            "Retourne le code 1 si le rapport contient une absence, un conflit "
            "de nom ou une incohérence d'URN. Utile en CI."
        ),
    )
    return parser.parse_args()


def display_path(path: Path, project_root: Path) -> str:
    """Retourne un chemin portable, relatif au projet quand cela est possible."""

    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def normalise_name(path: Path) -> str:
    """Normalise seulement la casse : les noms doivent rester explicitement égaux."""

    return path.stem.casefold()


def clean_cell_value(value: object) -> str | None:
    if value is None:
        return None
    value_as_text = str(value).strip()
    return value_as_text or None


def extract_excel_library_metadata(path: Path) -> tuple[str | None, str | None, str | None]:
    """Lit l'URN et la version dans la feuille ``library_meta`` d'un Excel."""

    try:
        workbook = load_workbook(
            path,
            read_only=True,
            data_only=True,
            keep_links=False,
        )
    except Exception as error:  # openpyxl expose plusieurs exceptions possibles.
        return None, None, f"Impossible de lire le classeur : {error}"

    try:
        if "library_meta" not in workbook.sheetnames:
            return None, None, "Feuille 'library_meta' absente"

        worksheet = workbook["library_meta"]
        metadata: dict[str, str] = {}
        for row in worksheet.iter_rows(values_only=True):
            if len(row) < 2:
                continue
            key = clean_cell_value(row[0])
            value = clean_cell_value(row[1])
            if key is not None and key.casefold() in {"urn", "version"} and value is not None:
                metadata[key.casefold()] = value

        urn = metadata.get("urn")
        if urn is None:
            return None, metadata.get("version"), "Clé 'urn' absente de la feuille 'library_meta'"
        return urn, metadata.get("version"), None
    except Exception as error:
        return None, None, f"Impossible de lire la feuille 'library_meta' : {error}"
    finally:
        workbook.close()


def extract_yaml_library_metadata(path: Path) -> tuple[str | None, str | None, str | None]:
    """Lit l'URN et la version sans désérialiser les objets volumineux du YAML."""

    try:
        # Toutes les bibliothèques du dépôt placent cette métadonnée de premier
        # niveau avant ``objects:``. Lire seulement cette partie rend le contrôle
        # très nettement plus rapide pour les YAML de plusieurs mégaoctets.
        with path.open("r", encoding="utf-8-sig") as yaml_file:
            metadata: dict[str, str] = {}
            for line in yaml_file:
                if ROOT_OBJECTS_PATTERN.match(line):
                    break

                metadata_match = ROOT_METADATA_PATTERN.match(line)
                if metadata_match is None:
                    continue

                try:
                    # PyYAML décode correctement les valeurs simples, les
                    # guillemets et les commentaires sans charger le document.
                    value = clean_cell_value(yaml.safe_load(metadata_match.group("value")))
                except yaml.YAMLError as error:
                    return None, None, f"Valeur YAML invalide : {error}"

                if value is not None:
                    metadata[metadata_match.group("key")] = value

                if "urn" in metadata and "version" in metadata:
                    return metadata["urn"], metadata["version"], None
    except OSError as error:
        return None, None, f"Impossible de lire le YAML : {error}"

    urn = metadata.get("urn")
    if urn is None:
        return None, metadata.get("version"), "Clé 'urn' absente à la racine du YAML"
    return urn, metadata.get("version"), None


def iter_library_paths(directory: Path, extensions: set[str]) -> Iterable[Path]:
    """Parcourt les fichiers utiles sans inclure les fichiers temporaires d'Excel."""

    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if (
            path.is_file()
            and path.suffix.casefold() in extensions
            and not path.name.startswith("~$")
        ):
            yield path


def collect_excel_files(directory: Path, project_root: Path) -> list[LibraryFile]:
    return [
        LibraryFile(
            path=path,
            relative_path=display_path(path, project_root),
            name_key=normalise_name(path),
            urn=urn,
            version=version,
            urn_error=error,
        )
        for path in iter_library_paths(directory, EXCEL_EXTENSIONS)
        for urn, version, error in [extract_excel_library_metadata(path)]
    ]


def collect_yaml_files(directory: Path, project_root: Path) -> list[LibraryFile]:
    return [
        LibraryFile(
            path=path,
            relative_path=display_path(path, project_root),
            name_key=normalise_name(path),
            urn=urn,
            version=version,
            urn_error=error,
        )
        for path in iter_library_paths(directory, YAML_EXTENSIONS)
        for urn, version, error in [extract_yaml_library_metadata(path)]
    ]


def group_by_name(files: Iterable[LibraryFile]) -> dict[str, list[LibraryFile]]:
    grouped: dict[str, list[LibraryFile]] = defaultdict(list)
    for library_file in files:
        grouped[library_file.name_key].append(library_file)
    return dict(grouped)


def group_by_urn(files: Iterable[LibraryFile]) -> dict[str, list[LibraryFile]]:
    grouped: dict[str, list[LibraryFile]] = defaultdict(list)
    for library_file in files:
        if library_file.urn is not None:
            grouped[library_file.urn].append(library_file)
    return dict(grouped)


def is_direct_pair(
    excel_files: list[LibraryFile], yaml_files: list[LibraryFile]
) -> bool:
    return len(excel_files) == 1 and len(yaml_files) == 1


def markdown_file_link(library_file: LibraryFile, report_path: Path) -> str:
    """Crée un lien Markdown relatif au rapport tout en gardant son libellé projet."""

    try:
        target = os.path.relpath(library_file.path, start=report_path.parent)
        target_url = quote(Path(target).as_posix(), safe="/.-_~")
    except ValueError:
        # Un chemin personnalisé sur un autre volume Windows ne peut pas être
        # relatif au rapport. L'URI file reste alors directement utilisable.
        target_url = library_file.path.as_uri()
    return f"[`{library_file.relative_path}`]({target_url})"


def markdown_path_list(files: Iterable[LibraryFile], report_path: Path) -> list[str]:
    return [f"- {markdown_file_link(library_file, report_path)}" for library_file in files]


def association_prefix(
    candidates: list[LibraryFile], valid_target_paths: set[Path]
) -> str:
    """Construit le préfixe demandé pour une association estimée par URN."""

    icons: list[str] = []
    if len(candidates) > 1:
        icons.append("⚠️")
    if any(candidate.path in valid_target_paths for candidate in candidates):
        icons.append("❌")
    return " ".join(icons) if icons else "✅"


def format_urn(urn: str | None, urn_error: str | None) -> str:
    if urn is not None:
        return f"URN : `{urn}`"
    return f"URN indisponible : {urn_error or 'raison inconnue'}"


def format_version(version: str | None) -> str:
    return f"`{version}`" if version is not None else "absente"


def is_expected_unpaired_file(library_file: LibraryFile) -> bool:
    """Indique les YAML/Excel sans équivalent attendus par convention de nom."""

    return library_file.name_key.startswith(EXPECTED_UNPAIRED_PREFIXES)


def append_estimated_associations(
    lines: list[str],
    source_files: list[LibraryFile],
    candidates_by_urn: dict[str, list[LibraryFile]],
    valid_target_paths: set[Path],
    arrow: str,
    report_path: Path,
) -> list[LibraryFile]:
    """Ajoute les associations par URN et retourne les sources sans candidat."""

    no_association: list[LibraryFile] = []
    for source in source_files:
        candidates = candidates_by_urn.get(source.urn, []) if source.urn else []
        if not candidates:
            no_association.append(source)
            continue

        prefix = association_prefix(candidates, valid_target_paths)
        targets = ", ".join(markdown_file_link(item, report_path) for item in candidates)
        lines.append(
            f"- {prefix} {markdown_file_link(source, report_path)} {arrow} {targets} "
            f"({format_urn(source.urn, source.urn_error)})"
        )
    return no_association


def build_report(
    excel_files: list[LibraryFile],
    yaml_files: list[LibraryFile],
    tools_dir: Path,
    libraries_dir: Path,
    project_root: Path,
    report_path: Path,
) -> tuple[str, bool]:
    excel_by_name = group_by_name(excel_files)
    yaml_by_name = group_by_name(yaml_files)
    all_name_keys = sorted(set(excel_by_name) | set(yaml_by_name))

    direct_pairs: list[tuple[LibraryFile, LibraryFile]] = []
    name_collisions: list[tuple[str, list[LibraryFile], list[LibraryFile]]] = []
    for name_key in all_name_keys:
        matching_excels = excel_by_name.get(name_key, [])
        matching_yamls = yaml_by_name.get(name_key, [])
        if matching_excels and matching_yamls:
            if is_direct_pair(matching_excels, matching_yamls):
                direct_pairs.append((matching_excels[0], matching_yamls[0]))
            else:
                name_collisions.append((name_key, matching_excels, matching_yamls))

    excel_without_name_pair = [
        item for item in excel_files if item.name_key not in yaml_by_name
    ]
    yaml_without_name_pair = [
        item for item in yaml_files if item.name_key not in excel_by_name
    ]

    valid_excel_paths = {excel.path for excel, _ in direct_pairs}
    valid_yaml_paths = {yaml_file.path for _, yaml_file in direct_pairs}
    direct_pair_urn_issues: list[DirectPairUrnIssue] = []
    direct_pair_version_issues: list[DirectPairVersionIssue] = []
    confirmed_urn_pairs = 0
    for excel, yaml_file in direct_pairs:
        if excel.urn is None or yaml_file.urn is None:
            reason = (
                f"Excel : {format_urn(excel.urn, excel.urn_error)}. "
                f"YAML : {format_urn(yaml_file.urn, yaml_file.urn_error)}."
            )
            direct_pair_urn_issues.append(DirectPairUrnIssue(excel, yaml_file, reason))
        elif excel.urn != yaml_file.urn:
            reason = f"URN Excel : `{excel.urn}` ; URN YAML : `{yaml_file.urn}`."
            direct_pair_urn_issues.append(DirectPairUrnIssue(excel, yaml_file, reason))
        else:
            confirmed_urn_pairs += 1

        if excel.version != yaml_file.version:
            direct_pair_version_issues.append(DirectPairVersionIssue(excel, yaml_file))

    yaml_by_urn = group_by_urn(yaml_files)
    excel_by_urn = group_by_urn(excel_files)
    no_association_excel_files = [
        item
        for item in excel_without_name_pair
        if item.urn is None or not yaml_by_urn.get(item.urn)
    ]
    no_association_yaml_files = [
        item
        for item in yaml_without_name_pair
        if item.urn is None or not excel_by_urn.get(item.urn)
    ]
    expected_no_association_excel = [
        item
        for item in no_association_excel_files
        if is_expected_unpaired_file(item)
    ]
    expected_no_association_yaml = [
        item
        for item in no_association_yaml_files
        if is_expected_unpaired_file(item)
    ]
    unexpected_excel_without_name_pair = [
        item for item in excel_without_name_pair if item not in expected_no_association_excel
    ]
    unexpected_yaml_without_name_pair = [
        item for item in yaml_without_name_pair if item not in expected_no_association_yaml
    ]

    lines = [
        "# Rapport de cohérence Excel / YAML des bibliothèques",
        "",
        "Les chemins ci-dessous sont relatifs à la racine du projet. Une paire "
        "directe est valide si le nom de fichier sans extension est identique et "
        "unique de chaque côté (comparaison insensible à la casse).",
        "",
        "## Périmètre",
        "",
        f"- Excel : `{display_path(tools_dir, project_root)}` (récursif)",
        f"- YAML : `{display_path(libraries_dir, project_root)}` (récursif)",
        "",
        "## Résumé",
        "",
        f"- Fichiers Excel analysés : **{len(excel_files)}**",
        f"- Fichiers YAML analysés : **{len(yaml_files)}**",
        f"- Paires Excel-YAML valides par nom : **{len(direct_pairs)}**",
        f"- Paires valides également confirmées par URN : **{confirmed_urn_pairs}**",
        f"- Paires directes dont la version diverge : **{len(direct_pair_version_issues)}**",
        (
            "- Excel sans YAML du même nom, hors exceptions workflow-/preset- : "
            f"**{len(unexpected_excel_without_name_pair)}**"
        ),
        (
            "- YAML sans Excel du même nom, hors exceptions workflow-/preset- : "
            f"**{len(unexpected_yaml_without_name_pair)}**"
        ),
        (
            "- Fichiers workflow-/preset- sans association attendus : "
            f"**{len(expected_no_association_excel) + len(expected_no_association_yaml)}**"
        ),
        f"- Conflits de noms non 1:1 : **{len(name_collisions)}**",
        "",
        "## Excel sans YAML du même nom (hors exceptions workflow-/preset-)",
        "",
    ]
    lines.extend(
        markdown_path_list(unexpected_excel_without_name_pair, report_path) or ["Aucun."]
    )

    lines.extend(["", "## YAML sans Excel du même nom (hors exceptions workflow-/preset-)", ""])
    lines.extend(
        markdown_path_list(unexpected_yaml_without_name_pair, report_path) or ["Aucun."]
    )

    lines.extend(["", "## Associations estimées par URN — Excel sans paire de nom", ""])
    no_association_excel = append_estimated_associations(
        lines,
        unexpected_excel_without_name_pair,
        yaml_by_urn,
        valid_yaml_paths,
        "→",
        report_path,
    )
    if len(no_association_excel) == len(unexpected_excel_without_name_pair):
        lines.append("Aucune association estimée.")

    lines.extend(["", "## Associations estimées par URN — YAML sans paire de nom", ""])
    no_association_yaml = append_estimated_associations(
        lines,
        unexpected_yaml_without_name_pair,
        excel_by_urn,
        valid_excel_paths,
        "→",
        report_path,
    )
    if len(no_association_yaml) == len(unexpected_yaml_without_name_pair):
        lines.append("Aucune association estimée.")

    lines.extend(["", "## Excel sans aucune association estimée", ""])
    if no_association_excel:
        for excel in no_association_excel:
            lines.append(
                f"- ❔ {markdown_file_link(excel, report_path)} "
                f"({format_urn(excel.urn, excel.urn_error)})"
            )
    else:
        lines.append("Aucun.")

    lines.extend(
        [
            "",
            "## Excel workflow-/preset- sans association (attendus)",
            "",
        ]
    )
    lines.extend(
        markdown_path_list(expected_no_association_excel, report_path) or ["Aucun."]
    )

    lines.extend(
        [
            "",
            "## YAML workflow-/preset- sans association (attendus)",
            "",
        ]
    )
    lines.extend(
        markdown_path_list(expected_no_association_yaml, report_path) or ["Aucun."]
    )

    lines.extend(["", "## YAML sans aucune association estimée", ""])
    if no_association_yaml:
        for yaml_file in no_association_yaml:
            lines.append(
                f"- ❔ {markdown_file_link(yaml_file, report_path)} "
                f"({format_urn(yaml_file.urn, yaml_file.urn_error)})"
            )
    else:
        lines.append("Aucun.")

    lines.extend(["", "## Conflits de noms (non considérés comme des paires valides)", ""])
    if name_collisions:
        for name_key, matching_excels, matching_yamls in name_collisions:
            lines.append(f"### Nom normalisé : `{name_key}`")
            lines.append("")
            lines.append("Excel :")
            lines.extend(markdown_path_list(matching_excels, report_path))
            lines.append("YAML :")
            lines.extend(markdown_path_list(matching_yamls, report_path))
            lines.append("")
    else:
        lines.append("Aucun.")

    lines.extend(["", "## Paires directes dont l'URN ne confirme pas le lien", ""])
    if direct_pair_urn_issues:
        for issue in direct_pair_urn_issues:
            lines.append(
                f"- ⚠️ {markdown_file_link(issue.excel, report_path)} ↔ "
                f"{markdown_file_link(issue.yaml_file, report_path)} — {issue.reason}"
            )
    else:
        lines.append("Aucune.")

    lines.extend(["", "## Paires directes dont la version diverge", ""])
    if direct_pair_version_issues:
        for issue in direct_pair_version_issues:
            lines.append(
                f"- ⚠️ {markdown_file_link(issue.excel, report_path)} ↔ "
                f"{markdown_file_link(issue.yaml_file, report_path)} — "
                f"version Excel : {format_version(issue.excel.version)} ; "
                f"version YAML : {format_version(issue.yaml_file.version)}."
            )
    else:
        lines.append("Aucune.")

    urn_errors = [item for item in [*excel_files, *yaml_files] if item.urn_error]
    lines.extend(["", "## Fichiers dont l'URN est illisible ou absente", ""])
    if urn_errors:
        for item in urn_errors:
            lines.append(
                f"- ⚠️ {markdown_file_link(item, report_path)} — {item.urn_error}"
            )
    else:
        lines.append("Aucun.")

    has_inconsistency = bool(
        unexpected_excel_without_name_pair
        or unexpected_yaml_without_name_pair
        or name_collisions
        or direct_pair_urn_issues
        or direct_pair_version_issues
        or urn_errors
    )
    return "\n".join(lines) + "\n", has_inconsistency


def report_for_console(markdown_report: str) -> str:
    """Retire les cibles des liens pour conserver des chemins lisibles au terminal."""

    return MARKDOWN_LINK_PATTERN.sub(lambda match: f"`{match.group('label')}`", markdown_report)


def main() -> int:
    arguments = parse_arguments()
    tools_dir = arguments.tools_dir.resolve()
    libraries_dir = arguments.libraries_dir.resolve()
    output_path = arguments.output.resolve()

    missing_directories = [
        directory
        for directory in (tools_dir, libraries_dir)
        if not directory.is_dir()
    ]
    if missing_directories:
        for directory in missing_directories:
            print(f"Erreur : le dossier n'existe pas : {directory}", file=sys.stderr)
        return 2

    project_root = PROJECT_ROOT
    excel_files = collect_excel_files(tools_dir, project_root)
    yaml_files = collect_yaml_files(libraries_dir, project_root)
    report, has_inconsistency = build_report(
        excel_files,
        yaml_files,
        tools_dir,
        libraries_dir,
        project_root,
        output_path,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(report_for_console(report), end="")
    print(f"Rapport Markdown écrit dans : {display_path(output_path, project_root)}")

    if arguments.fail_on_inconsistency and has_inconsistency:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
