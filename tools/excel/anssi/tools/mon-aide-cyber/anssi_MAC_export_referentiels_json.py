#!/usr/bin/env python3
"""
MonAideCyber - JSON Referential Exporter
========================================

Exports the MonAideCyber questionnaire/measures data from TypeScript sources
into two JSON files.

Outputs
-------
- `questionnaire_repo.json`
- `mesures_repo.json`

Run
---
python anssi_MAC_export_referentiels_json.py --api-root <path-to-mon-aide-cyber-api>
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import json5
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ModuleNotFoundError(
        "Missing module 'json5'. Install it with: python3 -m pip install json5"
    ) from exc


IMPORT_RE = re.compile(r"import\s+\{\s*([A-Za-z0-9_]+)\s*\}\s+from\s+'([^']+)';")
KV_SYMBOL_RE = re.compile(r"([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_]+)")


def display_path(path: Path, base_dir: Path) -> str:
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_imports(ts_file: Path) -> dict[str, Path]:
    imports: dict[str, Path] = {}
    for match in IMPORT_RE.finditer(read_text(ts_file)):
        symbol, rel = match.groups()
        imports[symbol] = (ts_file.parent / rel).with_suffix(".ts").resolve()
    return imports


def extract_object_literal(content: str, start_at: int, label: str) -> str:
    start = content.find("{", start_at)
    if start < 0:
        raise ValueError(f"Could not find '{{' for {label}")

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

    raise ValueError(f"Unclosed object for {label}")


def parse_const_object(content: str, const_name: str) -> dict[str, Any]:
    decl = re.search(rf"\bexport\s+const\s+{re.escape(const_name)}\b", content)
    if not decl:
        decl = re.search(rf"\bconst\s+{re.escape(const_name)}\b", content)
    if not decl:
        raise ValueError(f"Could not find const {const_name}")
    eq_idx = content.find("=", decl.end())
    if eq_idx < 0:
        raise ValueError(f"Could not find '=' for {const_name}")
    return json5.loads(extract_object_literal(content, eq_idx, f"const {const_name}"))


def parse_const_object_literal(content: str, const_name: str) -> str:
    decl = re.search(rf"\bexport\s+const\s+{re.escape(const_name)}\b", content)
    if not decl:
        decl = re.search(rf"\bconst\s+{re.escape(const_name)}\b", content)
    if not decl:
        raise ValueError(f"Could not find const {const_name}")
    eq_idx = content.find("=", decl.end())
    if eq_idx < 0:
        raise ValueError(f"Could not find '=' for {const_name}")
    return extract_object_literal(content, eq_idx, f"const {const_name}")


def parse_field_object(content: str, field_name: str) -> dict[str, Any]:
    field = re.search(rf"\b{re.escape(field_name)}\s*:", content)
    if not field:
        raise ValueError(f"Could not find field {field_name}")
    return json5.loads(
        extract_object_literal(content, field.end(), f"champ {field_name}")
    )


def parse_referentiel_questions(api_src: Path) -> dict[str, Any]:
    file = api_src / "diagnostic" / "donneesReferentiel.ts"
    imports = parse_imports(file)
    content = read_text(file)
    literal = parse_const_object_literal(content, "referentiel")
    entries = KV_SYMBOL_RE.findall(literal)
    out: dict[str, Any] = {}
    for thematique, symbol in entries:
        src = imports.get(symbol)
        if not src:
            raise ValueError(f"Missing import for {symbol}")
        out[thematique] = parse_const_object(read_text(src), symbol)
    return out


def parse_referentiel_mesures(api_src: Path) -> dict[str, Any]:
    file = api_src / "diagnostic" / "donneesMesures.ts"
    imports = parse_imports(file)
    content = read_text(file)
    literal = parse_const_object_literal(content, "tableauMesures")
    symbols = re.findall(r"\.\.\.([A-Za-z0-9_]+)", literal)

    merged: dict[str, Any] = {}
    for symbol in symbols:
        src = imports.get(symbol)
        if not src:
            raise ValueError(f"Missing import for {symbol}")
        merged.update(parse_const_object(read_text(src), symbol))
    return merged


def parse_transcripteur(api_src: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    trans_dir = api_src / "infrastructure" / "adaptateurs" / "transcripteur"
    file = trans_dir / "adaptateurTranscripteur.ts"
    imports = parse_imports(file)
    content = read_text(file)

    thematiques: dict[str, Any] = {}
    thematiques_field = re.search(r"\bthematiques\s*:", content)
    if not thematiques_field:
        raise ValueError("Could not find 'thematiques' field")
    literal = extract_object_literal(content, thematiques_field.end(), "thematiques")
    for thematique, symbol in KV_SYMBOL_RE.findall(literal):
        src = imports.get(symbol)
        if not src:
            raise ValueError(f"Missing transcripteur import for {symbol}")
        thematiques[thematique] = parse_const_object(read_text(src), symbol)

    conditions = parse_field_object(content, "conditionsPerimetre")
    return thematiques, conditions


def _indent_level(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _append_text(base: str, chunk: str) -> str:
    chunk = chunk.strip()
    if not chunk:
        return base
    return f"{base} {chunk}".strip() if base else chunk


def _extract_tag_line(line: str) -> tuple[str, str, str]:
    """Return (tag, attrs, inline_text). If the tag is invalid, tag=''."""
    s = line.strip()
    match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)(\([^)]*\))?(?:\s+(.*))?$", s)
    if not match:
        return "", "", s
    tag = match.group(1)
    attrs = (match.group(2) or "").strip()
    inline = (match.group(3) or "").strip()
    return tag, attrs, inline


def _render_anchor(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Render a Pug <a> tag to text/Markdown and return (text, next_idx)."""
    raw = lines[start_idx]
    indent = _indent_level(raw)
    tag, attrs, inline = _extract_tag_line(raw)
    if tag != "a":
        return "", start_idx + 1

    href = ""
    if attrs:
        href_match = re.search(r'href\s*=\s*[\'"]([^\'"]+)[\'"]', attrs)
        if href_match:
            href = href_match.group(1).strip()

    label_parts: list[str] = []
    if inline:
        label_parts.append(inline)

    i = start_idx + 1
    while i < len(lines):
        child_raw = lines[i]
        child_stripped = child_raw.strip()

        if not child_stripped:
            i += 1
            continue

        if _indent_level(child_raw) <= indent:
            break

        if child_stripped.startswith("|"):
            child_text = child_stripped[1:].strip()
            if child_text:
                label_parts.append(child_text)
            i += 1
            continue

        break

    label = " ".join(label_parts).strip()
    if not href:
        return label, i
    if not label:
        return href, i
    if label == href:
        return label, i
    return f"[{label}]({href})", i


