#!/usr/bin/env python3
import csv
import json
import unicodedata
from pathlib import Path

IN_PATH = Path("risk_bundle_fixed.json")
ASSETS_CSV = Path("bundle_assets.csv")
THREATS_CSV = Path("bundle_threats.csv")
CONTROLS_CSV = Path("bundle_controls.csv")


def sec_obj_text(d: dict) -> str:
    out = []
    for k in ["confidentiality", "integrity", "availability", "proof", "authenticity", "privacy", "safety"]:
        v = d.get(k, 0)
        if isinstance(v, int) and v > 0:
            out.append(f"{k}: {min(v,4)}")
    return ", ".join(out)


def dr_text(d: dict) -> str:
    out = []
    for k in ["rto", "rpo", "mtd"]:
        v = str(d.get(k, "")).strip().lower().replace(" ", "")
        if not v:
            continue
        v = v.replace("min", "m")
        out.append(f"{k}: {v}")
    return ", ".join(out)


def normalize_label(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    out = []
    previous_sep = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            previous_sep = False
        else:
            if not previous_sep:
                out.append("_")
                previous_sep = True
    return "".join(out).strip("_")


def status_map(v: str) -> str:
    x = (v or "").strip().lower()
    return {
        "en place": "active",
        "partiel": "in_progress",
        "planifié": "to_do",
        "planifie": "to_do",
    }.get(x, "to_do")


def category_map(v: str) -> str:
    x = (v or "").strip().lower()
    return {
        "technique": "technical",
        "organisationnel": "process",
        "organisationnelle": "process",
        "procédure": "procedure",
        "procedure": "procedure",
        "physique": "physical",
    }.get(x, "technical")


def main() -> None:
    bundle = json.loads(IN_PATH.read_text(encoding="utf-8"))

    with ASSETS_CSV.open("w", newline="", encoding="utf-8") as f:
        cols = [
            "ref_id", "name", "description", "type", "domain", "localisation",
            "observation", "reference_link", "security_objectives",
            "disaster_recovery_objectives", "parent_assets", "labels",
        ]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for a in bundle.get("assets", []):
            deps = []
            for d in (a.get("dependencies_upstream") or []) + (a.get("dependencies_downstream") or []):
                if d and d not in deps:
                    deps.append(d)
            labels = []
            for x in (a.get("labels") or []):
                s = normalize_label(x)
                if s and s not in labels:
                    labels.append(s)
            for extra in [a.get("class", ""), a.get("asset_subtype", "")]:
                s = normalize_label(extra)
                if s and s not in labels:
                    labels.append(s)
            w.writerow({
                "ref_id": str(a.get("ref_id", ""))[:100],
                "name": a.get("name", ""),
                "description": a.get("description", ""),
                "type": a.get("type", "SP"),
                "domain": a.get("domain", "Global") or "Global",
                "localisation": a.get("localisation", ""),
                "observation": a.get("observation", ""),
                "reference_link": a.get("reference_link", ""),
                "security_objectives": sec_obj_text(a.get("security_objectives") or {}),
                "disaster_recovery_objectives": dr_text(a.get("dr_objectives") or {}),
                "parent_assets": "|".join(deps),
                "labels": "|".join(labels),
            })

    with THREATS_CSV.open("w", newline="", encoding="utf-8") as f:
        cols = ["ref_id", "name", "description", "domain"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for t in bundle.get("threats", []):
            w.writerow({
                "ref_id": str(t.get("ref_id", ""))[:100],
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "domain": bundle.get("meta", {}).get("folder", "Global"),
            })

    with CONTROLS_CSV.open("w", newline="", encoding="utf-8") as f:
        cols = ["ref_id", "name", "description", "domain", "status", "category", "control_impact", "filtering_labels"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for c in bundle.get("controls", []):
            labels = "|".join(str(x).strip().replace(" ", "_") for x in (c.get("labels") or []) if str(x).strip())
            w.writerow({
                "ref_id": str(c.get("ref_id", ""))[:100],
                "name": c.get("name", ""),
                "description": c.get("description", ""),
                "domain": bundle.get("meta", {}).get("folder", "Global"),
                "status": status_map(c.get("status", "")),
                "category": category_map(c.get("category", "")),
                "control_impact": int(c.get("effectiveness", 3) or 3),
                "filtering_labels": labels,
            })

    print("Generated:")
    print(ASSETS_CSV)
    print(THREATS_CSV)
    print(CONTROLS_CSV)


if __name__ == "__main__":
    main()
