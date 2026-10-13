#!/usr/bin/env python
"""Deep consistency check: YAML library vs original CIS PDF (ToC + body headings)."""

import re
import sys
import unicodedata

import fitz
import yaml

REF_START_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")
TRAILER_DOTS_RE = re.compile(r"(?:\.\s*){2,}\d+\s*$")
TRAILER_TAG_RE = re.compile(r"(\((?:Automated|Manual)\))\s*\.*\s*\d+\s*$")
TAG_RE = re.compile(r"\s*\((Automated|Manual)\)$")
NOISE_RE = re.compile(r"^(Page \d+|Internal Only.*|TLP:.*)$")


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"-\s+", "-", s)  # hyphen linebreak artifacts
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def join_lines(parts):
    out = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out.endswith("-"):
            out += p
        elif out:
            out += " " + p
        else:
            out = p
    return out


def parse_toc(doc):
    """Return ordered [(ref, title, tag_or_None)] from the Table of Contents."""
    entries = []
    open_ref, open_parts = None, []
    in_toc = False
    for page in doc:
        text = page.get_text()
        if "Table of Contents" in text:
            in_toc = True
        if not in_toc:
            continue
        has_leaders = text.count("....") >= 2
        if not has_leaders and open_ref is None and entries:
            break  # left the ToC
        for raw in text.splitlines():
            line = raw.strip()
            if not line or NOISE_RE.match(line) or line == "Table of Contents":
                continue
            if open_ref is None:
                m = REF_START_RE.match(line)
                if not m:
                    continue
                open_ref, open_parts = m.group(1), [m.group(2)]
            else:
                open_parts.append(line)
            joined = join_lines(open_parts)
            t = TRAILER_DOTS_RE.search(joined)
            if t:
                title = joined[: t.start()].rstrip(" .")
            else:
                t = TRAILER_TAG_RE.search(joined)
                if t:
                    title = joined[: t.start()] + t.group(1)
            if t:
                tag_m = TAG_RE.search(title)
                tag = tag_m.group(1) if tag_m else None
                if tag_m:
                    title = title[: tag_m.start()].strip()
                entries.append((open_ref, title, tag))
                open_ref, open_parts = None, []
    return entries


def parse_body(doc, known_refs=None):
    """Return {ref: (title, tag)} from recommendation headings above 'Profile Applicability:'."""
    out = {}
    for page in doc:
        text = page.get_text()
        if "Profile Applicability:" not in text:
            continue
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not NOISE_RE.match(line.strip())
        ]
        for i, line in enumerate(lines):
            if not line.startswith("Profile Applicability:"):
                continue
            for j in range(i - 1, max(-1, i - 10), -1):
                m = REF_START_RE.match(lines[j])
                if m and (known_refs is None or m.group(1) in known_refs):
                    joined = join_lines([m.group(2)] + lines[j + 1 : i])
                    tag_m = TAG_RE.search(joined)
                    tag = tag_m.group(1) if tag_m else None
                    if tag_m:
                        joined = joined[: tag_m.start()].strip()
                    out[m.group(1)] = (joined, tag)
                    break
    return out


def yaml_nodes(path):
    with open(path) as f:
        lib = yaml.safe_load(f)
    fw = lib["objects"]["framework"]
    nodes = []
    for n in fw["requirement_nodes"]:
        title = n.get("name") or ""
        if title.endswith("…") and n.get("description"):
            title = n["description"]
        igs = n.get("implementation_groups") or []
        tag = {"A": "Automated", "M": "Manual"}.get(igs[0]) if igs else None
        nodes.append(
            (
                n["ref_id"],
                title,
                tag if n.get("assessable") else None,
                bool(n.get("assessable")),
            )
        )
    return lib, nodes


