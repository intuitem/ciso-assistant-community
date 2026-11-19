"""Build mapping-essential-eight-2023-and-scf-2025.2.2.yaml from SCF's Essential 8 STRM.

Input: the CSV export of https://securecontrolsframework.com/content/strm/scf-strm-apac-australia-essential-8.pdf
(SCF 2025.3, focal document = Essential Eight maturity model Nov 2023). Each row carries the ISM id of the
Essential Eight control in its Notes column, which is the ref_id of that control in essential-eight-2023.

Usage: python tools/build_essential_eight_scf_mapping.py <strm.csv>
"""

import csv
import sys
from pathlib import Path

import yaml

LIBS = Path(__file__).resolve().parent.parent / "backend/library/libraries"
E8, SCF = "essential-eight-2023", "scf-2025.2.2"
NAME = f"Essential Eight Maturity Model (November 2023) <-> {SCF}"
DESCRIPTION = (
    "Mapping between the Essential Eight Maturity Model (November 2023) and SCF: Secure Controls Framework "
    "(2025.2.2), from SCF's Set Theory Relationship Mapping (STRM) for Australia Essential 8 (SCF 2025.3). "
    "Each Essential Eight control is matched through the ISM id given by the STRM."
)
# STRM FDE # suffix -> mitigation strategy node of essential-eight-2023
STRATEGIES = {
    "P1": "pa",
    "P2": "pos",
    "P3": "mfa",
    "P4": "rap",
    "P5": "ac",
    "P6": "rmom",
    "P7": "uah",
    "P8": "rb",
}
RELATIONSHIPS = {
    "Equal": "equal",
    "Subset Of": "subset",
    "Superset Of": "superset",
    "Intersects With": "intersect",
}


def node_urns(library: str) -> set[str]:
    content = yaml.safe_load((LIBS / f"{library}.yaml").read_text())
    return {n["urn"] for n in content["objects"]["framework"]["requirement_nodes"]}


def build(csv_path: str) -> list[dict]:
    e8_urns, scf_urns = node_urns(E8), node_urns(SCF)
    mappings: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(open(csv_path, encoding="utf-8")):
        relationship = RELATIONSHIPS.get(row["STRM Relationship"])
        if relationship is None:  # "No Relationship"
            continue
        source = f"urn:intuitem:risk:req_node:{E8}:{STRATEGIES[row['FDE #'][-2:]]}:{row['Notes'].strip().lower()}"
        target = f"urn:intuitem:risk:req_node:{SCF}:{row['SCF #'].strip().lower()}"
        assert source in e8_urns, f"unknown Essential Eight control {source}"
        if target not in scf_urns:  # added after 2025.2.2 (SCF 2025.3 errata)
            print(f"skipped {source} -> {target}: not in {SCF}")
            continue
        mapping = {
            "source_requirement_urn": source,
            "target_requirement_urn": target,
            "relationship": relationship,
            "rationale": row["STRM Rationale"].strip().lower(),
            "strength_of_relationship": int(row["Strength"]),
        }
        # the STRM repeats a control at each maturity level it belongs to; strengths may differ (ISM-1490), keep the highest
        previous = mappings.setdefault((source, target), mapping)
        assert previous["relationship"] == relationship, (
            f"conflicting STRM rows for {source} -> {target}"
        )
        previous["strength_of_relationship"] = max(
            previous["strength_of_relationship"], mapping["strength_of_relationship"]
        )
    return sorted(
        mappings.values(),
        key=lambda m: (m["source_requirement_urn"], m["target_requirement_urn"]),
    )


def mapping_set(ref_id: str, source: str, target: str, mappings: list[dict]) -> dict:
    return {
        "urn": f"urn:intuitem:risk:req_mapping_set:{ref_id}",
        "ref_id": ref_id,
        "name": NAME,
        "description": DESCRIPTION,
        "source_framework_urn": f"urn:intuitem:risk:framework:{source}",
        "target_framework_urn": f"urn:intuitem:risk:framework:{target}",
        "requirement_mappings": mappings,
    }


def reverse(mapping: dict) -> dict:
    flipped = {"subset": "superset", "superset": "subset"}
    return {
        **mapping,
        "source_requirement_urn": mapping["target_requirement_urn"],
        "target_requirement_urn": mapping["source_requirement_urn"],
        "relationship": flipped.get(mapping["relationship"], mapping["relationship"]),
    }


def main():
    mappings = build(sys.argv[1])
    ref_id = f"mapping-{E8}-and-{SCF}"
    library = {
        "urn": f"urn:intuitem:risk:library:{ref_id}",
        "locale": "en",
        "ref_id": ref_id,
        "name": NAME,
        "description": DESCRIPTION,
        "copyright": "SCF - CC BY-ND 4.0",
        "version": 1,
        "publication_date": "2026-11-19",
        "provider": "SCF",
        "packager": "intuitem",
        "dependencies": [
            f"urn:intuitem:risk:library:{E8}",
            f"urn:intuitem:risk:library:{SCF}",
        ],
        # both directions, like the other SCF mappings, so SCF pivots to and from Essential Eight
        "objects": {
            "requirement_mapping_sets": [
                mapping_set(ref_id, E8, SCF, mappings),
                mapping_set(
                    f"{ref_id}-revert", SCF, E8, [reverse(m) for m in mappings]
                ),
            ]
        },
    }
    out = LIBS / f"{ref_id}.yaml"
    out.write_text(
        yaml.safe_dump(library, sort_keys=False, allow_unicode=True, width=110)
    )
    print(
        f"{out.name}: {len(mappings)} mappings, {len({m['source_requirement_urn'] for m in mappings})} sources"
    )


if __name__ == "__main__":
    main()
