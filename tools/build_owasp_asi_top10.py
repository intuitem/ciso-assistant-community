"""Build the OWASP Top 10 for Agentic Applications 2026 library from the published PDF.

    pdftotext -layout OWASP-Top-10-for-Agentic-Applications-2026.pdf asi.txt
    python tools/build_owasp_asi_top10.py asi.txt backend/library/libraries/owasp-asi-top-10-2026.yaml

Every string is transcribed verbatim from the source. Threats are the ten ASI entries;
requirement nodes are the "Prevention and Mitigation Guidelines" items as OWASP numbers them.
"""

import re
import sys
from collections import OrderedDict

import yaml

LIB_ID = "owasp-asi-top-10-2026"
BASE = f"urn:intuitem:risk:{{}}:{LIB_ID}"

SUBHEADS = (
    "Description",
    "Common Examples of the Vulnerability",
    "Example Attack Scenarios",
    "Prevention and Mitigation Guidelines",
    "References",
)

# a lead label OWASP wrote for the item, e.g. "Least Agency and Least Privilege for Tools."
LABEL = re.compile(r"^([A-Z][A-Za-z0-9&,'\-/ ]{3,60}?)\s*[:.]\s+(?=[A-Z(])")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def join(acc: str, line: str) -> str:
    """Append a wrapped line. A line ending in "word-" is a hyphen split by the
    line break, so close it up; anything else takes a separating space."""
    tail = line.strip()
    if re.search(r"\w-$", acc):
        return acc + tail
    return f"{acc} {tail}" if acc else tail


def is_noise(line: str) -> bool:
    t = line.strip()
    return (
        not t or t.startswith("genai.owasp.org") or bool(re.fullmatch(r"Page \d+", t))
    )


def split_entries(lines):
    """Locate the ten ASI body sections (skipping the table of contents)."""
    marks = []
    for i, line in enumerate(lines):
        t = line.strip()
        m = re.match(r"^ASI(\d\d):\s*(.+)$", t)
        if m and len(t) < 70 and not re.search(r"\d+$", t):
            marks.append((i, m.group(1), m.group(2).strip()))
    # TOC entries carry trailing page numbers and sit in the first pages
    marks = [m for m in marks if m[0] > 260]
    out = []
    for j, (i, num, title) in enumerate(marks):
        end = marks[j + 1][0] if j + 1 < len(marks) else len(lines)
        # headings set in large type wrap onto following lines, up to the first subheading
        parts, k = [title], i + 1
        while k < end and lines[k].strip() not in SUBHEADS:
            if not is_noise(lines[k]):
                parts.append(lines[k].strip())
            k += 1
            assert k - i < 6, f"no subheading found after ASI{num} heading"
        out.append((num, clean(" ".join(parts)), lines[k:end]))
    assert len(out) == 10, f"expected 10 ASI entries, found {len(out)}"
    return out


def subsection(body, header):
    start = next((i for i, l in enumerate(body) if l.strip() == header), None)
    if start is None:
        return []
    out = []
    for line in body[start + 1 :]:
        if line.strip() in SUBHEADS:
            break
        out.append(line)
    return out


def numbered_items(block):
    items, cur = [], None
    for line in block:
        if is_noise(line):
            continue
        m = re.match(r"^\s+(\d+)\.\s+(.*)$", line)
        if m:
            if cur is not None:
                items.append(cur)
            cur = clean(m.group(2))
        elif cur is not None:
            cur = join(cur, line)
    if cur is not None:
        items.append(cur)
    return items


def paragraphs(block):
    acc = ""
    for line in block:
        if not is_noise(line):
            acc = join(acc, line)
    return clean(acc)


def build(src_path):
    lines = open(src_path, encoding="utf-8").read().split("\n")
    threats, nodes = [], []

    for num, title, body in split_entries(lines):
        eid = f"ASI{num}"
        slug = eid.lower()
        description = paragraphs(subsection(body, "Description"))

        threats.append(
            OrderedDict(
                urn=f"{BASE.format('threat')}:{slug}",
                ref_id=eid,
                name=title,
                description=description,
            )
        )

        nodes.append(
            OrderedDict(
                urn=f"{BASE.format('req_node')}:{slug}",
                assessable=False,
                depth=1,
                ref_id=eid,
                name=title,
                description=description,
            )
        )

        mitigations = numbered_items(
            subsection(body, "Prevention and Mitigation Guidelines")
        )
        assert mitigations, f"no mitigations parsed for {eid}"

        for k, text in enumerate(mitigations, start=1):
            node = OrderedDict(
                urn=f"{BASE.format('req_node')}:{slug}.{k}",
                assessable=True,
                depth=2,
                parent_urn=f"{BASE.format('req_node')}:{slug}",
                ref_id=f"{eid}.{k}",
            )
            m = LABEL.match(text)
            if m and len(m.group(1).split()) <= 8:
                node["name"] = m.group(1).strip()
            node["description"] = text
            node["threats"] = [f"{BASE.format('threat')}:{slug}"]
            nodes.append(node)

    return threats, nodes


def main():
    src, dst = sys.argv[1], sys.argv[2]
    threats, nodes = build(src)

    name = "OWASP Top 10 for Agentic Applications 2026"
    description = (
        "The ten most critical security risks for agentic AI applications, published by "
        "the OWASP Gen AI Security Project - Agentic Security Initiative. Threats are the "
        "ten ASI entries; requirements are transcribed from each entry's "
        '"Prevention and Mitigation Guidelines". '
        "Scope a single audit to one agentic application. "
        "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
    )

    library = OrderedDict(
        urn=f"urn:intuitem:risk:library:{LIB_ID}",
        locale="en",
        ref_id=LIB_ID,
        name=name,
        description=description,
        copyright="OWASP - Creative Commons Attribution-ShareAlike 4.0",
        version=1,
        publication_date="2025-12-09",
        provider="OWASP",
        packager="intuitem",
        objects=OrderedDict(
            threats=threats,
            framework=OrderedDict(
                urn=f"urn:intuitem:risk:framework:{LIB_ID}",
                ref_id=LIB_ID,
                name=name,
                description=description,
                requirement_nodes=nodes,
            ),
        ),
    )

    yaml.add_representer(
        OrderedDict,
        lambda d, x: d.represent_mapping("tag:yaml.org,2002:map", x.items()),
    )
    with open(dst, "w", encoding="utf-8") as fh:
        yaml.dump(library, fh, allow_unicode=True, sort_keys=False, width=100)

    a = sum(1 for n in nodes if n["assessable"])
    named = sum(1 for n in nodes if n["assessable"] and "name" in n)
    print(
        f"threats={len(threats)} nodes={len(nodes)} assessable={a} with-name={named} -> {dst}"
    )


if __name__ == "__main__":
    main()