def check(pdf_path, yaml_path):
    doc = fitz.open(pdf_path)
    toc = parse_toc(doc)
    body = parse_body(doc, known_refs={r for r, _, _ in toc})
    lib, nodes = yaml_nodes(yaml_path)

    report = {
        "toc_entries": len(toc),
        "body_entries": len(body),
        "yaml_nodes": len(nodes),
        "issues": [],
    }
    say = report["issues"].append

    toc_map = {r: (t, g) for r, t, g in toc}
    if len(toc_map) != len(toc):
        from collections import Counter

        dupes = [k for k, v in Counter(r for r, _, _ in toc).items() if v > 1]
        say(f"TOC-PARSE duplicate refs in parsed ToC: {dupes}")
    yaml_map = {r: (t, g, a) for r, t, g, a in nodes}

    # --- coverage: every YAML node must exist in ToC, matching title & tag
    for ref, title, tag, assessable in nodes:
        if ref not in toc_map:
            say(f"YAML-ONLY {ref} not found in ToC: {title[:60]!r}")
            continue
        t_title, t_tag = toc_map[ref]
        if norm(title) != norm(t_title):
            say(
                f"TITLE-DIFF(ToC) {ref}:\n      yaml={norm(title)!r}\n      toc ={norm(t_title)!r}"
            )
        if tag != t_tag:
            say(f"TAG-DIFF(ToC) {ref}: yaml={tag} toc={t_tag}")
        if assessable != (t_tag is not None):
            say(f"ASSESSABLE-DIFF {ref}: yaml_assessable={assessable} toc_tag={t_tag}")

    # --- ToC entries absent from YAML: legit only if pruned empty section
    toc_children = {}
    for r, _, g in toc:
        parts = r.split(".")
        for k in range(1, len(parts)):
            toc_children.setdefault(".".join(parts[:k]), []).append((r, g))
    for ref, title, tag in toc:
        if ref in yaml_map:
            continue
        if tag is None:
            desc = toc_children.get(ref, [])
            if any(g for _, g in desc):
                say(
                    f"MISSING-SECTION {ref} pruned but has tagged descendants: {title[:60]!r}"
                )
            # else: legitimately pruned
        else:
            say(f"MISSING-RECO {ref} ({tag}) in ToC but not in YAML: {title[:60]!r}")

    # --- body cross-check (assessable only)
    for ref, (b_title, b_tag) in body.items():
        if ref not in yaml_map:
            say(
                f"BODY-ONLY {ref} has a body section but no YAML node: {b_title[:60]!r}"
            )
            continue
        y_title, y_tag, _ = yaml_map[ref]
        if b_tag and y_tag != b_tag:
            say(f"TAG-DIFF(body) {ref}: yaml={y_tag} body={b_tag}")
        if b_tag and norm(y_title) != norm(b_title):
            say(
                f"TITLE-DIFF(body) {ref}:\n      yaml={norm(y_title)!r}\n      body={norm(b_title)!r}"
            )
    for ref, (_, _, a) in yaml_map.items():
        if a and ref not in body:
            say(f"NO-BODY {ref} assessable in YAML but no body heading found")

    # --- ordering: YAML node order must match ToC order (restricted to shared refs)
    shared = [r for r, _, _ in toc if r in yaml_map]
    yaml_order = [r for r, _, _, _ in nodes if r in toc_map]
    if shared != yaml_order:
        diverged = False
        for a, b in zip(shared, yaml_order):
            if a != b:
                say(f"ORDER-DIFF first divergence: toc={a} yaml={b}")
                diverged = True
                break
        if not diverged:
            say(
                f"ORDER-DIFF length mismatch: toc has {len(shared)} shared refs, yaml has {len(yaml_order)}"
            )

    # --- metadata (version line may sit past page 1, like cover_metadata's doc[:3] scan)
    cover = "\n".join(page.get_text() for page in doc[:3])
    vm = re.search(r"[vV](\d+(?:\.\d+)*)\s*[-–]\s*(\d{2})-(\d{2})-(\d{4})", cover)
    if vm:
        v, mm, dd, yyyy = vm.groups()
        if f"v{v}" not in lib["description"]:
            say(f"META version v{v} not in description {lib['description']!r}")
        pub = str(lib["publication_date"])
        if pub != f"{yyyy}-{mm}-{dd}":
            say(f"META publication_date {pub} != cover {yyyy}-{mm}-{dd}")
    else:
        say("META could not re-read cover version line")
    doc.close()
    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: deep_check.py <benchmark.pdf> <library.yaml>")
    rep = check(sys.argv[1], sys.argv[2])
    status = "CLEAN" if not rep["issues"] else f"{len(rep['issues'])} issue(s)"
    print(
        f"toc={rep['toc_entries']} body={rep['body_entries']} yaml={rep['yaml_nodes']} -> {status}"
    )
    for iss in rep["issues"]:
        print("  ", iss)
    sys.exit(1 if rep["issues"] else 0)
