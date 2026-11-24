#!/usr/bin/env python3
"""Build the NIST SP 800-171 Rev. 2 <-> Rev. 3 mapping library.

Source: NIST's change analysis (Rev. 2 to Rev. 3), "Change Analysis 800-171 R2-R3"
sheet: https://csrc.nist.gov/files/pubs/sp/800/171/r3/final/docs/sp800-171r2-to-r3-analysis.xlsx

Rules (source = Rev. 2):
- no significant change -> equal
- significant / minor change -> subset (Rev. 3 adds detail)
- withdrawn, incorporated into / addressed by one requirement -> subset; several -> intersect each
- withdrawn with no destination (NCO, technology-specific, ...) -> not mapped
The reverse set flips subset/superset, so a subset is only kept where Rev. 3 keeps
every element of the Rev. 2 text; OVERRIDES below record where it does not, after a
text review of every pair.

Usage (from the repo root):
    .venv/bin/python tools/build_nist_800_171_r2_r3_mapping.py sp800-171r2-to-r3-analysis.xlsx
"""

import datetime
import re
import sys
from collections import Counter
from pathlib import Path

import openpyxl
import yaml

LIB = Path(__file__).resolve().parents[1] / "backend" / "library" / "libraries"
RID = "mapping-nist-800-171-rev2-and-nist-800-171-rev3"
U2 = "urn:intuitem:risk:req_node:nist-800-171-rev2:"
U3 = "urn:intuitem:risk:req_node:nist-800-171-rev3:"
FLIP = {"subset": "superset", "superset": "subset"}

# NIST typo: no 3.11.4 in Rev. 2; the row is the withdrawn 03.12.04 slot, its real source 3.12.4 has its own row
SKIP_ROWS = {"3.11.4"}

# (rev2, rev3) -> (relationship, reason); relationship None drops a NIST pairing
OVERRIDES = {
    ("3.1.1", "03.01.01"): (
        "intersect",
        "Rev. 3 covers accounts; access by devices is not restated",
    ),
    ("3.1.9", "03.01.09"): ("subset", "Rev. 3 requires display before granting access"),
    ("3.1.10", "03.01.10"): (
        "intersect",
        "Rev. 3 allows a user-initiated lock instead of an inactivity lock",
    ),
    ("3.1.12", "03.01.12"): (
        "intersect",
        "Rev. 3 drops monitoring of remote access sessions",
    ),
    ("3.1.13", "03.01.12"): (
        "intersect",
        "03.01.12 does not require encrypting remote sessions",
    ),
    ("3.1.21", "03.01.20"): (
        "intersect",
        "Rev. 3 covers organization-controlled portable storage only",
    ),
    ("3.3.1", "03.03.01"): (
        "intersect",
        "03.03.01 selects event types; creation and retention are in 03.03.03",
    ),
    ("3.3.3", "03.03.03"): (None, "review and update of logged events is 03.03.01 b"),
    ("3.3.7", "03.03.07"): (
        "intersect",
        "Rev. 3 drops clock synchronization with an authoritative source",
    ),
    ("3.4.1", "03.04.01"): ("intersect", "inventories moved to 03.04.10"),
    ("3.5.1", "03.05.01"): (
        "intersect",
        "Rev. 3 splits users (03.05.01) from devices (03.05.02)",
    ),
    ("3.5.2", "03.05.02"): (
        "intersect",
        "Rev. 3 splits users (03.05.01) from devices (03.05.02)",
    ),
    ("3.5.4", "03.05.04"): (
        "subset",
        "Rev. 3 drops the network-access limitation (local access included)",
    ),
    ("3.5.7", "03.05.07"): (
        "intersect",
        "Rev. 3 replaces the change of characters with organization-defined rules",
    ),
    ("3.6.1", "03.06.01"): ("intersect", "Rev. 3 drops user response activities"),
    ("3.7.3", "03.08.03"): (
        "intersect",
        "03.08.03 does not cover maintenance under organizational control",
    ),
    ("3.8.3", "03.08.03"): (
        "subset",
        "Rev. 3 adds release out of organizational control",
    ),
    ("3.8.4", "03.08.04"): ("subset", "Rev. 3 adds handling caveats"),
    ("3.10.1", "03.10.01"): (
        "intersect",
        "03.10.01 manages the access list; enforcement is in 03.10.07",
    ),
    ("3.10.2", "03.10.02"): (
        "intersect",
        "Rev. 3 drops protection of the support infrastructure",
    ),
    ("3.11.1", "03.11.01"): (
        "intersect",
        "Rev. 3 narrows the risk to unauthorized disclosure of CUI",
    ),
    ("3.13.8", "03.13.08"): (
        "subset",
        "Rev. 3 adds protection while in storage and drops the alternative physical safeguards exception",
    ),
    ("3.13.11", "03.13.11"): (
        "intersect",
        "Rev. 3 no longer requires FIPS-validated cryptography",
    ),
    ("3.13.12", "03.13.12"): (
        "intersect",
        "Rev. 3 allows organization-defined exceptions to the remote activation ban",
    ),
    ("3.14.3", "03.14.03"): (
        "intersect",
        "Rev. 3 drops taking action in response to alerts",
    ),
}

# links NIST does not list, found in the text review
ADDITIONS = [
    (
        "3.1.13",
        "03.13.08",
        "intersect",
        "remote session confidentiality, for CUI in transmission",
    ),
    ("3.3.1", "03.03.03", "intersect", "generation and retention of audit records"),
    ("3.3.3", "03.03.01", "subset", "03.03.01 b: review and update of the event types"),
    ("3.4.1", "03.04.10", "intersect", "system component inventory"),
    ("3.5.1", "03.05.02", "intersect", "device identification"),
    ("3.5.2", "03.05.01", "intersect", "user authentication"),
    (
        "3.5.6",
        "03.01.01",
        "intersect",
        "03.01.01 f.2: disable accounts inactive for a defined period (device identifiers not covered)",
    ),
    (
        "3.10.1",
        "03.10.07",
        "intersect",
        "enforcement of physical access authorizations",
    ),
    ("3.13.2", "03.16.01", "intersect", "systems security engineering principles"),
]


