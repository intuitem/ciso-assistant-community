#!/usr/bin/env python3
"""
Validate converted Excel files against backend YAML libraries.

Workflow:
1. Read relative Excel paths from convert_v1_to_v2 success log.
2. For each path, run convert_library_v2 in mode 0, then compatibility modes.
3. Compare produced YAML with backend/library/libraries/<normalized_name>.yaml.
4. Keep all produced YAML candidates next to the Excel file.
5. If match found, copy matching YAML next to the converted Excel and log success.
6. If no match found, log failure details.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
import unicodedata

import yaml

from convert_library_v2 import COMPATIBILITY_MODES, create_library


def normalize_yaml_name_from_excel(excel_name: str) -> str:
    # Comparison rule: lowercase YAML filename and remove trailing "_new".
    stem = Path(excel_name).stem.lower()
    if stem.endswith("_new"):
        stem = stem[: -len("_new")]
    return f"{stem}.yaml"


def remove_top_level_keys(data: Any, keys: set[str]) -> Any:
    # Keys in `keys` are ignored only at root level.
    # Keep nested data untouched.
    if isinstance(data, dict):
        cleaned = dict(data)
        for key in keys:
            cleaned.pop(key, None)
        return cleaned
    return data


def normalize_mapping_object_shape(data: Any) -> Any:
    """
    Legacy mapping YAMLs may use:
      objects.requirement_mapping_set (single object)
    while newer outputs may use:
      objects.requirement_mapping_sets (list, with optional "revert" entry).

    For comparison, align both formats to the legacy single-object shape.
    """
    if not isinstance(data, dict):
        return data

    objects = data.get("objects")
    if not isinstance(objects, dict):
        return data

    normalized = dict(data)
    normalized_objects = dict(objects)

    singular = normalized_objects.get("requirement_mapping_set")
    plural = normalized_objects.get("requirement_mapping_sets")

    if not isinstance(singular, dict) and isinstance(plural, list) and plural:
        normalized_objects["requirement_mapping_set"] = plural[0]

    if "requirement_mapping_sets" in normalized_objects:
        del normalized_objects["requirement_mapping_sets"]

    normalized["objects"] = normalized_objects
    return normalized


def normalize_for_compare(data: Any) -> Any:
    """
    Build a canonical representation to compare YAML content semantically:
    - dict keys are sorted,
    - list order is ignored,
    - date/datetime values are normalized to isoformat strings.
    """
    if isinstance(data, dict):
        normalized_dict: dict[str, Any] = {}
        for k, v in sorted(data.items()):
            # Legacy YAML files may keep mixed casing in this specific URN list.
            # Normalize only this field to lowercase for semantic comparison.
            if k == "reference_controls" and isinstance(v, list):
                lowered_controls: list[Any] = []
                for item in v:
                    normalized_item = normalize_for_compare(item)
                    if isinstance(normalized_item, str):
                        lowered_controls.append(normalized_item.lower())
                    else:
                        lowered_controls.append(normalized_item)
                normalized_dict[k] = lowered_controls
                continue

            # Some legacy YAMLs store risk matrix abbreviations as integers,
            # while newer outputs may serialize them as numeric strings.
            # Treat "1" and 1 as equivalent for this specific field.
            if k == "abbreviation":
                normalized_value = normalize_for_compare(v)
                if (
                    isinstance(normalized_value, str)
                    and normalized_value.isdigit()
                ):
                    normalized_dict[k] = int(normalized_value)
                else:
                    normalized_dict[k] = normalized_value
                continue
            normalized_dict[k] = normalize_for_compare(v)
        return normalized_dict

    if isinstance(data, list):
        normalized_items = [normalize_for_compare(x) for x in data]
        return sorted(
            normalized_items,
            key=lambda x: json.dumps(
                x, sort_keys=True, ensure_ascii=False, default=str
            ),
        )

    if isinstance(data, (date, datetime)):
        return data.isoformat()

    if isinstance(data, str):
        # Normalize text so YAML formatting differences do not create false mismatches:
        # - Unicode canonical form
        # - CRLF/CR -> LF
        # - strip trailing spaces on each line
        # - strip global leading/trailing spaces/newlines
        text = unicodedata.normalize("NFC", data).replace("\r\n", "\n").replace("\r", "\n")
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        return text.strip()

    return data


def prune_empty_scalar_fields(data: Any) -> Any:
    """
    Remove dict keys recursively when value is an empty scalar (None or "").
    This allows comparison to ignore legacy empty fields that are omitted by
    newer converters.
    """
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            pruned_v = prune_empty_scalar_fields(v)
            if k == "implementation_groups_definition" and pruned_v == []:
                continue
            if pruned_v is None or pruned_v == "":
                continue
            cleaned[k] = pruned_v
        return cleaned

    if isinstance(data, list):
        return [prune_empty_scalar_fields(x) for x in data]

    return data


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_success_paths(success_log: Path) -> list[Path]:
    paths: list[Path] = []
    with success_log.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            paths.append(Path(line))
    return paths


def resolve_excel_path(excel_root: Path, rel_path: Path, excel_suffix: str) -> Path:
    # First try the exact path from success log.
    direct = excel_root / rel_path
    if direct.exists():
        return direct

    # Fallback for flows where converted files were kept with a suffix (e.g. "_NEW").
    fallback = direct.with_name(f"{direct.stem}{excel_suffix}{direct.suffix}")
    if fallback.exists():
        return fallback

    raise FileNotFoundError(
        f'Excel not found for "{rel_path}" (tried "{direct}" and "{fallback}")'
    )


def main():
    tools_dir = Path(__file__).resolve().parent
    repo_dir = tools_dir.parent

    parser = argparse.ArgumentParser(
        description="Check convert_library_v2 outputs against backend libraries YAML files."
    )
    parser.add_argument(
        "--excel-root",
        type=Path,
        default=tools_dir / "excel",
        help='Root folder of converted Excel files (default: "tools/excel").',
    )
    parser.add_argument(
        "--success-log",
        type=Path,
        default=tools_dir / "convert_v1_to_v2_success.log",
        help='Log created by convert_v1_to_v2_tree.py (default: "tools/convert_v1_to_v2_success.log").',
    )
    parser.add_argument(
        "--libraries-root",
        type=Path,
        default=repo_dir / "backend/library/libraries",
        help='Reference YAML folder (default: "backend/library/libraries").',
    )
    parser.add_argument(
        "--excel-suffix-fallback",
        type=str,
        default="_NEW",
        help='Suffix to try when a path from success log no longer exists (default: "_NEW").',
    )
    parser.add_argument(
        "--success-out-log",
        type=Path,
        default=tools_dir / "yaml_compare_success.log",
        help='Log file listing matched YAMLs and compatibility mode.',
    )
    parser.add_argument(
        "--failure-out-log",
        type=Path,
        default=tools_dir / "yaml_compare_failures.log",
        help='Log file listing files with no matching YAML.',
    )
    parser.add_argument(
        "--execution-log",
        type=Path,
        default=tools_dir / "yaml_compare_execution.log",
        help="Detailed execution log that captures convert_library_v2 output.",
    )
    args = parser.parse_args()

    excel_root = args.excel_root.resolve()
    success_log = args.success_log.resolve()
    libraries_root = args.libraries_root.resolve()
    success_out_log = args.success_out_log.resolve()
    failure_out_log = args.failure_out_log.resolve()
    execution_log = args.execution_log.resolve()

    if not excel_root.is_dir():
        raise FileNotFoundError(f"Excel root not found or not a directory: {excel_root}")
    if not success_log.is_file():
        raise FileNotFoundError(f"Success log not found: {success_log}")
    if not libraries_root.is_dir():
        raise FileNotFoundError(
            f"Libraries root not found or not a directory: {libraries_root}"
        )

    success_out_log.parent.mkdir(parents=True, exist_ok=True)
    failure_out_log.parent.mkdir(parents=True, exist_ok=True)
    execution_log.parent.mkdir(parents=True, exist_ok=True)

    rel_excel_paths = read_success_paths(success_log)
    if not rel_excel_paths:
        raise ValueError(f"No entries found in success log: {success_log}")

    success_lines: list[str] = []
    failure_lines: list[str] = []
    success_count = 0
    failure_count = 0

    modes = list(COMPATIBILITY_MODES.keys())
    total = len(rel_excel_paths)

    with execution_log.open("w", encoding="utf-8") as exec_log:
        for idx, rel_path in enumerate(rel_excel_paths, 1):
            print(f'▶️  [{idx}/{total}] Checking "{rel_path.as_posix()}"')
            exec_log.write(f'[{idx}/{total}] {rel_path.as_posix()}\n')

            try:
                excel_path = resolve_excel_path(
                    excel_root, rel_path, args.excel_suffix_fallback
                )
            except Exception as err:
                failure_lines.append(f"{rel_path.as_posix()}")
                failure_lines.append(f"RESOLUTION_ERROR: {err}")
                failure_lines.append("")
                failure_count += 1
                exec_log.write(f"RESOLUTION_ERROR: {err}\n\n")
                print(f'❌ Resolution failed: "{rel_path}" ({err})', file=sys.stderr)
                continue

            normalized_yaml_name = normalize_yaml_name_from_excel(excel_path.name)
            reference_yaml_path = libraries_root / normalized_yaml_name

            if not reference_yaml_path.is_file():
                failure_lines.append(f"{rel_path.as_posix()}")
                failure_lines.append(
                    f'NO_REFERENCE_YAML: expected "{reference_yaml_path.as_posix()}"'
                )
                failure_lines.append("")
                failure_count += 1
                exec_log.write(
                    f'NO_REFERENCE_YAML: expected "{reference_yaml_path.as_posix()}"\n\n'
                )
                print(
                    f'❌ Reference YAML not found for "{rel_path}" -> "{normalized_yaml_name}"',
                    file=sys.stderr,
                )
                continue

            # Keep every generated YAML candidate next to the Excel source file.
            generated_subdir = excel_path.parent

            # Ignore top-level fields that can differ between conversions.
            reference_data = prune_empty_scalar_fields(
                normalize_for_compare(
                    normalize_mapping_object_shape(
                        remove_top_level_keys(
                            load_yaml(reference_yaml_path),
                            {"convert_library_version", "publication_date"},
                        )
                    )
                )
            )
            matched_mode: int | None = None
            matched_yaml: Path | None = None
            mode_failures: list[str] = []

            # Try default conversion first, then all compatibility modes until a match is found.
            for mode in modes:
                candidate_yaml = generated_subdir / (
                    f"{normalized_yaml_name[:-5]}__mode_{mode}.yaml"
                )
                exec_log.write(f"mode={mode} start\n")
                try:
                    with contextlib.redirect_stdout(exec_log), contextlib.redirect_stderr(
                        exec_log
                    ):
                        create_library(
                            str(excel_path),
                            str(candidate_yaml),
                            compat_mode=mode,
                            verbose=False,
                        )
                    candidate_data = prune_empty_scalar_fields(
                        normalize_for_compare(
                            normalize_mapping_object_shape(
                                remove_top_level_keys(
                                    load_yaml(candidate_yaml),
                                    {"convert_library_version", "publication_date"},
                                )
                            )
                        )
                    )
                    if candidate_data == reference_data:
                        matched_mode = mode
                        matched_yaml = candidate_yaml
                        exec_log.write(f"mode={mode}: MATCH\n")
                        break
                    msg = (
                        f'mode={mode}: generated but content does not match "{reference_yaml_path.name}"'
                    )
                    mode_failures.append(msg)
                    exec_log.write(f"{msg}\n")
                except Exception as err:
                    msg = f"mode={mode}: ERROR: {err}"
                    mode_failures.append(msg)
                    exec_log.write(f"{msg}\n")
                finally:
                    exec_log.write("\n")

            if matched_mode is None or matched_yaml is None:
                failure_lines.append(f"{rel_path.as_posix()}")
                failure_lines.append(
                    f'NO_MATCH_WITH_REFERENCE: "{reference_yaml_path.as_posix()}"'
                )
                for line in mode_failures:
                    failure_lines.append(line)
                failure_lines.append("")
                failure_count += 1
                exec_log.write("NO_MATCH\n\n")
                print(f'❌ No match found for "{rel_path}"', file=sys.stderr)
                continue

            # Keep the matching YAML next to the converted Excel for direct/manual inspection.
            final_yaml_path = excel_path.parent / normalized_yaml_name
            shutil.copy2(matched_yaml, final_yaml_path)
            success_lines.append(
                f"{rel_path.as_posix()} -> {final_yaml_path.as_posix()} | compat_mode={matched_mode}"
            )
            success_count += 1
            exec_log.write(
                f'MATCH -> {final_yaml_path.as_posix()} | compat_mode={matched_mode}\n\n'
            )
            print(
                f'✅ Match found for "{rel_path.as_posix()}" with mode={matched_mode} ({reference_yaml_path.name})'
            )

    # Always write both reports so each run has a complete trace.
    with success_out_log.open("w", encoding="utf-8") as f:
        for line in success_lines:
            f.write(f"{line}\n")

    with failure_out_log.open("w", encoding="utf-8") as f:
        for line in failure_lines:
            f.write(f"{line}\n")

    print("\n📋 YAML comparison completed!")
    print(f"📝 Success log: {success_out_log}")
    print(f"📝 Failure log: {failure_out_log}")
    print(f"📝 Execution log: {execution_log}")
    print("📦 Candidate YAML files kept next to each Excel source file")
    print(f"📊 Comparisons: {success_count} reussies, {failure_count} ratees")
    if failure_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ [ERROR] {err}", file=sys.stderr)
        sys.exit(1)
