#!/usr/bin/env python3
"""
Recursively rename Excel files by removing "_NEW" from the filename.

Examples:
    python tools/remove_new_suffix_from_excels.py
    python tools/remove_new_suffix_from_excels.py --root tools/excel
    python tools/remove_new_suffix_from_excels.py --root tools/excel --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Remove "_NEW" from .xlsx filenames recursively.'
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("excel"),
        help='Root folder to scan recursively (default: "excel").',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned renames without applying them.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        print(f"❌ [ERROR] Invalid root directory: {root}", file=sys.stderr)
        return 1

    renamed = 0
    skipped = 0

    for path in sorted(root.rglob("*.xlsx")):
        if "_NEW" not in path.stem:
            continue

        new_name = f"{path.stem.replace('_NEW', '')}{path.suffix}"
        target = path.with_name(new_name)

        if target.exists():
            print(f'⚠️  Skip (target exists): "{path}" -> "{target}"')
            skipped += 1
            continue

        print(f'➡️  Rename: "{path}" -> "{target}"')
        if not args.dry_run:
            path.rename(target)
        renamed += 1

    print(f"\n✅ Done. Renamed: {renamed} | Skipped: {skipped}")
    if args.dry_run:
        print("ℹ️  Dry-run mode: no file was renamed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
