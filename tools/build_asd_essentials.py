#!/usr/bin/env python3
"""Build the ASD Essentials for enterprise IT library from ASD's OSCAL release.

Source: github.com/AustralianCyberSecurityCentre/e4eit-oscal (ASD's mirror of
cyber.gov.au/e4eit/oscal) at a pinned commit: the catalog (functions >
principles > actions with their Indicators of Good Practice), one profile per
domain (the actions that apply there and its priority phase) and the mapping
collection.

Structure: ASD rates every action separately in each domain it applies to, so
the tree is domain (depth 1) > principle (depth 2, ref_id GOV-01) > action
(depth 3, assessable, ref_id IT.GOV-01.1), an action repeated under each of its
domains, as in ASD's per-domain resolved catalogs. The IGPs (not effective /
partially effective / fully effective) are the action's annotation: ASD uses
them to guide the assessor, who rates the action.

Implementation groups are the priority phases: a technical domain is in its own
phase only, so assessing several phases means selecting several groups. The two
capability domains apply across all phases (ASD reports them as "All"), so they
are in every group.

Also writes the transition mapping from essential-eight-2023, whose ref_ids are
ISM controls: ASD maps each action to the Essential Eight ISM controls. And the
mapping with nist-csf-2.0 (both directions), from the same collection.

Usage:
    python tools/build_asd_essentials.py [--source DIR] [--output-dir DIR]

Without --source, the pinned commit is downloaded from GitHub.
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

REPO = "AustralianCyberSecurityCentre/e4eit-oscal"
COMMIT = "1cd32b96310e2dd166b5d51ce64f414a4613025d"
CATALOG_SHA256 = "29b602fbbce89d83f9dffd6e6f99d32d1929b563a967f62b2c1cb52891fdb7d2"
VERSION = "v2026.10.15"

SLUG = "asd-essentials-enterprise-it"
NAME = "ASD Essentials for enterprise IT"
E8 = "essential-eight-2023"
E8_TITLE = "ASD’s Essential Eight"
CSF = "nist-csf-2.0"
CSF_TITLE = "NIST Cybersecurity Framework 2.0"

# ASD's summary table order: capability domains, then by priority phase.
DOMAINS = [
    "governance-and-culture",
    "visibility-and-response",
    "boundary-services",
    "identity-services",
    "critical-processes-and-services",
    "privileged-environments",
    "business-systems",
    "user-devices",
]
CAPABILITY = {"governance-and-culture", "visibility-and-response"}
TIERS = ["Not effective", "Partially effective", "Fully effective"]

OUTCOME = {
    "ref_id": "effectiveness",
    "kind": "weakest_link",
    "label": "Effectiveness",
    "rated_depth": 2,
    "per": "depth_1",
    "result_labels": {
        "compliant": "Fully effective",
        "partially_compliant": "Partially effective",
        "non_compliant": "Not effective",
    },
    "section_label": "domains",
    "annotation": (
        "A principle is rated in each domain by its lowest applicable action, and is not "
        "assessed while one of them is. Each domain scores its applicable principles: fully "
        "effective 1, partially effective 0.5, not effective and not assessed 0, averaged "
        "as a percentage. A domain with nothing assessed has no score."
    ),
}

PHASES = [
    (
        "1",
        "Priority phase 1",
        "Boundary services and identity services, with the capability domains.",
    ),
    (
        "2",
        "Priority phase 2",
        "Critical processes and services and privileged environments, with the capability "
        "domains.",
    ),
    (
        "3",
        "Priority phase 3",
        "Business systems and user devices, with the capability domains.",
    ),
]

DESCRIPTION = f"""The ASD Essentials for enterprise IT helps organisations protect enterprise IT environments from sophisticated cyber threats. It replaces the Essential Eight. Principles describe the security outcomes, actions what to do to achieve them, and domains where the actions apply: six technical domains, sequenced by priority phase, and two capability domains that apply across all phases.

Each action is rated separately in each domain it applies to, so it appears under each of its domains. Rate it from its Indicators of Good Practice: fully effective = compliant, partially effective = partially compliant, not effective = non compliant.

Select the priority phases to assess when creating an audit, for example 1 and 2 for the first two phases: each phase covers its own domains and the capability domains.

Assessment (ASD Essentials assessment process guide): a principle is rated, in each domain, by its lowest applicable action rating, and not assessed while any applicable action is not assessed. Each domain reports its principles at each rating and a percentage: not effective 0, partially effective 0.5, fully effective 1, summed and divided by the number of applicable principles.
https://www.cyber.gov.au/essentials/essentials-for-enterprise-it"""

