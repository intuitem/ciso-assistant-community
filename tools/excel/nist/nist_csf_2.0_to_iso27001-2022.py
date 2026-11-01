"""
Refresh the requirement mappings of mapping-nist-csf-2.0-to-iso27001-2022.yaml
from the ISO/IEC 27001:2022 informative references of the NIST CSF 2.0 Reference Tool.

Download the export (csf2.xlsx) from:
https://csrc.nist.gov/extensions/nudp/services/json/csf/download?olirids=all

Usage:
python nist_csf_2.0_to_iso27001-2022.py csf2.xlsx

Both mapping sets of the library (direct and -revert) are rewritten in place; the library
metadata (version, publication_date) is left for you to bump.
Any reference line or node id this script does not recognize stops it with an error,
so that a change in NIST's export format cannot silently drop mappings.
"""

import re
import sys
from pathlib import Path

import openpyxl
import yaml

LIBRARIES = Path(__file__).resolve().parents[3] / "backend/library/libraries"
MAPPING_FILE = LIBRARIES / "mapping-nist-csf-2.0-to-iso27001-2022.yaml"
PREFIX = "ISO/IEC 27001:2022:"
# NIST writes Annex A references both as "Annex A Controls: 5.30" and "Control 5.30"
KINDS = {"Mandatory Clause": "", "Annex A Controls": "a.", "Control": "a."}
# Typos in the NIST export
NIST_TYPOS = {"6.11": "6.1.1", "6.13": "6.1.3"}


def assessable_nodes(framework_file):
    """Node id (last URN segment) -> URN, for the assessable nodes of a framework library."""
    framework = yaml.safe_load((LIBRARIES / framework_file).read_text())["objects"][
        "framework"
    ]
    return {
        n["urn"].split(":")[-1]: n["urn"]
        for n in framework["requirement_nodes"]
        if n.get("assessable")
    }


def to_targets(kind, token, targets):
    """Map one NIST reference to assessable target nodes (a parent clause expands to its sub-clauses)."""
    token = re.sub(r"\s*\([a-z]\)$", "", token)  # "4.2(b)" -> "4.2"
    if not re.fullmatch(r"\d+(\.\d+)*", token):
        sys.exit(f"unrecognized ISO/IEC 27001 id: {token!r}")
    if kind == "Mandatory Clause":
        token = NIST_TYPOS.get(token, token)
    node = KINDS[kind] + token
    expanded = (
        [node] if node in targets else [t for t in targets if t.startswith(node + ".")]
    )
    if not expanded:
        sys.exit(f"ISO/IEC 27001 id not in the target framework: {node!r}")
    return expanded


sources = assessable_nodes("nist-csf-2.0.yaml")
targets = assessable_nodes("iso27001-2022.yaml")

mappings = {}  # ordered set of (source, target)
for row in openpyxl.load_workbook(sys.argv[1], read_only=True)["CSF 2.0"].iter_rows(
    min_row=3, values_only=True
):
    function, category, subcategory, _, references = row[:5]
    # Functions and categories also carry references; only subcategories are mapped
    if function or category or not subcategory or not references:
        continue
    source = subcategory.split(":")[0].strip().lower()
    if source not in sources:
        sys.exit(f"NIST CSF 2.0 id not in the source framework: {source!r}")
    for line in references.split("\n"):
        line = line.strip()
        if not line.startswith(PREFIX):
            continue
        m = re.fullmatch(
            r"(Mandatory Clause|Annex A Controls|Control)\s*:?\s*(.*)",
            line[len(PREFIX) :].strip(),
        )
        if not m:
            sys.exit(f"unrecognized reference line for {source}: {line!r}")
        kind, ids = m.groups()
        if ids.strip() in ("", "None"):
            continue
        for token in filter(None, (t.strip() for t in ids.split(","))):
            for target in to_targets(kind, token, targets):
                mappings[(source, target)] = None

library = yaml.safe_load(MAPPING_FILE.read_text())
for mapping_set in library["objects"]["requirement_mapping_sets"]:
    revert = mapping_set["urn"].endswith("-revert")
    mapping_set["requirement_mappings"] = [
        {
            "source_requirement_urn": targets[t] if revert else sources[s],
            "target_requirement_urn": sources[s] if revert else targets[t],
            "relationship": "intersect",
        }
        for s, t in mappings
    ]
with open(MAPPING_FILE, "w") as f:
    yaml.dump(library, f, sort_keys=False, allow_unicode=False)
print(f"{len(mappings)} mappings written to {MAPPING_FILE}")
