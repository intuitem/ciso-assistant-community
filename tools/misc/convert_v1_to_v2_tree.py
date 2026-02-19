#!/usr/bin/env python3
"""
Recursively convert v1 Excel files to v2 under an Excel root folder.

Behavior:
- Converted files stay next to source files with a suffix before .xlsx (default: _NEW).
- Original files are renamed to *.old and moved under:
  <old_root>/<relative_path_from_excel_root>/

Example:
    python tools/convert_v1_to_v2_tree.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from convert_v1_to_v2 import convert_v1_to_v2


def iter_xlsx_files(excel_root: Path):
    for file in sorted(excel_root.rglob("*.xlsx")):
        if file.name.startswith("~$"):
            continue
        yield file


def main():
    parser = argparse.ArgumentParser(
        description="Recursively run convert_v1_to_v2 on all .xlsx files in an Excel tree."
    )
    parser.add_argument(
        "--excel-root",
        type=Path,
        default=Path("excel"),
        help='Root folder containing source Excel files (default: "excel").',
    )
    parser.add_argument(
        "--old-root",
        type=Path,
        default=None,
        help='Root folder for .old files (default: sibling "#old_excel" next to excel root).',
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default="_NEW",
        help='Suffix added to converted files before ".xlsx" (default: "_NEW").',
    )
    parser.add_argument(
        "--error-log",
        type=Path,
        default=Path("convert_v1_to_v2_errors.log"),
        help='Path to the error log file (default: "convert_v1_to_v2_errors.log").',
    )
    parser.add_argument(
        "--success-log",
        type=Path,
        default=Path("convert_v1_to_v2_success.log"),
        help='Path to the success log file (default: "convert_v1_to_v2_success.log").',
    )
    args = parser.parse_args()

    excel_root = args.excel_root.resolve()
    if not excel_root.exists() or not excel_root.is_dir():
        raise FileNotFoundError(f"Excel root not found or not a directory: {excel_root}")

    old_root = (
        args.old_root.resolve()
        if args.old_root
        else (excel_root.parent / "#old_excel").resolve()
    )
    old_root.mkdir(parents=True, exist_ok=True)

    files = list(iter_xlsx_files(excel_root))
    if not files:
        raise FileNotFoundError(f'No ".xlsx" files found under: {excel_root}')

    errors: list[tuple[Path, str]] = []
    successes: list[Path] = []
    total = len(files)

    for idx, src in enumerate(files, 1):
        rel_parent = src.parent.relative_to(excel_root)
        backup_dir = old_root / rel_parent
        backup_dir.mkdir(parents=True, exist_ok=True)

        dst = src.with_name(f"{src.stem}{args.suffix}{src.suffix}")

        print(f'▶️  [{idx}/{total}] "{src}" -> "{dst.name}"')
        try:
            convert_v1_to_v2(src, dst, old_output_dir=backup_dir)
            successes.append(src.relative_to(excel_root))
        except Exception as err:
            print(f'❌ Failed: "{src}" ({err})', file=sys.stderr)
            errors.append((src.relative_to(excel_root), str(err)))

    print("\n📋 Recursive conversion completed!")
    success_log_path = args.success_log.resolve()
    success_log_path.parent.mkdir(parents=True, exist_ok=True)
    with success_log_path.open("w", encoding="utf-8") as f:
        for rel_path in successes:
            f.write(f"{rel_path.as_posix()}\n")
    print(f"📝 Success log written to: {success_log_path}")

    if errors:
        log_path = args.error_log.resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as f:
            for rel_path, reason in errors:
                f.write(f"{rel_path.as_posix()}\n")
                f.write(f"{reason}\n\n")

        print(
            f"❌ {len(errors)}/{total} file(s) failed.",
            file=sys.stderr,
        )
        print(f"📝 Error log written to: {log_path}", file=sys.stderr)
        for file, _reason in errors:
            print(f"- {file.as_posix()}", file=sys.stderr)
        sys.exit(1)

    print("✅ All files processed successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ [ERROR] {err}", file=sys.stderr)
        sys.exit(1)