def _flush_li(current: str, li_text: str) -> str:
    li_text = li_text.strip()
    if not li_text:
        return current
    bullet = f"\t• {li_text}"
    return f"{current}\n{bullet}" if current else bullet


def pug_to_text(pug_file: Path, seen: set[Path] | None = None) -> str:
    if seen is None:
        seen = set()
    pug_file = pug_file.resolve()
    if pug_file in seen or not pug_file.exists():
        return ""
    seen.add(pug_file)

    paragraphs: list[str] = []
    current = ""

    lines = read_text(pug_file).splitlines()
    i = 0

    li_indent: int | None = None
    li_text = ""

    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()
        indent = _indent_level(raw_line)

        if li_indent is not None and stripped and indent <= li_indent:
            current = _flush_li(current, li_text)
            li_indent = None
            li_text = ""

            # If we leave a list and move to another block, force
            # a new paragraph to avoid appending text to the last <li>.
            next_tag, _, _ = _extract_tag_line(raw_line)
            if current and next_tag not in {"li", "ul"} and not stripped.startswith("|"):
                paragraphs.append(current.strip())
                current = ""

        if not stripped or stripped.startswith("//"):
            i += 1
            continue

        if stripped.startswith("include "):
            if current:
                paragraphs.append(current.strip())
                current = ""
            include_path = (pug_file.parent / stripped[len("include ") :].strip())
            if include_path.suffix != ".pug":
                include_path = include_path.with_suffix(".pug")
            included = pug_to_text(include_path, seen)
            if included:
                paragraphs.extend([p for p in included.split("\n\n") if p.strip()])
            i += 1
            continue

        if stripped.startswith("|"):
            text = stripped[1:].strip()
            if li_indent is not None and indent > li_indent:
                li_text = _append_text(li_text, text)
            else:
                current = _append_text(current, text)
            i += 1
            continue

        tag, _attrs, inline = _extract_tag_line(raw_line)
        if not tag:
            if li_indent is not None and indent > (li_indent or 0):
                li_text = _append_text(li_text, stripped)
            else:
                current = _append_text(current, stripped)
            i += 1
            continue

        if tag in {"p", "br"} and not inline:
            if current:
                paragraphs.append(current.strip())
                current = ""
            i += 1
            continue

        if tag == "li":
            if li_indent is not None:
                current = _flush_li(current, li_text)
            li_indent = indent
            li_text = inline.strip()
            i += 1
            continue

        if tag == "a":
            link_text, next_i = _render_anchor(lines, i)
            if li_indent is not None and indent > li_indent:
                li_text = _append_text(li_text, link_text)
            else:
                current = _append_text(current, link_text)
            i = next_i
            continue

        if inline:
            if li_indent is not None and indent > li_indent:
                li_text = _append_text(li_text, inline)
            else:
                current = _append_text(current, inline)

        i += 1

    if li_indent is not None:
        current = _flush_li(current, li_text)

    if current:
        paragraphs.append(current.strip())

    return "\n\n".join([p for p in paragraphs if p.strip()])