COPYRIGHT = (
    "© Commonwealth of Australia 2026. Material from cyber.gov.au is provided under a "
    "Creative Commons Attribution 4.0 International licence and is attributed to the "
    "Australian Signals Directorate."
)


def fetch(source: Path | None, name: str) -> bytes:
    if source:
        return (source / name).read_bytes()
    url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{name}"
    with urllib.request.urlopen(url, timeout=60) as response:  # nosec B310
        return response.read()


def rationale(mappings: dict, entry: dict) -> str | None:
    """A map's own matching-rationale wins over the collection's (OSCAL); None if neither sets it."""
    return entry.get("matching-rationale") or mappings.get("provenance", {}).get(
        "matching-rationale"
    )


def props(obj: dict) -> dict:
    return {p["name"]: p.get("value") for p in obj.get("props", [])}


def load(source: Path | None):
    raw = fetch(source, "E4EIT_catalog.json")
    if hashlib.sha256(raw).hexdigest() != CATALOG_SHA256:
        print("warning: catalog differs from the pinned release", file=sys.stderr)
    catalog = json.loads(raw)["catalog"]
    profiles = {}
    for domain in DOMAINS:
        profile = json.loads(fetch(source, f"E4EIT_{domain}-domain_profile.json"))[
            "profile"
        ]
        meta = props(profile["metadata"])
        ids = [
            i
            for imp in profile["imports"]
            for inc in imp.get("include-controls", [])
            for i in inc.get("with-ids", [])
        ]
        profiles[domain] = {
            "phase": meta["domain-priority-phase"].removeprefix("phase-"),
            "description": meta["domain-description"],
            "actions": ids,
        }
    mappings = json.loads(fetch(source, "E4EIT_mapping-collection.json"))[
        "mapping-collection"
    ]
    return catalog, profiles, mappings


def igps(action: dict) -> str:
    blocks = []
    for part in action["parts"]:
        if part.get("class") != "indicators-of-good-practice":
            continue
        by_tier = {group["title"]: group.get("parts", []) for group in part["parts"]}
        assert set(by_tier) <= set(TIERS), by_tier.keys()
        for tier in TIERS:
            if by_tier.get(tier):
                items = [f"- {i['id']}: {i['prose']}" for i in by_tier[tier]]
                blocks.append("\n".join([f"{tier}:", *items]))
    return "\n\n".join(blocks)


def principles(catalog: dict) -> dict:
    """Action id -> (principle, action), in catalog order."""
    found = {}
    for function in catalog["groups"]:
        for principle in function["groups"]:
            overview = next(p["prose"] for p in principle["parts"])
            ref_id, _, name = principle["title"].partition(" - ")
            assert ref_id == principle["id"], principle["title"]
            for action in principle.get("controls", []):
                statement = next(
                    p for p in action["parts"] if p.get("class") == "essentials-action"
                )
                domains = [
                    p["value"] for p in action.get("props", []) if p["name"] == "domain"
                ]
                found[action["id"]] = {
                    "principle": {
                        "ref_id": ref_id,
                        "name": name,
                        "description": overview,
                    },
                    "statement": statement["prose"],
                    "igps": igps(action),
                    "domains": domains,
                }
    return found


def title_of(domain: str) -> str:
    return domain.replace("-", " ").capitalize()


def groups_for(domain: str, phase: str) -> list[str]:
    return ["1", "2", "3"] if domain in CAPABILITY else [phase]


