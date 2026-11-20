#!/usr/bin/env python3
"""Build the Cloud Sovereignty Framework (June 2026) library from the Commission's calculator.

Source: "Annex - Sovereignty assessment calculator.xlsx" (1 June 2026), published with the
Implementation guidance under "Cloud Sovereignty Framework" on
https://commission.europa.eu/funding-and-tenders/find-calls-tender/tender-opportunities-department/tender-opportunities-digital-services_en

Each answer scores its official points rescaled to 0-100 per question; objective weights are
the official weights (%), so the audit's weighted average approximates the official sovereignty
score / 10 (answer and requirement scores are rounded to integers). Answer labels carry their SEAL level, or "no SEAL impact" when every answer of the
question grants SEAL-4 (guidance rule). Calculator anomalies are kept and noted per objective.

Usage:
    python tools/build_cloud_sovereignty_framework_2026.py <calculator.xlsx> backend/library/libraries/cloud-sovereignty-framework-2026.yaml
"""

import re
import sys

import openpyxl
import yaml


class NoAliasDumper(yaml.SafeDumper):
    # shared lists (e.g. group lists) must be written out in full, not as &id/*id aliases
    def ignore_aliases(self, data):
        return True


src, out = sys.argv[1], sys.argv[2]
ws = openpyxl.load_workbook(src, data_only=False).active

LIB = "cloud-sovereignty-framework-2026"
NODE = f"urn:intuitem:risk:req_node:{LIB}"
sovs, sov, q = [], None, None
for row in ws.iter_rows(min_row=4, values_only=True):
    a, b, c, d, _e, f = (row + (None,) * 6)[:6]
    if isinstance(a, str) and a.startswith("SOV-"):
        ref, name = a.split(" ", 1)
        sov = {
            "ref_id": ref,
            "name": name.strip(),
            "description": b.strip(),
            "weight": round(d * 100),
            "questions": [],
        }
        sovs.append(sov)
        continue
    if a is not None and b:
        q = {"text": re.sub(r"\s+", " ", b).strip(), "choices": []}
        sov["questions"].append(q)
    label = str(c).strip() if c is not None else ""
    # calculator has unlabeled filler rows between scale points; they are not answers
    if not label or label == "0" or d is None:
        continue
    q["choices"].append(
        {"label": re.sub(r"\s+", " ", label), "points": float(d), "seal": int(f)}
    )

# anomalies in the official calculator, reproduced as published so scores match it
SOURCE_NOTES = {
    "SOV-4": "Source note: in the official calculator, the answers to question 6 (subcontractor and suppliers "
    "jurisdiction) repeat the cut-off resilience scale of SOV-1 question 8. They are reproduced as published.",
    "SOV-5": "Source note: in the official calculator, the upper answers to question 2 (manufacturing location) "
    "describe EU development teams rather than manufacturing locations. They are reproduced as published.",
    "SOV-8": "Source note: in the official calculator, questions 2, 3 and 4 each list one answer twice with "
    'different scores ("Circular economy EU-aligned", "Detailed EU methodology", "Only EU energy '
    'supplies"). They are reproduced as published; answers are ordered from lowest to highest score.',
}
nodes = []
for s in sovs:
    urn = f"{NODE}:{s['ref_id'].lower()}"
    questions = {}
    for qi, qq in enumerate(s["questions"], start=1):
        top = max(ch["points"] for ch in qq["choices"])
        # guidance: when every answer grants SEAL-4, the question has no impact on the SEAL
        no_impact = all(ch["seal"] == 4 for ch in qq["choices"])
        qurn = f"{urn}:question:{qi}"
        questions[qurn] = {
            "type": "unique_choice",
            "text": f"{qi}. {qq['text']}",
            "choices": [
                {
                    "urn": f"{qurn}:choice:{ci}",
                    "value": f"{ch['label']} ({'no SEAL impact' if no_impact else 'SEAL-' + str(ch['seal'])})",
                    "add_score": round(ch["points"] * 100 / top),
                }
                for ci, ch in enumerate(qq["choices"], start=1)
            ],
        }
    nodes.append(
        {
            "urn": urn,
            "assessable": True,
            "depth": 1,
            "ref_id": s["ref_id"],
            "name": s["name"],
            "description": s["description"],
            "weight": s["weight"],
            **(
                {"annotation": SOURCE_NOTES[s["ref_id"]]}
                if s["ref_id"] in SOURCE_NOTES
                else {}
            ),
            "questions": questions,
        }
    )

assert len(sovs) == 8 and sum(s["weight"] for s in sovs) == 100
assert sum(len(s["questions"]) for s in sovs) == 48
assert all(len(q["choices"]) >= 2 for s in sovs for q in s["questions"])

SEAL = [
    (
        "SEAL-0",
        "No Sovereignty",
        "Service, technology or operations under exclusive control of non-EU third parties, governed entirely by non-EU jurisdictions.",
    ),
    (
        "SEAL-1",
        "Jurisdictional Sovereignty",
        "EU law formally applies with limited practical enforceability; service, technology or operations under exclusive control of non-EU third parties.",
    ),
    (
        "SEAL-2",
        "Data Sovereignty",
        "EU jurisdictions apply, with material dependencies remain; service, technology or operations under indirect control of non-EU third parties.",
    ),
    (
        "SEAL-3",
        "Technological Sovereignty",
        "EU jurisdictions apply, EU actors exercising meaningful but not full influence; service, technology or operations under marginal control of non-EU third parties.",
    ),
    (
        "SEAL-4",
        "Full Digital Sovereignty",
        "Technology and operations under complete EU control, subject only to EU jurisdiction, with no critical non-EU dependencies.",
    ),
]
DESC = (
    "Cloud Sovereignty Framework - Implementation guidance and Annex - Sovereignty assessment calculator, "
    "European Commission, 1 June 2026. 48 specific objectives across 8 sovereignty objectives. "
    "Each answer scores its official points rescaled to 0-100, and the audit's weighted average approximates "
    "the official sovereignty score divided by 10 (scores are rounded to integers). Each answer also shows its SEAL level; the overall SEAL is the "
    "lowest SEAL among the answers (not computed by the app). Questions whose answers all grant SEAL-4 have no "
    "impact on the SEAL and are marked as such.\n\n"
    + "\n".join(f"{r} - {n}: {d}" for r, n, d in SEAL)
)
lib = {
    "urn": f"urn:intuitem:risk:library:{LIB}",
    "locale": "en",
    "ref_id": LIB,
    "name": "Cloud Sovereignty Framework (June 2026)",
    "description": DESC,
    "copyright": "© European Union, 2026. Reuse is authorised provided the source is acknowledged "
    "(Commission Decision 2011/833/EU).",
    "version": 1,
    "publication_date": "2026-06-01",
    "provider": "EUROPEAN COMMISSION",
    "packager": "intuitem",
    "objects": {
        "framework": {
            "urn": f"urn:intuitem:risk:framework:{LIB}",
            "ref_id": LIB,
            "name": "Cloud Sovereignty Framework (June 2026)",
            "description": DESC,
            "min_score": 0,
            "max_score": 100,
            "requirement_nodes": nodes,
        }
    },
}
with open(out, "w", encoding="utf-8") as fh:
    yaml.dump(
        lib, fh, Dumper=NoAliasDumper, sort_keys=False, allow_unicode=True, width=100
    )
print(len(nodes), "objectives,", sum(len(n["questions"]) for n in nodes), "questions")
