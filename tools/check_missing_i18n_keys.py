"""
Check missing i18n keys

This script compare keys with the frontend/messages/en.json for every file in frontend/messages to detect missing i18n keys in locale files compared to the default English file.

Usage:
    python check_missing_i18n_keys.py [-d|--dir frontend/messages] [-b|--base en] [-t|--target fr] [-o|--output output.csv]

Command-line arguments:
    -d, --dir       : Path to directory containing locale JSON files .
                      Default is frontend/messages (perfect if you are at the root project).

    -b, --base      : Base locale to compare against.
                      Default is English.

    -t, --target    : Target locale to compare against.
                      By default check all locales against base.

    -o, --output    : Output JSON file to save missing keys report.
                      Optional, but you'll only get the number of missing keys without it.

"""

import csv
import sys
import json
import argparse
from pathlib import Path


def load_json(file_path: Path) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def create_report(dir: Path, base_locale: str, target_locale: str, base_file_path: Path) -> list:
    base_keys = set(load_json(base_file_path).keys()) # will be used to check against others locales

    report = {}
    for locale_file in dir.glob("*.json"):
        iterated_locale = locale_file.stem
        if iterated_locale == base_locale:
            continue
        if target_locale and iterated_locale != target_locale:
            continue
        locale_keys = set(load_json(locale_file).keys())
        missing_keys = base_keys - locale_keys
        if missing_keys:
            report[iterated_locale] = sorted(missing_keys)

    return report

def save_report_to_csv(report: list, report_path: Path, base_file_path: Path) -> str:
    base_file = load_json(base_file_path)

    with open(report_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["locale", "missing_key", "base_translation"])
        for locale, keys in report.items():
            for key in keys:
                writer.writerow([locale, key, base_file[key]])

    print(f"\nReport saved to {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detect missing i18n keys compared to English locale."
    )
    parser.add_argument(
        "-d", "--dir",
        type=Path,
        default=Path("frontend/messages"),
        help="Path to directory containing locale JSON files (default: frontend/messages).",
    )
    parser.add_argument(
        "-b", "--base",
        type=str,
        default="en",
        help="Base locale to compare against (default: en).",
    )
    parser.add_argument(
        "-target", "--target",
        type=str,
        default=None,
        help="Target locale to compare against (optional, default all locales).",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output JSON file to save missing keys report (optional).",
    )
    args = parser.parse_args()

    if args.base == args.target:
        print(f"Base locale and target locale are the same.")
        sys.exit(1)

    base_file_path = args.dir / f"{args.base}.json"
    if not base_file_path.exists():
        print(f"Base locale file not found: {base_file_path}")
        sys.exit(1)

    report = create_report(args.dir, args.base, args.target, base_file_path)

    # Print report
    if report:
        print("Missing keys detected:")
        for locale, keys in report.items():
            print(f"[{locale}] {len(keys)} missing key(s).")
    else:
        print("All locales are aligned with the base locale.")

    # Save to file if requested
    if args.output:
        save_report_to_csv(report, args.output, base_file_path)