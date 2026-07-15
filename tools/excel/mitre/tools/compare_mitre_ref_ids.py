#!/usr/bin/env python3
"""Compare MITRE ATT&CK ref_id values between two CISO Assistant libraries."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import sys
from typing import Any

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
COMMUNITY_ROOT = SCRIPT_DIR.parents[3]
DEFAULT_ORIGINAL = (
    COMMUNITY_ROOT / "backend" / "library" / "libraries" / "mitre-attack.yaml"
)
DEFAULT_NEW = SCRIPT_DIR / "mitre-attack.yaml"
SECTIONS = ("reference_controls", "threats")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare ref_id values from objects.reference_controls and "
            "objects.threats between two MITRE ATT&CK YAML libraries."
        )
    )
    parser.add_argument(
        "--original",
        type=Path,
        default=DEFAULT_ORIGINAL,
        help=f"original YAML file (default: {DEFAULT_ORIGINAL})",
    )
    parser.add_argument(
        "--new",
        type=Path,
        default=DEFAULT_NEW,
        help=f"new YAML file (default: {DEFAULT_NEW})",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"File not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"The YAML root in {path} must be a mapping.")
    if not isinstance(data.get("objects"), dict):
        raise ValueError(f"The 'objects' key is missing or invalid in {path}.")

    return data


def extract_ref_ids_and_names(
    data: dict[str, Any], section: str, path: Path
) -> tuple[list[str], dict[str, str]]:
    entries = data["objects"].get(section)
    if not isinstance(entries, list):
        raise ValueError(
            f"The 'objects.{section}' key is missing or is not a list in {path}."
        )

    ref_ids: list[str] = []
    names_by_ref_id: dict[str, str] = {}
    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(
                f"Item {position} in 'objects.{section}' is not a mapping in {path}."
            )

        ref_id = entry.get("ref_id")
        if not isinstance(ref_id, str) or not ref_id.strip():
            raise ValueError(
                f"The ref_id for item {position} in 'objects.{section}' "
                f"is missing or invalid in {path}."
            )

        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"The name for item {position} in 'objects.{section}' "
                f"is missing or invalid in {path}."
            )

        clean_ref_id = ref_id.strip()
        ref_ids.append(clean_ref_id)
        names_by_ref_id.setdefault(clean_ref_id, name.strip())

    return ref_ids, names_by_ref_id


def natural_sort_key(value: str) -> tuple[tuple[int, int | str], ...]:
    """Sort identifiers naturally, for example T1001.2 before T1001.10."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", value)
        if part
    )


def format_changes(
    label: str, values: set[str], names_by_ref_id: dict[str, str], marker: str
) -> None:
    print(f"  {label} ({len(values)}):")
    if not values:
        print("    None")
        return

    max_ref_id_length = max(len(ref_id) for ref_id in values)
    for ref_id in sorted(values, key=natural_sort_key):
        spacing = " " * (max_ref_id_length - len(ref_id) + 1)
        print(f"    {marker} [{ref_id}]{spacing}{names_by_ref_id[ref_id]}")


def duplicate_ref_ids(values: list[str]) -> set[str]:
    return {ref_id for ref_id, count in Counter(values).items() if count > 1}


def main() -> int:
    args = parse_args()
    original_path = args.original.resolve()
    new_path = args.new.resolve()

    try:
        original_data = load_yaml(original_path)
        new_data = load_yaml(new_path)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Original: {original_path}")
    print(f"New:      {new_path}")

    for section in SECTIONS:
        try:
            original_values, original_names = extract_ref_ids_and_names(
                original_data, section, original_path
            )
            new_values, new_names = extract_ref_ids_and_names(
                new_data, section, new_path
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

        original_ids = set(original_values)
        new_ids = set(new_values)
        added = new_ids - original_ids
        removed = original_ids - new_ids

        print(f"\n{section}")
        print(
            f"  Totals: {len(original_ids)} in the original, "
            f"{len(new_ids)} in the new file"
        )
        format_changes("Added", added, new_names, "+")
        format_changes("Removed", removed, original_names, "-")

        original_duplicates = duplicate_ref_ids(original_values)
        new_duplicates = duplicate_ref_ids(new_values)
        if original_duplicates:
            duplicates = ", ".join(sorted(original_duplicates, key=natural_sort_key))
            print(f"  Warning - duplicates in the original: {duplicates}")
        if new_duplicates:
            duplicates = ", ".join(sorted(new_duplicates, key=natural_sort_key))
            print(f"  Warning - duplicates in the new file: {duplicates}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
