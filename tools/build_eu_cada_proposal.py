#!/usr/bin/env python3
"""Build the EU Cloud and AI Development Act (proposal) Union assurance levels library.

Source: Council document ST-10104-2026-ADD-1 (annexes to COM(2026) 502 final, 3 June 2026),
https://data.consilium.europa.eu/doc/document/ST-10104-2026-ADD-1/en/pdf

Annex II gives one section per Union assurance level, criteria (a)-(k) as requirements and
their sub-points i-iv as child requirements. Groups are cumulative (Article 20(1)): a level-n
criterion is in UAL-n and every higher group. Annex III audit evidence (criteria A-K) is the
typical evidence of the matching level 2-4 criteria.

Usage:
    python tools/build_eu_cada_proposal.py <annexes.pdf> backend/library/libraries/eu-cada-proposal.yaml
"""

import itertools
import re
import sys
from pathlib import Path

import yaml


class NoAliasDumper(yaml.SafeDumper):
    # shared lists (e.g. group lists) must be written out in full, not as &id/*id aliases
    def ignore_aliases(self, data):
        return True


src, out = sys.argv[1], sys.argv[2]
if src.endswith(".pdf"):
    import pypdfium2

    pdf = pypdfium2.PdfDocument(src)
    raw = "\n".join(page.get_textpage().get_text_range() for page in pdf)
else:
    raw = Path(src).read_text(encoding="utf-8")
raw = raw.replace("\r\n", "\n").replace(
    "\ufffe", "-"
)  # PDF line endings and soft-hyphen artefact
raw = re.sub(r"\nEN \d+ EN\n", "\n", raw)
lines = raw.split("\n")


def section(start, end):
    i = next(n for n, l in enumerate(lines) if l.startswith(start))
    j = next(n for n, l in enumerate(lines) if n > i and l.startswith(end))
    return lines[i:j]


def clean(chunk):
    return re.sub(r"\s+", " ", " ".join(chunk)).strip()


PREFIX = "urn:intuitem:risk:req_node:eu-cada-proposal"
LEVELS = {
    1: "Union assurance level 1",
    2: "Union assurance level 2",
    3: "Union assurance level 3",
    4: "Union assurance level 4",
}

# Annex III: one evidence block per letter, applies to levels 2-4 (Annex III wording)
annex3 = lines[next(n for n, l in enumerate(lines) if l.startswith("ANNEX III")) :]
evidence, cur = {}, None
for l in annex3:
    m = re.match(r"^\d+\. Audit criteri(?:on|a) ([A-K]) ?[–-] ?(.*)", l)
    if m:
        cur = m.group(1).lower()
        evidence[cur] = [
            f"Annex III, audit criterion {m.group(1)} – {m.group(2).strip()}"
        ]
    elif cur:
        evidence[cur].append(l)


def fmt_evidence(v):
    # heading may wrap onto following lines until the body starts
    k = next(n for n, l in enumerate(v) if l.startswith("The auditing organisation"))
    body = re.sub(
        r" ?(\(\d+\)|\d\.\d\. ) *",
        lambda m: "\n" + m.group(1).strip() + " ",
        clean(v[k:]),
    )
    return clean(v[:k]) + "\n" + body.strip()


intro3 = clean(
    annex3[
        2 : next(
            n for n, l in enumerate(annex3) if l.startswith("1. Audit criterion A")
        )
    ]
)
NOTE = " ".join(
    x
    for x in re.split(r"(?<=\.) ", intro3)
    if x.startswith(("This Annex is indicative", "While the evidence"))
)
assert NOTE.count(".") >= 2, NOTE
evidence = {
    k: f"{fmt_evidence(v)}\n\nNote (Annex III): {NOTE}" for k, v in evidence.items()
}
assert sorted(evidence) == list("abcdefghijk"), sorted(evidence)

nodes = []
annex2 = section("ANNEX II", "ANNEX III")
intro_end = next(
    n for n, l in enumerate(annex2) if l.startswith("1. Union assurance level 1")
)
nodes.append(
    {
        "urn": f"{PREFIX}:scope",
        "assessable": False,
        "depth": 1,
        "ref_id": "Annex II",
        "name": "Criteria for Union assurance levels",
        "description": clean(annex2[2:intro_end]),
        "implementation_groups": [f"UAL-{i}" for i in LEVELS],
    }
)

