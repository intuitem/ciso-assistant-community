#!/usr/bin/env python3
"""Compare Excel libraries in tools with YAML libraries.

The script recursively finds OpenXML Excel files in ``tools`` and YAML files in
``backend/library/libraries``. A direct pair is valid when both files have the
same name (without the extension) and there is exactly one file on each side.
Files without a name-based pair then receive a suggestion based exclusively on
their library URN.

Typical usage from the ciso-assistant-community root:

    python tools/check_excel_yaml_library_consistency.py

The report is printed to the terminal and written by default to
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
PROJECT_ROOT = SCRIPT_PATH.parents[2]
DEFAULT_TOOLS_DIR = PROJECT_ROOT / "tools"
DEFAULT_LIBRARIES_DIR = PROJECT_ROOT / "backend" / "library" / "libraries"
DEFAULT_REPORT_PATH = SCRIPT_PATH.parent / "excel_yaml_library_consistency_report.md"


@dataclass(frozen=True)
class LibraryFile:
    """Minimum information required to compare a library."""

    path: Path
    relative_path: str
    name_key: str
    urn: str | None
    version: str | None
    urn_error: str | None


@dataclass(frozen=True)
class DirectPairUrnIssue:
    """A same-name file pair whose URNs do not confirm the relationship."""

    excel: LibraryFile
    yaml_file: LibraryFile
    reason: str


@dataclass(frozen=True)
class DirectPairVersionIssue:
    """A same-name file pair whose versions differ."""

    excel: LibraryFile
    yaml_file: LibraryFile


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Excel and YAML library filenames, then suggest matches by URN."
        )
    )
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=DEFAULT_TOOLS_DIR,
        help=f"Directory to scan for Excel files (default: {DEFAULT_TOOLS_DIR})",
    )
    parser.add_argument(
        "--libraries-dir",
        type=Path,
        default=DEFAULT_LIBRARIES_DIR,
        help=(
            "Directory to scan for YAML files "
            f"(default: {DEFAULT_LIBRARIES_DIR})"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Markdown report to generate (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--fail-on-inconsistency",
        action="store_true",
        help=(
            "Return exit code 1 when the report contains a missing match, filename "
            "collision, URN inconsistency, or version mismatch. Useful in CI."
        ),
    )
    return parser.parse_args()


def display_path(path: Path, project_root: Path) -> str:
    """Return a portable path relative to the project whenever possible."""

    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def normalize_name(path: Path) -> str:
    """Normalize case only: filenames must otherwise remain explicitly identical."""

    return path.stem.casefold()


def clean_cell_value(value: object) -> str | None:
    if value is None:
        return None
    value_as_text = str(value).strip()
    return value_as_text or None


def extract_excel_library_metadata(path: Path) -> tuple[str | None, str | None, str | None]:
    """Read the URN and version from an Excel ``library_meta`` sheet."""

    try:
        workbook = load_workbook(
            path,
            read_only=True,
            data_only=True,
            keep_links=False,
        )
    except Exception as error:  # openpyxl can raise several exception types.
        return None, None, f"Unable to read workbook: {error}"

    try:
        if "library_meta" not in workbook.sheetnames:
            return None, None, "Missing 'library_meta' sheet"

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
            return None, metadata.get("version"), "Missing 'urn' key in the 'library_meta' sheet"
        return urn, metadata.get("version"), None
    except Exception as error:
        return None, None, f"Unable to read 'library_meta' sheet: {error}"
    finally:
        workbook.close()


def extract_yaml_library_metadata(path: Path) -> tuple[str | None, str | None, str | None]:
    """Read the URN and version without deserializing large YAML objects."""

    try:
        # All repository libraries keep this top-level metadata before
        # ``objects:``. Reading only this section is much faster for multi-MB YAML.
        with path.open("r", encoding="utf-8-sig") as yaml_file:
            metadata: dict[str, str] = {}
            for line in yaml_file:
                if ROOT_OBJECTS_PATTERN.match(line):
                    break

                metadata_match = ROOT_METADATA_PATTERN.match(line)
                if metadata_match is None:
                    continue

                try:
                    # PyYAML correctly decodes simple values, quotes, and comments
                    # without loading the complete document.
                    value = clean_cell_value(yaml.safe_load(metadata_match.group("value")))
                except yaml.YAMLError as error:
                    return None, None, f"Invalid YAML value: {error}"

                if value is not None:
                    metadata[metadata_match.group("key")] = value

                if "urn" in metadata and "version" in metadata:
                    return metadata["urn"], metadata["version"], None
    except OSError as error:
        return None, None, f"Unable to read YAML: {error}"

    urn = metadata.get("urn")
    if urn is None:
        return None, metadata.get("version"), "Missing 'urn' key at the YAML root"
    return urn, metadata.get("version"), None


def iter_library_paths(directory: Path, extensions: set[str]) -> Iterable[Path]:
    """Iterate over relevant files while excluding temporary Excel files."""

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
            name_key=normalize_name(path),
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
            name_key=normalize_name(path),
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
    """Create a report-relative Markdown link while retaining its project label."""

    try:
        target = os.path.relpath(library_file.path, start=report_path.parent)
        target_url = quote(Path(target).as_posix(), safe="/.-_~")
    except ValueError:
        # A custom path on another Windows volume cannot be report-relative.
        # Its file URI remains directly usable instead.
        target_url = library_file.path.as_uri()
    return f"[`{library_file.relative_path}`]({target_url})"


def markdown_path_list(files: Iterable[LibraryFile], report_path: Path) -> list[str]:
    return [f"- {markdown_file_link(library_file, report_path)}" for library_file in files]


def association_prefix(
    candidates: list[LibraryFile], valid_target_paths: set[Path]
) -> str:
    """Build the requested prefix for a URN-based estimated association."""

    icons: list[str] = []
    if len(candidates) > 1:
        icons.append("⚠️")
    if any(candidate.path in valid_target_paths for candidate in candidates):
        icons.append("❌")
    return " ".join(icons) if icons else "✅"


def format_urn(urn: str | None, urn_error: str | None) -> str:
    if urn is not None:
        return f"URN: `{urn}`"
    return f"URN unavailable: {urn_error or 'unknown reason'}"


def format_version(version: str | None) -> str:
    return f"`{version}`" if version is not None else "missing"


def is_expected_unpaired_file(library_file: LibraryFile) -> bool:
    """Identify expected unmatched YAML/Excel files by filename convention."""

    return library_file.name_key.startswith(EXPECTED_UNPAIRED_PREFIXES)


def append_estimated_associations(
    lines: list[str],
    source_files: list[LibraryFile],
    candidates_by_urn: dict[str, list[LibraryFile]],
    valid_target_paths: set[Path],
    arrow: str,
    report_path: Path,
) -> list[LibraryFile]:
    """Add URN-based associations and return source files without candidates."""

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
                f"Excel: {format_urn(excel.urn, excel.urn_error)}. "
                f"YAML: {format_urn(yaml_file.urn, yaml_file.urn_error)}."
            )
            direct_pair_urn_issues.append(DirectPairUrnIssue(excel, yaml_file, reason))
        elif excel.urn != yaml_file.urn:
            reason = f"Excel URN: `{excel.urn}`; YAML URN: `{yaml_file.urn}`."
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
        "# Excel / YAML Library Consistency Report",
        "",
        "The paths below are relative to the project root. A direct pair is valid "
        "when its extensionless filename is identical and unique on each side "
        "(case-insensitive comparison).",
        "",
        "## Scope",
        "",
        f"- Excel: `{display_path(tools_dir, project_root)}` (recursive)",
        f"- YAML: `{display_path(libraries_dir, project_root)}` (recursive)",
        "",
        "## Summary",
        "",
        f"- Excel files analyzed: **{len(excel_files)}**",
        f"- YAML files analyzed: **{len(yaml_files)}**",
        f"- Valid Excel-YAML pairs by name: **{len(direct_pairs)}**",
        f"- Valid pairs also confirmed by URN: **{confirmed_urn_pairs}**",
        f"- Direct pairs with version mismatches: **{len(direct_pair_version_issues)}**",
        (
            "- Excel files without same-name YAML, excluding workflow-/preset- exceptions: "
            f"**{len(unexpected_excel_without_name_pair)}**"
        ),
        (
            "- YAML files without same-name Excel, excluding workflow-/preset- exceptions: "
            f"**{len(unexpected_yaml_without_name_pair)}**"
        ),
        (
            "- Expected unmatched workflow-/preset- files: "
            f"**{len(expected_no_association_excel) + len(expected_no_association_yaml)}**"
        ),
        f"- Non-1:1 filename collisions: **{len(name_collisions)}**",
        "",
        "## Excel without same-name YAML (excluding workflow-/preset- exceptions)",
        "",
    ]
    lines.extend(
        markdown_path_list(unexpected_excel_without_name_pair, report_path) or ["None."]
    )

    lines.extend(["", "## YAML without same-name Excel (excluding workflow-/preset- exceptions)", ""])
    lines.extend(
        markdown_path_list(unexpected_yaml_without_name_pair, report_path) or ["None."]
    )

    lines.extend(["", "## URN-based estimated associations — Excel without name pair", ""])
    no_association_excel = append_estimated_associations(
        lines,
        unexpected_excel_without_name_pair,
        yaml_by_urn,
        valid_yaml_paths,
        "→",
        report_path,
    )
    if len(no_association_excel) == len(unexpected_excel_without_name_pair):
        lines.append("No estimated associations.")

    lines.extend(["", "## URN-based estimated associations — YAML without name pair", ""])
    no_association_yaml = append_estimated_associations(
        lines,
        unexpected_yaml_without_name_pair,
        excel_by_urn,
        valid_excel_paths,
        "→",
        report_path,
    )
    if len(no_association_yaml) == len(unexpected_yaml_without_name_pair):
        lines.append("No estimated associations.")

    lines.extend(["", "## Excel without any estimated association", ""])
    if no_association_excel:
        for excel in no_association_excel:
            lines.append(
                f"- ❔ {markdown_file_link(excel, report_path)} "
                f"({format_urn(excel.urn, excel.urn_error)})"
            )
    else:
        lines.append("None.")

    lines.extend(
        [
            "",
            "## Expected unmatched workflow-/preset- Excel files",
            "",
        ]
    )
    lines.extend(
        markdown_path_list(expected_no_association_excel, report_path) or ["None."]
    )

    lines.extend(
        [
            "",
            "## Expected unmatched workflow-/preset- YAML files",
            "",
        ]
    )
    lines.extend(
        markdown_path_list(expected_no_association_yaml, report_path) or ["None."]
    )

    lines.extend(["", "## YAML without any estimated association", ""])
    if no_association_yaml:
        for yaml_file in no_association_yaml:
            lines.append(
                f"- ❔ {markdown_file_link(yaml_file, report_path)} "
                f"({format_urn(yaml_file.urn, yaml_file.urn_error)})"
            )
    else:
        lines.append("None.")

    lines.extend(["", "## Filename collisions (not considered valid pairs)", ""])
    if name_collisions:
        for name_key, matching_excels, matching_yamls in name_collisions:
            lines.append(f"### Normalized name: `{name_key}`")
            lines.append("")
            lines.append("Excel:")
            lines.extend(markdown_path_list(matching_excels, report_path))
            lines.append("YAML:")
            lines.extend(markdown_path_list(matching_yamls, report_path))
            lines.append("")
    else:
        lines.append("None.")

    lines.extend(["", "## Direct pairs whose URN does not confirm the relationship", ""])
    if direct_pair_urn_issues:
        for issue in direct_pair_urn_issues:
            lines.append(
                f"- ⚠️ {markdown_file_link(issue.excel, report_path)} ↔ "
                f"{markdown_file_link(issue.yaml_file, report_path)} — {issue.reason}"
            )
    else:
        lines.append("None.")

    lines.extend(["", "## Direct pairs with version mismatches", ""])
    if direct_pair_version_issues:
        for issue in direct_pair_version_issues:
            lines.append(
                f"- ⚠️ {markdown_file_link(issue.excel, report_path)} ↔ "
                f"{markdown_file_link(issue.yaml_file, report_path)} — "
                f"Excel version: {format_version(issue.excel.version)}; "
                f"YAML version: {format_version(issue.yaml_file.version)}."
            )
    else:
        lines.append("None.")

    urn_errors = [item for item in [*excel_files, *yaml_files] if item.urn_error]
    lines.extend(["", "## Files with unreadable or missing URN", ""])
    if urn_errors:
        for item in urn_errors:
            lines.append(
                f"- ⚠️ {markdown_file_link(item, report_path)} — {item.urn_error}"
            )
    else:
        lines.append("None.")

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
    """Remove link targets to keep paths readable in the terminal."""

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
            print(f"Error: directory does not exist: {directory}", file=sys.stderr)
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
    print(f"Markdown report written to: {display_path(output_path, project_root)}")

    if arguments.fail_on_inconsistency and has_inconsistency:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
