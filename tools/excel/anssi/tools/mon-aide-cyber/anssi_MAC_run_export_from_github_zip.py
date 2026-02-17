#!/usr/bin/env python3
"""Wrapper Python:
- reutilise/telescope le ZIP du repo GitHub
- dezippe temporairement dans le dossier du script
- execute anssi_MAC_export_referentiels_json.py
- supprime le dossier dezippe (conserve le ZIP)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from tqdm import tqdm


def normalize_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def display_path(path: Path, base_dir: Path) -> str:
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


def download_if_needed(zip_url: str, zip_file: Path, base_dir: Path) -> None:
    if zip_file.exists():
        print(f'♻️  [INFO] ZIP déjà present: "{display_path(zip_file, base_dir)}"')
        return

    zip_file.parent.mkdir(parents=True, exist_ok=True)
    print(f'📥  [DOWN] Téléchargement du ZIP: "{zip_url}"')

    with urllib.request.urlopen(zip_url) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        with zip_file.open("wb") as out_file, tqdm(
            total=total_size if total_size > 0 else None,
            unit="o",
            unit_scale=True,
            unit_divisor=1024,
            desc="⤵️  ZIP",
        ) as progress:
            while True:
                chunk = response.read(1024 * 64)
                if not chunk:
                    break
                out_file.write(chunk)
                progress.update(len(chunk))

    print(f'✅ [OK] ZIP téléchargé: "{display_path(zip_file, base_dir)}"')


def extract_zip(zip_file: Path, extract_parent: Path, extracted_dir: Path, base_dir: Path) -> None:
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    print(f'📂 [INFO] Décompression de "{display_path(zip_file, base_dir)}"')
    with zipfile.ZipFile(zip_file, "r") as zf:
        zf.extractall(extract_parent)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_python_script = "anssi_MAC_export_referentiels_json.py"
    default_zip_file = "mon-aide-cyber-main.zip"
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
            default=default_zip_file,
            help="Chemin local du ZIP.",
        )
        parser.add_argument(
            "--python-script",
            default=default_python_script,
            help="Chemin vers anssi_MAC_export_referentiels_json.py.",
        )
        parser.add_argument(
            "--out-dir",
            default=".",
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

        zip_file = normalize_path(args.zip_file, script_dir)
        python_script = normalize_path(args.python_script, script_dir)
        out_dir = normalize_path(args.out_dir, script_dir)
        api_root = extracted_dir / "mon-aide-cyber-api"

        if not python_script.exists():
            raise FileNotFoundError(
                f'Script Python introuvable: {display_path(python_script, script_dir)}'
            )

        out_dir.mkdir(parents=True, exist_ok=True)

        download_if_needed(args.zip_url, zip_file, script_dir)
        extract_zip(zip_file, script_dir, extracted_dir, script_dir)
        if not api_root.exists():
            raise FileNotFoundError(
                f'Dossier API introuvable apres dezip: {display_path(api_root, script_dir)}'
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
        print("⚙️  [INFO] Génération des JSON...")
        subprocess.run(cmd, check=True)
        print("✅ [OK] Génération Terminée!")
        # print(f'- Questions: "{display_path(out_dir / args.questions_file, script_dir)}"')
        # print(f'- Mesures:   "{display_path(out_dir / args.mesures_file, script_dir)}"')
    except KeyboardInterrupt:
        print("❌ [ERROR] Interrompu par l'utilisateur.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ [ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        print("🗑️  [INFO] Suppression des fichiers inutiles...")
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir)


if __name__ == "__main__":
    main()
