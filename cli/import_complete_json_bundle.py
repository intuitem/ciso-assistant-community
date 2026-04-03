#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXED_BUNDLE = ROOT / "risk_bundle_fixed.json"
DEFAULT_RAW_BUNDLE = Path(r"E:\asset threat scenario control.txt")


def parse_bundle_text(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    marker = '"risk_scenario_ref_ids": ["SC-008'
    idx = raw.rfind(marker)
    if idx == -1:
        raise ValueError("JSON invalid and no known truncation marker found")
    repaired = raw[: idx + len(marker)] + '"]\n      ,"effectiveness": 3,\n      "labels": []\n    }\n  ]\n}\n'
    return json.loads(repaired)


def prepare_bundle(raw_bundle: Path | None) -> None:
    if raw_bundle and raw_bundle.exists():
        raw_bytes = raw_bundle.read_bytes()
        last_error = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                bundle = parse_bundle_text(raw_bytes.decode(enc))
                FIXED_BUNDLE.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Prepared fixed bundle from {raw_bundle}")
                return
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Unable to prepare bundle from source file: {last_error}")
    if not FIXED_BUNDLE.exists():
        raise RuntimeError("No source bundle found and risk_bundle_fixed.json does not exist")


def run_step(title: str, cmd: list[str]) -> None:
    print(f"== {title} ==")
    subprocess.run(cmd, cwd=ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a complete JSON risk bundle into CISO Assistant."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help=(
            "Path to the raw JSON bundle. If omitted, the script tries the historical "
            f"default location {DEFAULT_RAW_BUNDLE} and otherwise reuses risk_bundle_fixed.json."
        ),
    )
    parser.add_argument(
        "--folder",
        default="Global",
        help="Folder/domain name used by Data Wizard imports when generating assets, threats, and controls.",
    )
    parser.add_argument(
        "--perimeter",
        default="Global Perimeter",
        help="Perimeter name used for risk assessment scenario import.",
    )
    parser.add_argument(
        "--matrix",
        default="4x4 risk matrix from EBIOS-RM",
        help="Risk matrix name used for risk assessment scenario import.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    py = sys.executable
    raw_bundle = args.input
    if raw_bundle is None and DEFAULT_RAW_BUNDLE.exists():
        raw_bundle = DEFAULT_RAW_BUNDLE
    prepare_bundle(raw_bundle)

    run_step("Import risk sources", [py, "-W", "ignore", "import_risk_sources.py"])
    run_step("Import EBIOS feared events", [py, "-W", "ignore", "import_ebios_feared_events.py"])
    run_step("Generate bundle CSV files", [py, "bundle_to_csv.py"])
    run_step(
        "Import assets",
        [py, "clica.py", "import-assets", "--file", ".\\bundle_assets.csv", "--folder", args.folder, "--on-conflict", "update"],
    )
    run_step(
        "Import threats",
        [py, "clica.py", "import-threats", "--file", ".\\bundle_threats.csv", "--folder", args.folder, "--on-conflict", "update"],
    )
    run_step(
        "Import applied controls",
        [py, "clica.py", "import-applied-controls", "--file", ".\\bundle_controls.csv", "--folder", args.folder, "--on-conflict", "update"],
    )
    run_step("Generate risk assessment CSV", [py, "bundle_risk_assessment_csv.py"])
    run_step(
        "Import risk assessment scenarios",
        [
            py,
            "clica.py",
            "import-risk-assessment",
            "--file",
            ".\\bundle_risk_assessment.csv",
            "--perimeter",
            args.perimeter,
            "--matrix",
            args.matrix,
            "--on-conflict",
            "update",
        ],
    )
    print("== Complete import finished ==")


if __name__ == "__main__":
    main()
