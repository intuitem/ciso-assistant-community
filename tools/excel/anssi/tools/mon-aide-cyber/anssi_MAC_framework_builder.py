#!/usr/bin/env python3
"""
MonAideCyber Framework Builder - Automated Extraction & Conversion Pipeline
===========================================================================

Automates the full MonAideCyber pipeline:
1) Download/reuse source ZIP from GitHub
2) Export JSON referentials
3) Build framework Excel (v2)
4) Convert Excel to YAML library
5) Cleanup temporary extracted files

Artifacts
---------
- `anssi-mon_aide_cyber.xlsx`
- `anssi-mon_aide_cyber.yaml`

Run
---
python anssi_MAC_framework_builder.py
"""

import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from anssi_MAC_export_referentiels_json import export_referentiels_json
from anssi_MAC_build_excel_from_json import build_excel_from_json

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover
    tqdm = None

# Import convert_library_v2.py (same philosophy as AD builder)
REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_SCRIPTS_DIR = REPO_ROOT / "backend" / "scripts"
sys.path.insert(0, str(BACKEND_SCRIPTS_DIR))
from convert_library_v2 import create_library as convert_excel_to_yaml


# ---------------------------------------------------------------------------
# Fixed configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ZIP_URL = "https://github.com/betagouv/mon-aide-cyber/archive/refs/heads/main.zip"
ZIP_FILE = SCRIPT_DIR / "mon-aide-cyber-main.zip"
EXTRACTED_DIR = SCRIPT_DIR / "mon-aide-cyber-main"
API_ROOT = EXTRACTED_DIR / "mon-aide-cyber-api"

OUT_DIR = SCRIPT_DIR
QUESTIONS_FILE = "questionnaire_repo.json"
MESURES_FILE = "mesures_repo.json"
EXCEL_FILE = "anssi-mon-aide-cyber.xlsx"
YAML_FILE = "anssi-mon-aide-cyber.yaml"

QUESTIONS_OUT = OUT_DIR / QUESTIONS_FILE
MESURES_OUT = OUT_DIR / MESURES_FILE
EXCEL_OUT = OUT_DIR / EXCEL_FILE
YAML_OUT = OUT_DIR / YAML_FILE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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

    # Security (For CodeFactor)
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
                    if not chunk:
                        continue
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


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def prepare_sources() -> bool:
    print_step_banner(1, "Prepare Source Repository")
    zip_reused = download_if_needed(ZIP_URL, ZIP_FILE)
    extract_zip(ZIP_FILE, EXTRACTED_DIR)

    if not API_ROOT.exists():
        raise FileNotFoundError(
            f"API directory not found after extraction: {display_path(API_ROOT)}"
        )

    print("✅ [OK] Source repository is ready")
    return zip_reused


def generate_json_files() -> None:
    print_step_banner(2, "Export JSON Referentials")
    export_referentiels_json(
        api_root=API_ROOT,
        out_dir=OUT_DIR,
        questions_file=QUESTIONS_FILE,
        mesures_file=MESURES_FILE,
    )
    print("✅ [OK] JSON export completed")


def generate_excel_file() -> None:
    print_step_banner(3, "Build Excel Framework from JSON")
    build_excel_from_json(
        questionnaire_path=QUESTIONS_OUT,
        mesures_path=MESURES_OUT,
        output_path=EXCEL_OUT,
        include_dev_info=True,
    )
    print("✅ [OK] Excel build completed")


def generate_yaml_file() -> None:
    print_step_banner(4, "Create YAML Framework from Excel")
    convert_excel_to_yaml(str(EXCEL_OUT), str(YAML_OUT), compat_mode=0, verbose=False)
    print("✅ [OK] YAML conversion completed")


def print_results(zip_reused: bool) -> None:
    print_step_banner(5, "Summary")
    print(f'- Questions JSON: "{display_path(QUESTIONS_OUT)}"')
    print(f'- Mesures JSON:   "{display_path(MESURES_OUT)}"')
    print(f'- Excel:          "{display_path(EXCEL_OUT)}"')
    print(f'- YAML:           "{display_path(YAML_OUT)}"')

    if zip_reused:
        print("⚠️  [WARNING] Existing ZIP was reused (no fresh download).")

    print(
        "ℹ️  [NOTE] Some question annotations may require some manual formatting (e.g. Questions 2, 7, 21, 22, 25, 41, 43 & 44)"
    )


def cleanup() -> None:
    print("\n🗑️  [INFO] Cleaning temporary files...")
    if EXTRACTED_DIR.exists():
        shutil.rmtree(EXTRACTED_DIR)
    for generated_json in (QUESTIONS_OUT, MESURES_OUT):
        if generated_json.exists():
            generated_json.unlink()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    zip_reused = False
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        zip_reused = prepare_sources()
        generate_json_files()
        generate_excel_file()
        generate_yaml_file()
        print_results(zip_reused)

    except KeyboardInterrupt:
        print("❌ [ERROR] Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ [ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        cleanup()


if __name__ == "__main__":
    main()