def requirements(name):
    content = yaml.safe_load((LIB / name).read_text())
    return {
        n["ref_id"]
        for n in content["objects"]["framework"]["requirement_nodes"]
        if n.get("assessable")
    }


def mapping(src, tgt, rel, annotation):
    return {
        "source_requirement_urn": U2 + src,
        "target_requirement_urn": U3 + tgt,
        "relationship": rel,
        "rationale": "semantic",
        "annotation": annotation,
    }


def nist_rows(path):
    ws = openpyxl.load_workbook(path, read_only=True)["Change Analysis 800-171 R2-R3"]
    for r in list(ws.iter_rows(values_only=True))[1:]:
        src = str(r[2] or "").strip()
        if not src or src in SKIP_ROWS:
            continue  # empty: new in Rev. 3
        if r[14]:  # withdrawn
            note = (
                re.sub(r"\s+", " ", str(r[8])).strip().replace("03.02 01", "03.02.01")
            )
            targets = re.findall(r"03\.\d{2}\.\d{2}", note)
            rel = "subset" if len(targets) == 1 else "intersect"
            yield src, targets, rel, f"Withdrawn in Rev. 3: {note}"
            continue
        if r[9]:
            rel, kind = "equal", "no significant change"
        elif r[10] or r[11]:
            rel, kind = "subset", "significant change" if r[10] else "minor change"
        else:
            raise ValueError(f"{src}: no change type")
        if r[12]:
            kind += ", new organization-defined parameter"
        yield src, [str(r[6]).strip()], rel, f"NIST change analysis: {kind}"


def build(path):
    r2, r3 = (
        requirements("nist-800-171-rev2.yaml"),
        requirements("nist-800-171-rev3.yaml"),
    )
    maps, seen, used = [], set(), set()
    for src, targets, rel, annotation in nist_rows(path):
        assert src in r2 and src not in seen, src
        seen.add(src)
        for tgt in targets:
            assert tgt in r3, (src, tgt)
            if (src, tgt) in OVERRIDES:
                used.add((src, tgt))
                rel_o, reason = OVERRIDES[(src, tgt)]
                if rel_o is None:
                    continue
                maps.append(mapping(src, tgt, rel_o, f"{annotation}; {reason}"))
            else:
                maps.append(mapping(src, tgt, rel, annotation))
    assert used == set(OVERRIDES), set(OVERRIDES) - used
    for src, tgt, rel, reason in ADDITIONS:
        assert (
            src in r2
            and tgt in r3
            and (src, tgt)
            not in {
                (
                    m["source_requirement_urn"][len(U2) :],
                    m["target_requirement_urn"][len(U3) :],
                )
                for m in maps
            }
        )
        maps.append(
            mapping(src, tgt, rel, f"Not in the NIST change analysis: {reason}")
        )
    assert seen == r2, r2 - seen
    maps.sort(
        key=lambda m: [
            int(x) for x in m["source_requirement_urn"][len(U2) :].split(".")
        ]
    )

    name = "nist-800-171-rev2 <-> nist-800-171-rev3"
    desc = "Mapping between NIST SP 800-171 Rev. 2 and NIST SP 800-171 Rev. 3, derived from the NIST change analysis (Rev. 2 to Rev. 3)"
    fwd = {
        "urn": f"urn:intuitem:risk:req_mapping_set:{RID}",
        "ref_id": RID,
        "name": name,
        "description": desc,
        "source_framework_urn": "urn:intuitem:risk:framework:nist-800-171-rev2",
        "target_framework_urn": "urn:intuitem:risk:framework:nist-800-171-rev3",
        "requirement_mappings": maps,
    }
    rev = dict(
        fwd,
        urn=fwd["urn"] + "-revert",
        ref_id=RID + "-revert",
        source_framework_urn=fwd["target_framework_urn"],
        target_framework_urn=fwd["source_framework_urn"],
        requirement_mappings=[
            dict(
                m,
                source_requirement_urn=m["target_requirement_urn"],
                target_requirement_urn=m["source_requirement_urn"],
                relationship=FLIP.get(m["relationship"], m["relationship"]),
            )
            for m in maps
        ],
    )
    lib = {
        "urn": f"urn:intuitem:risk:library:{RID}",
        "locale": "en",
        "ref_id": RID,
        "name": name,
        "description": desc,
        "copyright": "Public domain (NIST)",
        "version": 1,
        "publication_date": datetime.date(2026, 11, 19),
        "provider": "intuitem",
        "packager": "intuitem",
        "dependencies": [
            "urn:intuitem:risk:library:nist-800-171-rev2",
            "urn:intuitem:risk:library:nist-800-171-rev3",
        ],
        "objects": {"requirement_mapping_sets": [fwd, rev]},
    }
    (LIB / f"{RID}.yaml").write_text(
        yaml.safe_dump(lib, sort_keys=False, allow_unicode=True, width=88)
    )
    print(len(maps), "mappings", dict(Counter(m["relationship"] for m in maps)))
    print(
        "Rev. 2 not mapped:",
        sorted(r2 - {m["source_requirement_urn"][len(U2) :] for m in maps}),
    )
    print(
        "Rev. 3 not reached:",
        sorted(r3 - {m["target_requirement_urn"][len(U3) :] for m in maps}),
    )


if __name__ == "__main__":
    build(sys.argv[1])
