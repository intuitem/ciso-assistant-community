#!/usr/bin/env python3
"""Exporte 2 JSON a partir du referentiel MonAideCyber.

Sorties:
- questionnaire_repo.json: toutes les thematiques/questions/reponses
- mesures_repo.json: toutes les mesures avec textes resolves depuis les .pug
  + liens questions/reponses -> mesures
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import json5
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "Module 'json5' manquant. Installe-le avec: python3 -m pip install json5"
    ) from exc


def extract_object_literal(content: str, const_name: str) -> str:
    decl = re.search(rf"\bexport\s+const\s+{re.escape(const_name)}\b", content)
    if not decl:
        decl = re.search(rf"\bconst\s+{re.escape(const_name)}\b", content)
    if not decl:
        raise ValueError(f"Impossible de trouver const {const_name}")

    eq_idx = content.find("=", decl.end())
    if eq_idx < 0:
        raise ValueError(f"Impossible de trouver '=' pour {const_name}")
    start = content.find("{", eq_idx)
    if start < 0:
        raise ValueError(f"Impossible de trouver '{{' pour {const_name}")

    i = start
    depth = 0
    in_str = False
    quote = ""
    escaped = False
    in_line_comment = False
    in_block_comment = False
    while i < len(content):
        ch = content[i]
        nxt = content[i + 1] if i + 1 < len(content) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                in_str = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in ("'", '"'):
            in_str = True
            quote = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return content[start : i + 1]
        i += 1

    raise ValueError(f"Objet non ferme pour {const_name}")


def resolve_imports(ts_file: Path) -> dict[str, Path]:
    text = ts_file.read_text(encoding="utf-8")
    imports: dict[str, Path] = {}
    pattern = re.compile(r"import\s+\{\s*([A-Za-z0-9_]+)\s*\}\s+from\s+'([^']+)';")
    for match in pattern.finditer(text):
        symbol = match.group(1)
        rel = match.group(2)
        imports[symbol] = (ts_file.parent / rel).with_suffix(".ts").resolve()
    return imports


def parse_referentiel_questions(api_src: Path) -> dict[str, Any]:
    referentiel_file = api_src / "diagnostic" / "donneesReferentiel.ts"
    imports = resolve_imports(referentiel_file)
    text = referentiel_file.read_text(encoding="utf-8")
    referentiel_obj = extract_object_literal(text, "referentiel")
    entries = re.findall(r"([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_]+)", referentiel_obj)

    out: dict[str, Any] = {}
    for thematique, symbol in entries:
        src_file = imports.get(symbol)
        if src_file is None:
            raise ValueError(f"Import introuvable pour {symbol}")
        content = src_file.read_text(encoding="utf-8")
        literal = extract_object_literal(content, symbol)
        out[thematique] = json5.loads(literal)
    return out


def parse_referentiel_mesures(api_src: Path) -> dict[str, Any]:
    mesures_file = api_src / "diagnostic" / "donneesMesures.ts"
    imports = resolve_imports(mesures_file)
    text = mesures_file.read_text(encoding="utf-8")
    tableau_literal = extract_object_literal(text, "tableauMesures")
    spread_symbols = re.findall(r"\.\.\.([A-Za-z0-9_]+)", tableau_literal)

    merged: dict[str, Any] = {}
    for symbol in spread_symbols:
        src_file = imports.get(symbol)
        if src_file is None:
            raise ValueError(f"Import introuvable pour {symbol}")
        content = src_file.read_text(encoding="utf-8")
        literal = extract_object_literal(content, symbol)
        merged.update(json5.loads(literal))
    return merged


def _line_to_text(line: str) -> tuple[str | None, bool]:
    s = line.strip()
    if not s or s.startswith("//"):
        return None, False
    if s.startswith("include "):
        return None, False
    if s.startswith("|"):
        return s[1:].strip(), False
    m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)(\([^)]*\))?(?:\s+(.*))?$", s)
    if not m:
        return s, False
    tag = m.group(1)
    inline = (m.group(3) or "").strip()
    if tag in {"p", "br"} and not inline:
        return None, True
    if inline:
        return inline, False
    return None, False


def pug_to_text(pug_file: Path, seen: set[Path] | None = None) -> str:
    if seen is None:
        seen = set()
    pug_file = pug_file.resolve()
    if pug_file in seen or not pug_file.exists():
        return ""
    seen.add(pug_file)

    paragraphs: list[str] = []
    current: str = ""
    for raw_line in pug_file.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("include "):
            if current:
                paragraphs.append(current.strip())
                current = ""
            inc = stripped[len("include ") :].strip()
            include_path = (pug_file.parent / inc)
            if include_path.suffix != ".pug":
                include_path = include_path.with_suffix(".pug")
            included = pug_to_text(include_path, seen)
            if included:
                paragraphs.extend([p for p in included.split("\n\n") if p.strip()])
            continue

        text, paragraph_break = _line_to_text(raw_line)
        if paragraph_break:
            if current:
                paragraphs.append(current.strip())
                current = ""
            continue
        if text:
            current = f"{current} {text}".strip() if current else text.strip()

    if current:
        paragraphs.append(current.strip())
    return "\n\n".join([p for p in paragraphs if p.strip()])


def resolve_mesure_texts(api_src: Path, mesures: dict[str, Any]) -> None:
    include_base = api_src / "infrastructure" / "restitution" / "html" / "modeles"
    for payload in mesures.values():
        if not isinstance(payload, dict):
            continue
        for level in ("niveau1", "niveau2"):
            lvl = payload.get(level)
            if not isinstance(lvl, dict):
                continue
            for field in ("pourquoi", "comment"):
                rel = lvl.get(field)
                if isinstance(rel, str):
                    lvl[f"{field}_fichier"] = rel
                    lvl[field] = pug_to_text((include_base / rel).resolve())


def build_mesure_links(questions_ref: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    links: dict[str, list[dict[str, Any]]] = {}

    def add_link(mesure_id: str, link: dict[str, Any]) -> None:
        links.setdefault(mesure_id, []).append(link)

    def process_reponse(
        *,
        thematique: str,
        question: dict[str, Any],
        reponse: dict[str, Any],
        parent: dict[str, str] | None = None,
    ) -> None:
        resultat = reponse.get("resultat") if isinstance(reponse, dict) else None
        mesures = resultat.get("mesures", []) if isinstance(resultat, dict) else []
        for mesure in mesures:
            if not isinstance(mesure, dict):
                continue
            mesure_id = mesure.get("identifiant")
            if not isinstance(mesure_id, str):
                continue
            add_link(
                mesure_id,
                {
                    "thematique": thematique,
                    "question_identifiant": question.get("identifiant"),
                    "question_libelle": question.get("libelle"),
                    "reponse_identifiant": reponse.get("identifiant"),
                    "reponse_libelle": reponse.get("libelle"),
                    "niveau": mesure.get("niveau"),
                    "parent": parent,
                },
            )

    for thematique, bloc in questions_ref.items():
        questions = bloc.get("questions", []) if isinstance(bloc, dict) else []
        for question in questions:
            if not isinstance(question, dict):
                continue
            for reponse in question.get("reponsesPossibles", []) or []:
                if not isinstance(reponse, dict):
                    continue
                process_reponse(thematique=thematique, question=question, reponse=reponse)
                for q_tiroir in reponse.get("questions", []) or []:
                    if not isinstance(q_tiroir, dict):
                        continue
                    for rep_tiroir in q_tiroir.get("reponsesPossibles", []) or []:
                        if not isinstance(rep_tiroir, dict):
                            continue
                        process_reponse(
                            thematique=thematique,
                            question=q_tiroir,
                            reponse=rep_tiroir,
                            parent={
                                "question_identifiant": str(question.get("identifiant")),
                                "question_libelle": str(question.get("libelle")),
                                "reponse_identifiant": str(reponse.get("identifiant")),
                                "reponse_libelle": str(reponse.get("libelle")),
                            },
                        )
    return links


def enrich_mesures_with_links(
    mesures: dict[str, Any], links: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mesure_id, payload in mesures.items():
        enriched = dict(payload)
        enriched["questions_associees"] = links.get(mesure_id, [])
        out[mesure_id] = enriched
    return out


def main() -> None:
    try:
        parser = argparse.ArgumentParser(
            description="Exporte 2 JSON (questionnaire + mesures) depuis le repo MonAideCyber."
        )
        parser.add_argument(
            "--api-root",
            default=str(Path(__file__).resolve().parents[1]),
            help="Chemin vers mon-aide-cyber-api",
        )
        parser.add_argument("--out-dir", default=".", help="Dossier de sortie des JSON")
        parser.add_argument(
            "--questions-file",
            default="questionnaire_repo.json",
            help="Nom du JSON questions/reponses",
        )
        parser.add_argument(
            "--mesures-file",
            default="mesures_repo.json",
            help="Nom du JSON mesures",
        )
        args = parser.parse_args()

        api_src = Path(args.api_root).resolve() / "src"
        out_dir = Path(args.out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        questions_ref = parse_referentiel_questions(api_src)
        mesures_ref = parse_referentiel_mesures(api_src)
        resolve_mesure_texts(api_src, mesures_ref)
        links = build_mesure_links(questions_ref)
        mesures_enriched = enrich_mesures_with_links(mesures_ref, links)

        questionnaire_payload = {
            "source": "mon-aide-cyber-api/src/diagnostic/referentiel",
            "referentiel": questions_ref,
        }
        mesures_payload = {
            "source": "mon-aide-cyber-api/src/diagnostic/mesures + src/infrastructure/restitution/mesures",
            "mesures": mesures_enriched,
        }

        questions_out = out_dir / args.questions_file
        mesures_out = out_dir / args.mesures_file
        questions_out.write_text(
            json.dumps(questionnaire_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        mesures_out.write_text(
            json.dumps(mesures_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"OK: {questions_out}")
        print(f"OK: {mesures_out}")
    except KeyboardInterrupt:
        print("Interrompu par l'utilisateur.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
