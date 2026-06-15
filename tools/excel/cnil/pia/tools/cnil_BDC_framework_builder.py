#!/usr/bin/env python3
"""
CNIL PIA Knowledge Base Framework Builder
=========================================

Automates the full CNIL PIA knowledge base pipeline:
1) Download/reuse source ZIP from GitHub
2) Export one consolidated multilingual JSON referential
3) Build framework Excel (v2)
4) Convert Excel to YAML library
5) Cleanup temporary extracted files

Artifacts
---------
- `cnil-pia-bdc.xlsx`
- `cnil-pia-bdc.yaml`

Run
---
python cnil_BDC_framework_builder.py
python cnil_BDC_framework_builder.py --force-source-locale
"""

import argparse
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from cnil_BDC_build_excel_from_json import build_excel_from_json
from cnil_BDC_export_referentiels_json import export_referentiels_json

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover
    tqdm = None


REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_SCRIPTS_DIR = REPO_ROOT / "backend" / "scripts"
sys.path.insert(0, str(BACKEND_SCRIPTS_DIR))
from convert_library_v2 import create_library as convert_excel_to_yaml


SCRIPT_DIR = Path(__file__).resolve().parent
ZIP_URL = "https://github.com/LINCnil/pia/archive/refs/heads/master.zip"
ZIP_FILE = SCRIPT_DIR / "pia-master.zip"
EXTRACTED_DIR = SCRIPT_DIR / "pia-master"

OUT_DIR = SCRIPT_DIR
JSON_FILE = "bdc_repo.json"
EXCEL_FILE = "cnil-pia-bdc.xlsx"
YAML_FILE = "cnil-pia-bdc.yaml"
SOURCE_LOCALE_JSON_FILE = "bdc_repo_source_locale.json"
SOURCE_LOCALE_EXCEL_FILE = "cnil-pia-bdc-source-locale.xlsx"
SOURCE_LOCALE_YAML_FILE = "cnil-pia-bdc-source-locale.yaml"

JSON_OUT = OUT_DIR / JSON_FILE
EXCEL_OUT = OUT_DIR / EXCEL_FILE
YAML_OUT = OUT_DIR / YAML_FILE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the CNIL PIA knowledge base framework library."
    )
    parser.add_argument(
        "-l",
        "--force-source-locale",
        action="store_true",
        help="Keep source locale metadata as-is, without English fallback translations.",
    )
    return parser.parse_args()


def output_paths(force_source_locale: bool) -> tuple[str, Path, Path, Path]:
    if force_source_locale:
        return (
            SOURCE_LOCALE_JSON_FILE,
            OUT_DIR / SOURCE_LOCALE_JSON_FILE,
            OUT_DIR / SOURCE_LOCALE_EXCEL_FILE,
            OUT_DIR / SOURCE_LOCALE_YAML_FILE,
        )
    return JSON_FILE, JSON_OUT, EXCEL_OUT, YAML_OUT


def display_path(path: Path, base_dir: Path = SCRIPT_DIR) -> str:
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


def print_step_banner(step_number: int, title: str) -> None:
    message = f"##### [STEP {step_number}] {title} #####"
    line = "#" * len(message)
    print(f"\n{line}")
    print(message)
    print(f"{line}\n")


def download_if_needed(zip_url: str, zip_file: Path) -> bool:
    """Return True if an existing ZIP is reused, else False."""
    if zip_file.exists():
        print(f'♻️  [INFO] ZIP already exists: "{display_path(zip_file)}"')
        return True

    zip_file.parent.mkdir(parents=True, exist_ok=True)
    print(f'📥 [DOWN] Downloading ZIP from: "{zip_url}"')

    parsed = urlparse(zip_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Unsupported URL scheme")
    if parsed.netloc != "github.com":
        raise ValueError("Unexpected host")

    with requests.get(zip_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        total_size = int(response.headers.get("Content-Length", 0))
        with zip_file.open("wb") as out_file:
            if tqdm is None:
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        out_file.write(chunk)
            else:
                with tqdm(
                    total=total_size if total_size > 0 else None,
                    unit="o",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc="ZIP",
                ) as progress:
                    for chunk in response.iter_content(chunk_size=1024 * 64):
                        if not chunk:
                            continue
                        out_file.write(chunk)
                        progress.update(len(chunk))

    print(f'✅ [OK] ZIP downloaded: "{display_path(zip_file)}"')
    return False


def extract_zip(zip_file: Path, extracted_dir: Path) -> None:
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    print(f'📂 [INFO] Extracting ZIP: "{display_path(zip_file)}"')
    with zipfile.ZipFile(zip_file, "r") as zf:
        zf.extractall(SCRIPT_DIR)


def prepare_sources() -> bool:
    print_step_banner(1, "Prepare Source Repository")
    zip_reused = download_if_needed(ZIP_URL, ZIP_FILE)
    extract_zip(ZIP_FILE, EXTRACTED_DIR)

    if not EXTRACTED_DIR.exists():
        raise FileNotFoundError(
            f"Repository directory not found after extraction: {display_path(EXTRACTED_DIR)}"
        )

    print("✅ [OK] Source repository is ready")
    return zip_reused


def generate_json_file(
    json_file: str, force_source_locale: bool = False
) -> None:
    print_step_banner(2, "Export JSON Referential")
    export_referentiels_json(
        repo_root=EXTRACTED_DIR,
        out_dir=OUT_DIR,
        output_file=json_file,
        force_source_locale=force_source_locale,
    )
    print("✅ [OK] JSON export completed")


def generate_excel_file(json_out: Path, excel_out: Path) -> None:
    print_step_banner(3, "Build Excel Framework from JSON")
    build_excel_from_json(json_path=json_out, output_path=excel_out)
    print("✅ [OK] Excel build completed")


def generate_yaml_file(excel_out: Path, yaml_out: Path) -> None:
    print_step_banner(4, "Create YAML Framework from Excel")
    convert_excel_to_yaml(str(excel_out), str(yaml_out), compat_mode=0, verbose=False)
    print("✅ [OK] YAML conversion completed")


def print_results(zip_reused: bool, json_out: Path, excel_out: Path, yaml_out: Path) -> None:
    print_step_banner(5, "Summary")
    print(f'- JSON:  "{display_path(json_out)}"')
    print(f'- Excel: "{display_path(excel_out)}"')
    print(f'- YAML:  "{display_path(yaml_out)}"')
    if zip_reused:
        print("⚠️  [WARNING] Existing ZIP was reused (no fresh download).")


def cleanup(json_out: Path) -> None:
    print("\n🗑️  [INFO] Cleaning temporary files...")
    if EXTRACTED_DIR.exists():
        shutil.rmtree(EXTRACTED_DIR)
    if json_out.exists():
        json_out.unlink()


def main() -> None:
    args = parse_args()
    json_file, json_out, excel_out, yaml_out = output_paths(args.force_source_locale)
    zip_reused = False
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        zip_reused = prepare_sources()
        generate_json_file(json_file, args.force_source_locale)
        generate_excel_file(json_out, excel_out)
        generate_yaml_file(excel_out, yaml_out)
        print_results(zip_reused, json_out, excel_out, yaml_out)
    except KeyboardInterrupt:
        print("❌ [ERROR] Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ [ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        cleanup(json_out)


if __name__ == "__main__":
    main()
