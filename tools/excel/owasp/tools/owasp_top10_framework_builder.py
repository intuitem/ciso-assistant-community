#!/usr/bin/env python3
"""Run the complete OWASP Top 10 to CISO Assistant build pipeline."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from owasp_top10_build_excel import build_excel_from_json
from owasp_top10_export_json import export_owasp_top10_json, write_relative_links_log

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover
    tqdm = None


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
BACKEND_SCRIPTS_DIR = REPOSITORY_ROOT / "backend" / "scripts"
sys.path.insert(0, str(BACKEND_SCRIPTS_DIR))

from convert_library_v2 import create_library as convert_excel_to_yaml


ZIP_URL = "https://github.com/OWASP/Top10/archive/refs/heads/master.zip"
ZIP_PATH = SCRIPT_DIR / "owasp-top10-master.zip"
EXTRACTED_ROOT = SCRIPT_DIR / "Top10-master"


def output_suffix(value: str) -> str:
    """Validate a filename suffix used for generated artifacts."""
    suffix = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", suffix):
        raise argparse.ArgumentTypeError(
            "the output suffix must contain only letters, numbers, dots, "
            "underscores, or hyphens"
        )
    return suffix


def output_stem(year: int, suffix: str | None = None) -> str:
    """Return the shared basename for generated OWASP artifacts."""
    filename_suffix = f"-{suffix}" if suffix else ""
    return f"owasp-top-10-web-{year}{filename_suffix}"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPOSITORY_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def print_step_banner(step_number: int, title: str) -> None:
    message = f"##### [STEP {step_number}] {title} #####"
    line = "#" * len(message)
    print(f"\n{line}")
    print(message)
    print(f"{line}\n")


def download_zip(zip_url: str, output_path: Path, refresh: bool = False) -> bool:
    """Download the repository ZIP and return True when the cache was reused."""
    if output_path.exists() and not refresh:
        print(f'♻️  [INFO] ZIP already exists: "{display_path(output_path)}"')
        return True

    print(f'📥 [DOWN] Downloading ZIP from: "{zip_url}"')

    parsed = urlparse(zip_url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        raise ValueError("The OWASP source URL must use HTTPS on github.com")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(zip_url, stream=True, timeout=120) as response:
        response.raise_for_status()
        total_size = int(response.headers.get("Content-Length", 0))
        with output_path.open("wb") as destination:
            chunks = response.iter_content(chunk_size=1024 * 128)
            if tqdm is None:
                for chunk in chunks:
                    if chunk:
                        destination.write(chunk)
            else:
                with tqdm(
                    total=total_size or None,
                    unit="o",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc="ZIP",
                ) as progress:
                    for chunk in chunks:
                        if chunk:
                            destination.write(chunk)
                            progress.update(len(chunk))
    print(f'✅ [OK] ZIP downloaded: "{display_path(output_path)}"')
    return False


def extract_zip_safely(zip_path: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    print(f'📂 [INFO] Extracting ZIP: "{display_path(zip_path)}"')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination_resolved = destination.resolve()

    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            member_path = (destination.parent / member.filename).resolve()
            if member_path != destination_resolved and destination_resolved not in member_path.parents:
                raise ValueError(f"Unsafe ZIP member path: {member.filename}")
        archive.extractall(destination.parent)

    if not destination.exists():
        raise FileNotFoundError(f"Expected extracted repository was not found: {destination}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an OWASP Top 10 CISO Assistant library (default year: 2025)"
    )
    parser.add_argument(
        "-y",
        "--year",
        type=int,
        default=2025,
        help="OWASP Top 10 release year (tested with 2021 and 2025)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for the generated XLSX and YAML files",
    )
    parser.add_argument(
        "--output-suffix",
        type=output_suffix,
        help=(
            "Append a suffix to generated filenames, for example "
            "'relative-links-fixed'"
        ),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        help="Use an already extracted OWASP/Top10 repository instead of downloading it",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download a fresh repository ZIP even when a cached ZIP exists",
    )
    parser.add_argument(
        "--keep-json",
        action="store_true",
        help="Keep the normalized intermediate JSON file",
    )
    parser.add_argument(
        "--keep-extracted",
        action="store_true",
        help="Keep the extracted repository when the builder downloaded it",
    )
    parser.add_argument(
        "--skip-yaml",
        action="store_true",
        help="Generate only the XLSX file",
    )
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> dict[str, object]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_stem = output_stem(args.year, args.output_suffix)
    json_path = SCRIPT_DIR / f"{artifact_stem}.json"
    excel_path = output_dir / f"{artifact_stem}.xlsx"
    yaml_path = output_dir / f"{artifact_stem}.yaml"
    relative_links_log_path = output_dir / f"{artifact_stem}-relative-links.log"

    manages_extracted_source = args.source_root is None
    source_root = args.source_root.resolve() if args.source_root else EXTRACTED_ROOT
    zip_reused = False

    try:
        print_step_banner(1, "Prepare Source Repository")
        if manages_extracted_source:
            zip_reused = download_zip(ZIP_URL, ZIP_PATH, refresh=args.refresh)
            extract_zip_safely(ZIP_PATH, EXTRACTED_ROOT)
        else:
            print(
                f'📂 [INFO] Using source repository: "{display_path(source_root)}"'
            )
        if not (source_root / str(args.year) / "docs").exists():
            raise FileNotFoundError(
                f"The source repository has no docs for year {args.year}: {source_root}"
            )
        print("✅ [OK] Source repository is ready")

        print_step_banner(
            2, f"Extract OWASP Top 10:{args.year} Markdown and Translations"
        )
        payload = export_owasp_top10_json(source_root, json_path, year=args.year)
        print("✅ [OK] JSON export completed")

        print_step_banner(3, "Build Excel Framework from JSON")
        stats = build_excel_from_json(json_path, excel_path)
        print("✅ [OK] Excel build completed")

        print_step_banner(4, "Create YAML Framework from Excel")
        if args.skip_yaml:
            print("ℹ️  [NOTE] YAML conversion skipped by request (--skip-yaml).")
        else:
            convert_excel_to_yaml(
                str(excel_path), str(yaml_path), compat_mode=0, verbose=False
            )
            print("✅ [OK] YAML conversion completed")

        print_step_banner(5, "Summary")
        locales = [str(locale) for locale in payload["exported_locales"]]
        print(f"- Year:              {args.year}")
        print(f"- Threats exported:  {stats['threats']}")
        print(f"- Languages exported: {len(locales)}")
        print(f"- Languages:         {', '.join(locales)}")
        print(f"- Default language:  {payload['default_locale']}")
        print(f'- Excel:             "{display_path(excel_path)}"')
        if not args.skip_yaml:
            print(f'- YAML:              "{display_path(yaml_path)}"')
        if args.keep_json:
            print(f'- JSON:              "{display_path(json_path)}"')
        if zip_reused:
            print(
                "⚠️  [WARNING] Existing ZIP was reused (no fresh download). "
                "Use --refresh to download a fresh copy."
            )

        fallbacks = payload.get("english_fallbacks", [])
        if fallbacks:
            print(f"⚠️  [WARNING] English file fallbacks applied: {len(fallbacks)}")
            for fallback in fallbacks:
                print(
                    f"- {fallback['locale']} / {fallback['target']} / "
                    f"{fallback['source_file']}: {fallback['reason']}"
                )

        skipped = payload.get("skipped_locales", {})
        if skipped:
            print(f"⚠️  [WARNING] Skipped languages: {len(skipped)}")
            for locale, reason in skipped.items():
                print(f"- {locale}: {reason}")

        relative_links = payload.get("relative_links_removed", [])
        write_relative_links_log(relative_links, relative_links_log_path)
        print(
            "- Relative Markdown links converted to bold: "
            f"{len(relative_links)}"
        )
        print(
            f'- Relative link log: "{display_path(relative_links_log_path)}"'
        )

        return {
            "excel": excel_path,
            "yaml": None if args.skip_yaml else yaml_path,
            "languages": locales,
            "english_fallbacks": fallbacks,
            "skipped_languages": skipped,
            "relative_links_removed": relative_links,
            "relative_links_log": relative_links_log_path,
        }
    finally:
        print("\n🗑️  [INFO] Cleaning temporary files...")
        if json_path.exists() and not args.keep_json:
            json_path.unlink()
        if manages_extracted_source and EXTRACTED_ROOT.exists() and not args.keep_extracted:
            shutil.rmtree(EXTRACTED_ROOT)


def main() -> None:
    args = parse_args()
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        print("❌ [ERROR] Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ [ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
