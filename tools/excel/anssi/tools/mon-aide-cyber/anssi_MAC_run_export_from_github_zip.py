#!/usr/bin/env python3
"""Wrapper Python:
- reutilise/telescope le ZIP du repo GitHub
- dezippe temporairement dans le dossier du script
- execute export_referentiels_json.py
- supprime le dossier dezippe (conserve le ZIP)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path


def _progress_bar(current: int, total: int, width: int = 30) -> str:
    if total <= 0:
        return "[telechargement...]"
    ratio = max(0.0, min(1.0, current / total))
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    percent = ratio * 100
    return f"[{bar}] {percent:6.2f}%"


def download_if_needed(zip_url: str, zip_file: Path) -> None:
    if zip_file.exists():
        print(f"ZIP deja present: {zip_file}")
        return
    zip_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"Telechargement du ZIP: {zip_url}")
    started_at = time.time()

    def reporthook(block_num: int, block_size: int, total_size: int) -> None:
        downloaded = block_num * block_size
        if total_size > 0:
            downloaded = min(downloaded, total_size)
        elapsed = max(0.001, time.time() - started_at)
        speed_bps = downloaded / elapsed
        speed_mbps = speed_bps / (1024 * 1024)
        bar = _progress_bar(downloaded, total_size)
        if total_size > 0:
            remain = total_size - downloaded
            eta = int(remain / speed_bps) if speed_bps > 0 else 0
            msg = (
                f"\r{bar}  {downloaded/(1024*1024):7.2f} / {total_size/(1024*1024):7.2f} MiB"
                f"  {speed_mbps:5.2f} MiB/s  ETA {eta:3d}s"
            )
        else:
            msg = (
                f"\r{bar}  {downloaded/(1024*1024):7.2f} MiB"
                f"  {speed_mbps:5.2f} MiB/s"
            )
        print(msg, end="", flush=True)

    urllib.request.urlretrieve(zip_url, zip_file, reporthook=reporthook)
    print()
    print(f"ZIP telecharge: {zip_file}")


def extract_zip(zip_file: Path, extract_parent: Path, extracted_dir: Path) -> None:
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    print(f"Decompression de {zip_file}")
    with zipfile.ZipFile(zip_file, "r") as zf:
        zf.extractall(extract_parent)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_python_script = script_dir / "export_referentiels_json.py"
    default_zip_file = script_dir / "mon-aide-cyber-main.zip"
    default_extract_dir = script_dir / "mon-aide-cyber-main"
    extracted_dir = default_extract_dir

    try:
        parser = argparse.ArgumentParser(
            description="Lance l'export des referentiels a partir du ZIP GitHub de mon-aide-cyber."
        )
        parser.add_argument(
            "--zip-url",
            default="https://github.com/betagouv/mon-aide-cyber/archive/refs/heads/main.zip",
            help="URL du ZIP du repo.",
        )
        parser.add_argument(
            "--zip-file",
            default=str(default_zip_file),
            help="Chemin local du ZIP (cache conserve).",
        )
        parser.add_argument(
            "--python-script",
            default=str(default_python_script),
            help="Chemin vers export_referentiels_json.py.",
        )
        parser.add_argument(
            "--out-dir",
            default=str(script_dir),
            help="Dossier de sortie des JSON.",
        )
        parser.add_argument(
            "--questions-file",
            default="questionnaire_repo.json",
            help="Nom du JSON questions/reponses.",
        )
        parser.add_argument(
            "--mesures-file",
            default="mesures_repo.json",
            help="Nom du JSON mesures.",
        )
        args = parser.parse_args()

        zip_file = Path(args.zip_file).resolve()
        python_script = Path(args.python_script).resolve()
        out_dir = Path(args.out_dir).resolve()
        api_root = extracted_dir / "mon-aide-cyber-api"

        if not python_script.exists():
            raise FileNotFoundError(f"Script Python introuvable: {python_script}")

        out_dir.mkdir(parents=True, exist_ok=True)

        download_if_needed(args.zip_url, zip_file)
        extract_zip(zip_file, script_dir, extracted_dir)
        if not api_root.exists():
            raise FileNotFoundError(
                f"Dossier API introuvable apres dezip: {api_root}"
            )

        cmd = [
            sys.executable,
            str(python_script),
            "--api-root",
            str(api_root),
            "--out-dir",
            str(out_dir),
            "--questions-file",
            args.questions_file,
            "--mesures-file",
            args.mesures_file,
        ]
        print("Generation des JSON...")
        subprocess.run(cmd, check=True)
        print("Termine.")
        print(f"- Questions: {out_dir / args.questions_file}")
        print(f"- Mesures:   {out_dir / args.mesures_file}")
    except KeyboardInterrupt:
        print("Interrompu par l'utilisateur.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir)


if __name__ == "__main__":
    main()