def build_framework(catalog, profiles):
    actions = principles(catalog)
    order = list(actions)
    nodes, instances = [], defaultdict(list)
    base = f"urn:intuitem:risk:req_node:{SLUG}"
    for domain in DOMAINS:
        profile = profiles[domain]
        applicable = set(profile["actions"])
        tagged = {a for a, x in actions.items() if domain in x["domains"]}
        assert applicable == tagged, (domain, applicable ^ tagged)
        groups = groups_for(domain, profile["phase"])
        domain_urn = f"{base}:{domain}"
        nodes.append(
            {
                "urn": domain_urn,
                "assessable": False,
                "depth": 1,
                "name": title_of(domain),
                "description": profile["description"],
                "implementation_groups": groups,
            }
        )
        seen = set()
        for action_id in (a for a in order if a in applicable):
            action = actions[action_id]
            principle = action["principle"]
            principle_urn = f"{domain_urn}:{principle['ref_id'].lower()}"
            if principle_urn not in seen:
                seen.add(principle_urn)
                nodes.append(
                    {
                        "urn": principle_urn,
                        "assessable": False,
                        "depth": 2,
                        "parent_urn": domain_urn,
                        "ref_id": principle["ref_id"],
                        "name": principle["name"],
                        "description": principle["description"],
                        "implementation_groups": groups,
                    }
                )
            urn = f"{principle_urn}:{action_id.lower()}"
            instances[action_id].append(urn)
            nodes.append(
                {
                    "urn": urn,
                    "assessable": True,
                    "depth": 3,
                    "parent_urn": principle_urn,
                    "ref_id": action_id,
                    "description": action["statement"],
                    "annotation": action["igps"],
                    "implementation_groups": groups,
                }
            )
    framework = {
        "urn": f"urn:intuitem:risk:framework:{SLUG}",
        "ref_id": NAME,
        "name": NAME,
        "description": DESCRIPTION,
        "implementation_groups_definition": [
            {"ref_id": ref_id, "name": name, "description": description}
            for ref_id, name, description in PHASES
        ],
        "outcomes_definition": [OUTCOME],
        "requirement_nodes": nodes,
    }
    return framework, instances


def library(
    urn_slug, name, description, objects, dependencies=None, copyright=None, version=1
):
    lib = {
        "urn": f"urn:intuitem:risk:library:{urn_slug}",
        "locale": "en",
        "ref_id": urn_slug if dependencies else NAME,
        "name": name,
        "description": description,
        "copyright": copyright or COPYRIGHT,
        "version": version,
        "publication_date": date.today().isoformat(),
        "provider": "Australian Signals Directorate (ASD)",
        "packager": "intuitem",
    }
    if dependencies:
        lib["dependencies"] = dependencies
    lib["objects"] = objects
    return lib


def build_e8_mapping(mappings, instances, e8_path: Path):
    e8 = yaml.safe_load(e8_path.read_text(encoding="utf-8"))
    by_ism = defaultdict(list)
    for node in e8["objects"]["framework"]["requirement_nodes"]:
        if node["assessable"]:
            by_ism[node["ref_id"].lower()].append(node["urn"])
    titles = {r["uuid"]: r["title"] for r in mappings["back-matter"]["resources"]}
    (e8_map,) = [
        m
        for m in mappings["mappings"]
        if titles[m["target-resource"]["href"].lstrip("#")].startswith(E8_TITLE)
    ]
    pairs, missing = [], set()
    for entry in e8_map["maps"]:
        assert entry["relationship"] == "intersects-with", entry["relationship"]
        assert len(entry["sources"]) == 1, entry["sources"]
        action = entry["sources"][0]["id-ref"]
        for target in entry["targets"]:
            ism = target["id-ref"]
            if ism not in by_ism:
                missing.add(ism)
            for source in by_ism.get(ism, []):
                for urn in instances[action]:
                    pairs.append((source, urn, rationale(mappings, entry)))
    if missing:
        print(f"E8 ISM ids not in {E8}: {sorted(missing)}", file=sys.stderr)
    seen = set()
    rows = []
    for source, target, matching in pairs:
        if (source, target) not in seen:
            seen.add((source, target))
            rows.append(
                {
                    "source_requirement_urn": source,
                    "target_requirement_urn": target,
                    "relationship": "intersect",
                    "rationale": matching,
                    "strength_of_relationship": None,
                }
            )
    slug = f"mapping-{E8}-and-{SLUG}"
    description = (
        f"Transition mapping from the Essential Eight Maturity Model (November 2023) to the "
        f"{NAME}, from ASD's OSCAL mapping collection ({VERSION}): each action intersects the "
        "Essential Eight ISM controls ASD maps it to, in every domain it applies to."
    )
    name = f"Essential Eight Maturity Model (November 2023) -> {NAME}"
    return library(
        slug,
        name,
        description,
        {
            "requirement_mapping_set": {
                "urn": f"urn:intuitem:risk:req_mapping_set:{slug}",
                "ref_id": slug,
                "name": name,
                "description": description,
                "source_framework_urn": f"urn:intuitem:risk:framework:{E8}",
                "target_framework_urn": f"urn:intuitem:risk:framework:{SLUG}",
                "requirement_mappings": rows,
            }
        },
        dependencies=[
            f"urn:intuitem:risk:library:{E8}",
            f"urn:intuitem:risk:library:{SLUG}",
        ],
        version=2,  # v2: rationale read from ASD's provenance (functional, was semantic)
    ), len(missing)


