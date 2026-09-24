#!/usr/bin/env python3
"""Compare normalized content from two YAML libraries or v2 Excel workbooks.

A ``.xlsx`` file is temporarily converted with the project's v2 converter
before comparison. The comparator therefore accepts two YAML files or a YAML
file and its source workbook.

Example:

    python tools/compare_library_content.py \
        backend/library/libraries/adobe-ccf-v5.yaml \
        tools/excel/adobe/adobe-ccf-v5.xlsx

Normalization loads YAML, which converts ``\\xE9`` and ``\\u00e9`` to ``é``.
It also normalizes Unicode (NFC) and line endings without hiding differences
in values, types, lists, or structure.
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
PROJECT_ROOT = SCRIPT_PATH.parents[2]
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
        description="Compare two YAML libraries or Excel workbooks after normalization."
    )
    parser.add_argument("left", type=Path, help="First YAML file or v2 Excel workbook")
    parser.add_argument("right", type=Path, help="Second YAML file or v2 Excel workbook")
    parser.add_argument(
        "--compat",
        type=int,
        default=0,
        help="Converter compatibility mode for Excel input (default: 0)",
    )
    parser.add_argument(
        "--max-differences",
        type=int,
        default=100,
        help="Maximum number of detailed differences (default: 100)",
    )
    parser.add_argument(
        "--include-converter-metadata",
        action="store_true",
        help="Also compare the technical convert_library_version metadata.",
    )
    parser.add_argument(
        "--fail-on-difference",
        action="store_true",
        help="Return exit code 1 when at least one difference is found.",
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
        raise ValueError(f"Unable to read YAML '{path}': {error}") from error


def load_converter_module() -> Any:
    if not CONVERTER_PATH.is_file():
        raise ValueError(f"v2 converter not found: {CONVERTER_PATH}")

    module_spec = importlib.util.spec_from_file_location(
        "ciso_library_v2_converter", CONVERTER_PATH
    )
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Unable to load converter: {CONVERTER_PATH}")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def convert_excel_to_data(path: Path, compat_mode: int) -> Any:
    """Convert a v2 Excel workbook to a temporary file, then load its YAML."""

    converter = load_converter_module()
    with tempfile.TemporaryDirectory(prefix="compare_library_content_") as temp_dir:
        converted_yaml = Path(temp_dir) / f"{path.stem}.yaml"
        # The converter prints progress. Keep the comparator output focused on
        # its own report.
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
        raise ValueError(f"File not found: {path}")

    suffix = path.suffix.casefold()
    if suffix in YAML_EXTENSIONS:
        return load_yaml(path), "YAML"
    if suffix in EXCEL_EXTENSIONS:
        return convert_excel_to_data(path, compat_mode), "v2 Excel temporarily converted to YAML"
    raise ValueError(
        f"Unsupported format for '{path}'. Accepted formats: "
        f"{', '.join(sorted(YAML_EXTENSIONS | EXCEL_EXTENSIONS))}"
    )


def normalize_text(value: str) -> str:
    """Remove encoding differences without changing the meaning of text."""

    normalized_line_endings = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized_unicode = unicodedata.normalize("NFC", normalized_line_endings)
    readable_spaces = normalized_unicode.replace("\u00a0", " ").replace("\u202f", " ")
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

    normalized_paragraphs: list[str] = []
    for paragraph in paragraphs:
        result = paragraph[0]
        for line in paragraph[1:]:
            # Keep lists readable, but join ordinary lines separated only by the
            # YAML serializer as continuous text.
            separator = (
                "\n"
                if BULLET_OR_NUMBERED_LINE.match(result.split("\n")[-1])
                or BULLET_OR_NUMBERED_LINE.match(line)
                else " "
            )
            result = f"{result}{separator}{line}"
        normalized_paragraphs.append(result)

    return "\n\n".join(normalized_paragraphs)


def normalize_data(value: Any, include_converter_metadata: bool) -> Any:
    """Recursively normalize YAML values for reliable comparison."""

    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, (datetime_module.datetime, datetime_module.date)):
        return value.isoformat()
    if isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            normalized_key = normalize_text(key) if isinstance(key, str) else key
            if (
                not include_converter_metadata
                and normalized_key in IGNORED_CONVERTER_KEYS
            ):
                continue
            if normalized_key in normalized:
                raise ValueError(
                    f"Two keys become identical after normalization: {normalized_key!r}"
                )
            normalized[normalized_key] = normalize_data(
                item, include_converter_metadata
            )
        return normalized
    if isinstance(value, list):
        return [normalize_data(item, include_converter_metadata) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_data(item, include_converter_metadata) for item in value)
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
            f"Different type ({type(left).__name__} / {type(right).__name__})",
            left,
            right,
        )
        return

    if isinstance(left, dict):
        left_keys = set(left)
        right_keys = set(right)
        for key in sorted(left_keys - right_keys, key=sort_key):
            if append_difference(
                differences, maximum, f"{path}.{key}", "Missing key on the right", left[key], None
            ):
                return
        for key in sorted(right_keys - left_keys, key=sort_key):
            if append_difference(
                differences, maximum, f"{path}.{key}", "Missing key on the left", None, right[key]
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
                f"Different length ({len(left)} / {len(right)})",
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
        append_difference(differences, maximum, path, "Different value", left, right)


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
    print("Normalized library comparison")
    print(f"- Left: {display_path(left_path)} ({left_kind})")
    print(f"- Right: {display_path(right_path)} ({right_kind})")
    print(
        "- Normalization: YAML decoding, Unicode NFC, trailing whitespace, "
        "line endings and continuation lines, key order"
    )

    if not differences:
        print("\n✅ Content and structure are identical after normalization.")
        return

    print(f"\n❌ {len(differences)} difference(s) shown.")
    if len(differences) >= maximum:
        print(f"The limit of {maximum} differences has been reached.")
    for difference in differences:
        print(f"\n- {difference.path} — {difference.reason}")
        print(f"  left: {preview(difference.left)}")
        print(f"  right: {preview(difference.right)}")


def main() -> int:
    arguments = parse_arguments()
    if arguments.max_differences < 1:
        print("Error: --max-differences must be greater than 0.", file=sys.stderr)
        return 2

    try:
        left_data, left_kind = load_source(arguments.left.resolve(), arguments.compat)
        right_data, right_kind = load_source(arguments.right.resolve(), arguments.compat)
        normalized_left = normalize_data(
            left_data, arguments.include_converter_metadata
        )
        normalized_right = normalize_data(
            right_data, arguments.include_converter_metadata
        )
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    differences: list[Difference] = []
    compare_values(normalized_left, normalized_right, "$", differences, arguments.max_differences)
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