def resolve_mesure_texts(api_src: Path, mesures: dict[str, Any]) -> None:
    include_base = api_src / "infrastructure" / "restitution" / "html" / "modeles"
    for payload in mesures.values():
        if not isinstance(payload, dict):
            continue
        for level_name, lvl in payload.items():
            if not (isinstance(level_name, str) and level_name.startswith("niveau")):
                continue
            if not isinstance(lvl, dict):
                continue
            for field in ("pourquoi", "comment"):
                rel = lvl.get(field)
                if isinstance(rel, str):
                    lvl[f"{field}_fichier"] = rel
                    lvl[field] = pug_to_text((include_base / rel).resolve())


def info_bulles_to_texts(api_src: Path, info_bulles: list[str] | None) -> list[str]:
    if not info_bulles:
        return []
    base = api_src / "infrastructure" / "adaptateurs" / "transcripteur" / "info-bulles"
    return [pug_to_text((base / rel).resolve()) for rel in info_bulles]


def index_transcripteur_questions(thematique_meta: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    if not isinstance(thematique_meta, dict):
        return index

    def visit(question: dict[str, Any]) -> None:
        identifiant = question.get("identifiant")
        if isinstance(identifiant, str):
            index[identifiant] = question
        for reponse in question.get("reponses", []) or []:
            child = reponse.get("question") if isinstance(reponse, dict) else None
            if isinstance(child, dict):
                visit(child)

    for groupe in thematique_meta.get("groupes", []) or []:
        if isinstance(groupe, dict):
            for question in groupe.get("questions", []) or []:
                if isinstance(question, dict):
                    visit(question)
    return index


def enrich_question_tree(api_src: Path, question: dict[str, Any], index: dict[str, dict[str, Any]]) -> None:
    identifiant = question.get("identifiant")
    meta = index.get(identifiant) if isinstance(identifiant, str) else None
    if isinstance(meta, dict):
        if "perimetre" in meta:
            question["perimetre"] = meta["perimetre"]
        if "type" in meta:
            question["type_transcripteur"] = meta["type"]
        info_bulles = meta.get("info-bulles")
        if isinstance(info_bulles, list):
            question["info-bulles"] = info_bulles
            question["info-bulles-textes"] = info_bulles_to_texts(api_src, info_bulles)

    for reponse in question.get("reponsesPossibles", []) or []:
        if isinstance(reponse, dict):
            for child in reponse.get("questions", []) or []:
                if isinstance(child, dict):
                    enrich_question_tree(api_src, child, index)


def enrich_referentiel_with_transcripteur(
    api_src: Path,
    referentiel: dict[str, Any],
    thematiques: dict[str, Any],
    conditions_perimetre: dict[str, Any],
) -> None:
    section_fields = ("description", "libelle", "styles", "localisationIllustration")
    for thematique, bloc in referentiel.items():
        if not isinstance(bloc, dict):
            continue
        meta = thematiques.get(thematique)
        if not isinstance(meta, dict):
            continue
        for field in section_fields:
            if field in meta:
                bloc[field] = meta[field]

        index = index_transcripteur_questions(meta)
        for question in bloc.get("questions", []) or []:
            if isinstance(question, dict):
                enrich_question_tree(api_src, question, index)

        # Reorder keys to keep perimeter-related section fields first.
        ordered: dict[str, Any] = {}
        for field in section_fields:
            if field in bloc:
                ordered[field] = bloc[field]
        for key, value in bloc.items():
            if key not in ordered:
                ordered[key] = value
        referentiel[thematique] = ordered

    referentiel["_conditionsPerimetre"] = conditions_perimetre


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def export_referentiels_json(
    api_root: Path,
    out_dir: Path,
    questions_file: str = "questionnaire_repo.json",
    mesures_file: str = "mesures_repo.json",
) -> tuple[Path, Path]:
    """Single entry point: export questions+measures and return output paths."""
    api_src = api_root.resolve() / "src"
    out_dir = out_dir.resolve()

    questions_ref = parse_referentiel_questions(api_src)
    trans_thematiques, conditions = parse_transcripteur(api_src)
    enrich_referentiel_with_transcripteur(
        api_src, questions_ref, trans_thematiques, conditions
    )

    mesures_ref = parse_referentiel_mesures(api_src)
    resolve_mesure_texts(api_src, mesures_ref)

    questions_out = out_dir / questions_file
    mesures_out = out_dir / mesures_file
    dump_json(
        questions_out,
        {
            "source": "mon-aide-cyber-api/src/diagnostic/referentiel",
            "referentiel": questions_ref,
        },
    )
    dump_json(
        mesures_out,
        {
            "source": "mon-aide-cyber-api/src/diagnostic/mesures + src/infrastructure/restitution/mesures",
            "mesures": mesures_ref,
        },
    )
    return questions_out, mesures_out


def main() -> None:
    try:
        parser = argparse.ArgumentParser(
            description="Export 2 JSON files (questionnaire + measures) from the MonAideCyber repository."
        )
        parser.add_argument(
            "--api-root",
            default=str(Path(__file__).resolve().parents[1]),
            help="Path to mon-aide-cyber-api",
        )
        parser.add_argument("--out-dir", default=".", help="Output directory for JSON files")
        parser.add_argument("--questions-file", default="questionnaire_repo.json")
        parser.add_argument("--mesures-file", default="mesures_repo.json")
        args = parser.parse_args()

        script_dir = Path(__file__).resolve().parent
        questions_out, mesures_out = export_referentiels_json(
            api_root=Path(args.api_root),
            out_dir=Path(args.out_dir),
            questions_file=args.questions_file,
            mesures_file=args.mesures_file,
        )

        print(f"- Questions: \"{display_path(questions_out, script_dir)}\"")
        print(f"- Measures:  \"{display_path(mesures_out, script_dir)}\"")
    except KeyboardInterrupt:
        print("❌ [ERROR] Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ [ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