def build_csf_mapping(mappings, instances, csf_path: Path):
    csf = yaml.safe_load(csf_path.read_text(encoding="utf-8"))
    known = {n["urn"] for n in csf["objects"]["framework"]["requirement_nodes"]}
    titles = {r["uuid"]: r["title"] for r in mappings["back-matter"]["resources"]}
    (csf_map,) = [
        m
        for m in mappings["mappings"]
        if titles[m["target-resource"]["href"].lstrip("#")].startswith(CSF_TITLE)
    ]
    rows = []
    for entry in csf_map["maps"]:
        assert entry["relationship"] == "intersects-with", entry["relationship"]
        assert len(entry["sources"]) == 1, entry["sources"]
        action = entry["sources"][0]["id-ref"]
        for target in entry["targets"]:
            urn = f"urn:intuitem:risk:req_node:{CSF}:{target['id-ref'].lower()}"
            assert urn in known, f"CSF id not in {CSF}: {target['id-ref']}"
            for source in instances[action]:
                rows.append(
                    {
                        "source_requirement_urn": source,
                        "target_requirement_urn": urn,
                        "relationship": "intersect",
                        "rationale": rationale(mappings, entry),
                        "strength_of_relationship": None,
                    }
                )
    slug = f"mapping-{SLUG}-and-{CSF}"
    description = (
        f"Mapping between the {NAME} and the NIST Cybersecurity Framework 2.0, from ASD's OSCAL "
        f"mapping collection ({VERSION}): each action intersects the CSF subcategories ASD maps "
        "it to, in every domain it applies to."
    )
    name = f"{NAME} <-> NIST CSF 2.0"

    def mapping_set(ref_id, source, target, mapping_rows):
        return {
            "urn": f"urn:intuitem:risk:req_mapping_set:{ref_id}",
            "ref_id": ref_id,
            "name": name,
            "description": description,
            "source_framework_urn": f"urn:intuitem:risk:framework:{source}",
            "target_framework_urn": f"urn:intuitem:risk:framework:{target}",
            "requirement_mappings": mapping_rows,
        }

    # intersect is symmetric; the reverse set lets CSF (and ISO 27001 through it) reach the Essentials
    reverse = [
        {
            **r,
            "source_requirement_urn": r["target_requirement_urn"],
            "target_requirement_urn": r["source_requirement_urn"],
        }
        for r in rows
    ]
    return library(
        slug,
        name,
        description,
        {
            "requirement_mapping_sets": [
                mapping_set(slug, SLUG, CSF, rows),
                mapping_set(f"{slug}-revert", CSF, SLUG, reverse),
            ]
        },
        dependencies=[
            f"urn:intuitem:risk:library:{SLUG}",
            f"urn:intuitem:risk:library:{CSF}",
        ],
    )


def _str_representer(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


class NoAliasDumper(yaml.Dumper):
    def ignore_aliases(self, data):
        return True


def write(path: Path, data: dict):
    yaml.add_representer(str, _str_representer)
    path.write_text(
        yaml.dump(
            data, Dumper=NoAliasDumper, sort_keys=False, allow_unicode=True, width=100
        ),
        encoding="utf-8",
    )
    print(f"wrote {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Build the ASD Essentials for enterprise IT library."
    )
    parser.add_argument(
        "--source", type=Path, help="directory with the OSCAL JSON files"
    )
    root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--output-dir", type=Path, default=root / "backend/library/libraries"
    )
    args = parser.parse_args()

    catalog, profiles, mappings = load(args.source)
    framework, instances = build_framework(catalog, profiles)
    assessable = sum(n["assessable"] for n in framework["requirement_nodes"])
    assert len(instances) == 58 and assessable == 212, (len(instances), assessable)
    write(
        args.output_dir / f"{SLUG}.yaml",
        library(SLUG, NAME, DESCRIPTION, {"framework": framework}),
    )
    mapping, _ = build_e8_mapping(
        mappings, instances, root / f"backend/library/libraries/{E8}.yaml"
    )
    write(args.output_dir / f"mapping-{E8}-and-{SLUG}.yaml", mapping)
    write(
        args.output_dir / f"mapping-{SLUG}-and-{CSF}.yaml",
        build_csf_mapping(
            mappings, instances, root / f"backend/library/libraries/{CSF}.yaml"
        ),
    )


if __name__ == "__main__":
    main()