body = annex2[intro_end:]
level_starts = [
    n
    for n, l in enumerate(body)
    if re.match(r"^[1-4]\. Union assurance level [1-4]$", l.strip())
]
level_starts.append(len(body))
for li, (a, b) in enumerate(itertools.pairwise(level_starts), start=1):
    blk = body[a + 1 : b]
    lvl_urn = f"{PREFIX}:ual-{li}"
    # Article 20(1): a higher-level audit must also meet every lower-level criterion
    igs = [f"UAL-{i}" for i in LEVELS if i >= li]
    nodes.append(
        {
            "urn": lvl_urn,
            "assessable": False,
            "depth": 1,
            "ref_id": f"UAL-{li}",
            "name": LEVELS[li],
            "implementation_groups": igs,
        }
    )
    sub2 = next(n for n, l in enumerate(blk) if l.startswith(f"{li}.2."))
    crit_blk, scope2 = blk[:sub2], blk[sub2:]
    head_end = next(n for n, l in enumerate(crit_blk) if l.startswith("(a)"))
    nodes.append(
        {
            "urn": f"{lvl_urn}:{li}.1",
            "assessable": False,
            "depth": 2,
            "parent_urn": lvl_urn,
            "ref_id": f"{li}.1",
            "description": re.sub(rf"^{li}\.1\. ", "", clean(crit_blk[:head_end])),
            "implementation_groups": igs,
        }
    )
    # split criteria (a)..(k), then sub-points i..iv
    crits, cur = [], None
    for l in crit_blk[head_end:]:
        m = re.match(r"^\(([a-k])\) ?(.*)", l)
        if m:
            cur = [m.group(1), [m.group(2)]]
            crits.append(cur)
        else:
            cur[1].append(l)
    letters = [c[0] for c in crits]
    assert letters == list("abcdefghijk"[: len(letters)]), letters
    for letter, chunk in crits:
        parts = re.split(r"(?:^|\n)(i{1,3}|iv)\. ", "\n".join(chunk))
        crit_urn = f"{lvl_urn}:{li}.1:{letter}"
        node = {
            "urn": crit_urn,
            "depth": 3,
            "parent_urn": f"{lvl_urn}:{li}.1",
            "ref_id": f"{li}.1({letter})",
            "implementation_groups": igs,
        }
        if li > 1:
            node["typical_evidence"] = evidence[letter]
        if len(parts) == 1:
            nodes.append({**node, "assessable": True, "description": clean(parts)})
            continue
        # 3.1(g) states the no-third-country-control condition itself, not just an intro
        crit = {
            **node,
            "assessable": node["ref_id"] == "3.1(g)",
            "description": clean([parts[0]]),
        }
        if "Article 19" in crit["description"]:
            crit["annotation"] = (
                "Editorial note: the proposal text refers to Article 19, which covers the "
                "UAL-1 conformity self-assessment. The implementing acts identifying "
                "associated third countries for UAL-3 are set out in Article 18."
            )
        nodes.append(crit)
        for roman, text in zip(parts[1::2], parts[2::2]):
            nodes.append(
                {
                    "urn": f"{crit_urn}:{roman}",
                    "assessable": True,
                    "depth": 4,
                    "parent_urn": crit_urn,
                    "ref_id": f"{li}.1({letter})({roman})",
                    "description": clean([text]),
                    "implementation_groups": igs,
                    **({"typical_evidence": evidence[letter]} if li > 1 else {}),
                }
            )
    nodes.append(
        {
            "urn": f"{lvl_urn}:{li}.2",
            "assessable": False,
            "depth": 2,
            "parent_urn": lvl_urn,
            "ref_id": f"{li}.2",
            "description": clean([re.sub(rf"^{li}\.2\. ", "", scope2[0])] + scope2[1:]),
            "implementation_groups": igs,
        }
    )

DESC = (
    "Proposal for a Regulation establishing a framework of measures for strengthening Europe's cloud "
    "and AI ecosystem (Cloud and AI Development Act), COM(2026) 502 final, 3 June 2026 - Annex II "
    "(criteria for Union assurance levels) with Annex III (audit evidence) as typical evidence. "
    "This is a legislative proposal: the criteria may change before adoption."
)
lib = {
    "urn": "urn:intuitem:risk:library:eu-cada-proposal",
    "locale": "en",
    "ref_id": "EU-CADA-proposal",
    "name": "Cloud and AI Development Act (proposal) - Union assurance levels",
    "description": DESC,
    "copyright": "© European Union, 2026. Reuse is authorised provided the source is acknowledged "
    "(Commission Decision 2011/833/EU).",
    "version": 1,
    "publication_date": "2026-06-03",
    "provider": "EUROPEAN COMMISSION",
    "packager": "intuitem",
    "objects": {
        "framework": {
            "urn": "urn:intuitem:risk:framework:eu-cada-proposal",
            "ref_id": "EU-CADA-proposal",
            "name": "Cloud and AI Development Act (proposal) - Union assurance levels",
            "description": DESC,
            "implementation_groups_definition": [
                {
                    "ref_id": f"UAL-{i}",
                    "name": LEVELS[i],
                    "description": f"Criteria a cloud computing service must meet to be recognised at {LEVELS[i]}, "
                    "including the criteria of the lower levels (Article 20(1)).",
                }
                for i in LEVELS
            ],
            "requirement_nodes": nodes,
        }
    },
}
with open(out, "w", encoding="utf-8") as f:
    yaml.dump(
        lib, f, Dumper=NoAliasDumper, sort_keys=False, allow_unicode=True, width=100
    )
print(len(nodes), "nodes,", sum(n["assessable"] for n in nodes), "assessable")
