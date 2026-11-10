"""Generate the ITSP.10.033 to NIST SP 800-53 rev5 mapping workbook.

ITSP.10.033 is the Canadian adaptation of NIST SP 800-53 rev5 and keeps its
identifiers, zero-padded (AC-02(01) for AC-2(1)). Each ITSP.10.033 item is
paired with the NIST item of the same identifier. The relationship, read from
ITSP.10.033 to NIST, comes from the two statements:

- equal: same statement once layout, spelling, abbreviations and generic
  Canadian terminology are normalised (COSMETIC, ABBREVIATIONS, TERMINOLOGY);
- superset: every NIST statement item is in the ITSP.10.033 statement, which
  adds items of its own (AA., BB., A.400.);
- anything else was read by a person and is listed in REWORDED or REVIEWED.

Families, withdrawn items, Canada-specific items (number 400 and above) and
items missing from the packaged NIST library are not mapped.

The script fails when REWORDED, REVIEWED or NOT_IN_NIST no longer match the
libraries, so a library update cannot silently change the mapping.
"""

import argparse
import re
from collections import Counter
from pathlib import Path

import yaml
from openpyxl import Workbook


# ========= CONFIG =========
SCRIPT_DIR = Path(__file__).resolve().parent
LIBRARIES_DIR = SCRIPT_DIR.parents[3] / "backend" / "library" / "libraries"
SOURCE_YAML = LIBRARIES_DIR / "itsp.10.033.yaml"
TARGET_YAML = LIBRARIES_DIR / "nist-sp-800-53-rev5.yaml"
OUTPUT_XLSX = SCRIPT_DIR.parent / "mapping-itsp.10.033-and-nist-sp-800-53-rev5.xlsx"
PACKAGER = "intuitem"
CANADIAN_ITEM_NUMBER = 400
# ==========================

EQUAL = "equal"
SUPERSET = "superset"
SUBSET = "subset"
INTERSECT = "intersect"

SYNTACTIC = "syntactic"
SEMANTIC = "semantic"

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
PADDED_CONTROL_RE = re.compile(r"\b([A-Z]{2})-0+(\d)")
PADDED_ENHANCEMENT_RE = re.compile(r"\(0(\d)\)")
# "a.", "A.1.a.", "AA.", "(a)", "1.", bullets.
ITEM_LABEL_RE = re.compile(
    r"^\s*(?:\(?[A-Za-z]{1,2}\)|\(?\d{1,2}\)"
    r"|[A-Za-z]{1,2}\.(?:\d{1,3}\.)*(?:[a-z]\.)?|\d{1,2}\.|•|-)\s+"
)
# "(EMSEC)", "(IOCs)" after the term they abbreviate.
PARENTHESISED_ABBREVIATION_RE = re.compile(r"\s*\([A-Z]{2,}s?\)")
TRAILING_CONJUNCTION_RE = re.compile(r"(?:[;:,.]\s*|\s+)(?:and/or|and|or)\s*$")
NIST_WITHDRAWN_RE = re.compile(r"^\[?Withdrawn")

# Spelling, hyphenation and number words.
COSMETIC = [
    (r"\bone or more\b", "1 or more"),
    (r"selection \(1\):", "selection:"),
    (r"at least 1 ", "at least one "),
    (r"\btwo\b", "2"),
    (r"behaviour", "behavior"),
    (r"rigour", "rigor"),
    (r"modelling", "modeling"),
    (r"labelling", "labeling"),
    (r"travelling", "traveling"),
    (r"\bdialling\b", "dialing"),
    (r"cancelled", "canceled"),
    (r"judgement", "judgment"),
    (r"defence", "defense"),
    (r"licence", "license"),
    (r"centre\b", "center"),
    (r"programme\b", "program"),
    (r"catalogue", "catalog"),
    (r"analyse", "analyze"),
    (r"colour", "color"),
    (r"authoris", "authoriz"),
    (r"organis", "organiz"),
    (r"cyber security", "cybersecurity"),
    (r"e-mail", "email"),
    (r"\bnon[ -]", "non"),
    (r"\bpre[ -]production", "preproduction"),
    (r"\bre[ -]e", "ree"),
    (r"\bon[ -]site", "onsite"),
    (r"\boff[ -]site", "offsite"),
    (r"life[ -]cycle", "lifecycle"),
    (r"tamper[ -]proof", "tamperproof"),
]

# Term written out on one side, abbreviated on the other.
ABBREVIATIONS = [
    (r"supply chain risk management", "scrm"),
    (r"\binformation technology\b", "it"),
    (r"multi-?factor authentication", "mfa"),
    (r"attribute-based access control", "abac"),
    (r"coordinated universal time", "utc"),
    (r"public key infrastructure", "pki"),
    (r"concept of operations", "conops"),
    (r"operations security", "opsec"),
    (r"mean time to failure", "mttf"),
]

# Canadian vocabulary for a notion NIST names differently.
TERMINOLOGY = [
    (r"personally identifiable information|\bpii\b", "personal information"),
    (r"\bhandling\b", "processing"),
    (r"\bhandles\b", "processes"),
    (r"\bhandled\b", "processed"),
    (r"\bhandle\b", "process"),
    (r"\bpias?\b|privacy (?:impact|risk) assessments?", "privacy risk assessment"),
    (r"orders in council", "executive orders"),
    (r",? jurisprudence", ""),
    (r" or custodian\b", ""),
    (r"\bcanada\b", "the nation"),
]

# ITSP.10.033 follows NIST SP 800-53 release 5.2.0, the packaged NIST library
# predates release 5.1.1.
NOT_IN_NIST = {
    "IA-13",
    "IA-13(01)",
    "IA-13(02)",
    "IA-13(03)",
    "SA-15(13)",
    "SA-24",
    "SI-02(07)",
}

# Same requirement with words reordered, regrouped or swapped for a synonym.
REWORDED = {
    "AC-17(04)",
    "AU-03",
    "CA-02",
    "CA-02(03)",
    "CP-02(05)",
    "CP-04(02)",
    "CP-08(05)",
    "IA-05(01)",
    "IR-02(03)",
    "IR-04(08)",
    "IR-07(02)",
    "IR-08(01)",
    "MA-03(02)",
    "PE-13(04)",
    "PE-14(01)",
    "PL-08",
    "PM-03",
    "PM-09",
    "PM-11",
    "PM-14",
    "PM-15",
    "PM-23",
    "PM-24",
    "PM-31",
    "PS-03(01)",
    "PS-03(02)",
    "PS-03(03)",
    "PS-03(04)",
    "PS-04",
    "PS-08",
    "PT-07",
    "RA-02",
    "SA-04",
    "SA-04(03)",
    "SA-04(11)",
    "SA-05",
    "SA-09(01)",
    "SA-11",
    "SA-11(01)",
    "SA-11(02)",
    "SA-15(02)",
    "SA-23",
    "SC-02(02)",
    "SC-07(04)",
    "SC-42(02)",
    "SI-04(11)",
    "SI-04(13)",
    "SI-04(18)",
    "SI-05",
    "SI-07(01)",
    "SI-07(02)",
    "SI-08(03)",
    "SR-11",
    "SR-11(02)",
}

# Statements the normalisation cannot settle, with what sets them apart.
REVIEWED = {
    "AC-02": (
        SUPERSET,
        "ITSP.10.033 adds data custodians, dormant accounts and periodic reviews.",
    ),
    "AC-08": (
        INTERSECT,
        "ITSP.10.033 replaces the consent to monitoring statement with Privacy Act notice content.",
    ),
    "AC-24": (EQUAL, "ITSP.10.033 lets both options be selected."),
    "CA-03": (
        EQUAL,
        "ITSP.10.033 lists information sharing agreements and arrangements among the agreement types.",
    ),
    "CA-08(03)": (EQUAL, "ITSP.10.033 lets both options be selected."),
    "CP-02": (
        SUPERSET,
        "ITSP.10.033 adds data integrity, impact on personal information and plan review by responsible individuals.",
    ),
    "CP-08(01)": (
        INTERSECT,
        "Priority Access for Dialing (ISED) instead of Telecommunications Service Priority.",
    ),
    "IA-02(01)": (SUPERSET, "ITSP.10.033 requires strong MFA."),
    "IA-02(12)": (
        INTERSECT,
        "GC-issued PKI hardware tokens instead of PIV credentials.",
    ),
    "IA-05(15)": (
        INTERSECT,
        "Products meeting the required assurance levels instead of GSA-approved products.",
    ),
    "IA-08(01)": (
        INTERSECT,
        "PKI credentials from GC departments instead of PIV credentials from federal agencies.",
    ),
    "IA-08(02)": (
        INTERSECT,
        "Authenticators at an ITSP.30.031 level of assurance instead of NIST-compliant ones.",
    ),
    "MA-03(03)": (SUPERSET, "ITSP.10.033 also covers personal information."),
    "MA-05(01)": (SUBSET, "ITSP.10.033 has no citizenship condition."),
    "MA-05(03)": (INTERSECT, "Canadian instead of U.S. citizens."),
    "MA-05(04)": (
        INTERSECT,
        "Systems jointly owned with Canada instead of the United States.",
    ),
    "MP-08(03)": (
        INTERSECT,
        "Protected information instead of controlled unclassified information.",
    ),
    "PE-03": (SUPERSET, "ITSP.10.033 adds access cards, safes and cipher locks."),
    "PM-02": (EQUAL, "Role title adapted to Canadian institutions."),
    "PM-05": (SUPERSET, "ITSP.10.033 also inventories programs."),
    "PM-05(01)": (SUPERSET, "ITSP.10.033 also inventories programs."),
    "PM-17": (
        INTERSECT,
        "Controlled information instead of controlled unclassified information.",
    ),
    "PM-18": (
        INTERSECT,
        "Plan built on the Privacy Act delegation of authority instead of the senior agency official for privacy. ITSP.10.033 adds communicating the plan.",
    ),
    "PM-19": (EQUAL, "Role title adapted to Canadian institutions."),
    "PM-20": (
        INTERSECT,
        "Info Source and the annual report to Parliament instead of public privacy reports and access to the senior agency official for privacy.",
    ),
    "PM-20(01)": (
        SUBSET,
        "ITSP.10.033 only requires policies where the privacy of visitors could be affected.",
    ),
    "PM-21": (
        INTERSECT,
        "Record of disclosures under the Privacy Act instead of the accounting of disclosures. ITSP.10.033 adds agreements before disclosure.",
    ),
    "PM-22": (
        INTERSECT,
        "ITSP.10.033 adds collection procedures and change records, NIST adds notice of deletions and appeals.",
    ),
    "PM-25": (
        SUPERSET,
        "ITSP.10.033 adds a restriction on disclosing datasets to external contractors.",
    ),
    "PM-26": (SUPERSET, "ITSP.10.033 requires responses made with discretion."),
    "PM-27": (
        SUPERSET,
        "ITSP.10.033 adds Privacy Act reporting to Parliament and TBS.",
    ),
    "PS-02": (
        INTERSECT,
        "Security screening requirements instead of position risk designations.",
    ),
    "PT-01": (
        EQUAL,
        "Same policy and procedures, named privacy policy in ITSP.10.033.",
    ),
    "PT-02": (SUBSET, "ITSP.10.033 covers collection and use, NIST all processing."),
    "PT-03": (
        INTERSECT,
        "Uses and disclosures under the Privacy Act (PIB, OPC and TBS notification) instead of processing purposes.",
    ),
    "PT-04": (
        INTERSECT,
        "ITSP.10.033 details consent for secondary uses and indirect collection, NIST covers consent to any processing.",
    ),
    "PT-05": (
        INTERSECT,
        "Notice content follows the Privacy Act. NIST adds timing, plain language and purposes.",
    ),
    "PT-05(01)": (
        SUPERSET,
        "ITSP.10.033 only accepts notice at the time of collection.",
    ),
    "PT-05(02)": (
        INTERSECT,
        "Privacy notice statements and PIBs instead of Privacy Act statements and systems of records.",
    ),
    "PT-06": (
        INTERSECT,
        "Personal information banks (TBS, Info Source) instead of system of records notices (OMB, Federal Register).",
    ),
    "PT-06(01)": (
        INTERSECT,
        "Consistent uses in the PIB instead of routine uses in the system of records notice.",
    ),
    "PT-06(02)": (
        INTERSECT,
        "Exempt banks under section 18 of the Privacy Act instead of U.S. Privacy Act exemptions.",
    ),
    "PT-07(01)": (
        INTERSECT,
        "Social insurance numbers instead of social security numbers, with different obligations.",
    ),
    "PT-07(02)": (
        INTERSECT,
        "Canadian Charter of Rights and Freedoms instead of the First Amendment.",
    ),
    "PT-08": (
        INTERSECT,
        "Data matching under information sharing agreements instead of the U.S. computer matching program.",
    ),
    "RA-08": (
        INTERSECT,
        "Different PIA triggers: ITSP.10.033 adds substantial modifications, NIST the federal collection criteria.",
    ),
    "SA-04(06)": (INTERSECT, "Cyber Centre approval instead of NSA."),
    "SA-04(07)": (
        INTERSECT,
        "Canadian Common Criteria Program instead of NIAP and NSA.",
    ),
    "SA-04(10)": (
        INTERSECT,
        "Products recommended by the Cyber Centre instead of the FIPS 201 approved products list.",
    ),
    "SA-09(08)": (INTERSECT, "Canada instead of the United States."),
    "SC-12(02)": (
        INTERSECT,
        "CMVP-validated or Cyber Centre approved instead of NIST FIPS-validated or NSA-approved.",
    ),
    "SC-12(03)": (INTERSECT, "Cyber Centre instead of NSA and DoD approval."),
    "SI-07(12)": (
        SUPERSET,
        "ITSP.10.033 covers all software, NIST user-installed software.",
    ),
    "SI-18": (
        INTERSECT,
        "ITSP.10.033 ensures rather than checks accuracy, only for information used for an administrative purpose.",
    ),
    "SI-18(03)": (
        SUBSET,
        "ITSP.10.033 limits direct collection to wherever possible.",
    ),
}
ADDED_ITEMS_NOTE = "ITSP.10.033 adds statement items."


def load_library(path: Path) -> tuple[dict, dict]:
    with open(path, encoding="utf-8") as file:
        library = yaml.safe_load(file)
    objects = library["objects"]
    return library, objects.get("framework") or objects["frameworks"][0]


def unpad(ref_id: str) -> str:
    return re.sub(r"(?<!\d)0+(?=\d)", "", ref_id)


def is_canadian(ref_id: str) -> bool:
    return any(
        int(number) >= CANADIAN_ITEM_NUMBER for number in re.findall(r"\d+", ref_id)
    )


def normalise(line: str, terminology: bool) -> str:
    text = MARKDOWN_LINK_RE.sub(r"\1", line).replace("**", "").replace(" ", " ")
    text = PADDED_CONTROL_RE.sub(r"\1-\2", text)
    text = PADDED_ENHANCEMENT_RE.sub(r"(\1)", text)
    for _ in range(3):
        text = ITEM_LABEL_RE.sub("", text)
    text = PARENTHESISED_ABBREVIATION_RE.sub("", text)
    text = text.lower().replace("’", "'")
    text = TRAILING_CONJUNCTION_RE.sub("", text)
    rules = COSMETIC + ABBREVIATIONS + (TERMINOLOGY if terminology else [])
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def statement_items(node: dict, terminology: bool) -> list[str]:
    lines = (node.get("description") or "").splitlines()
    return [item for line in lines if (item := normalise(line, terminology))]


def is_subsequence(short: list[str], long: list[str]) -> bool:
    remaining = iter(long)
    return all(item in remaining for item in short)


def compare_statements(source: dict, target: dict) -> tuple[str, str, str] | None:
    """Relationship, rationale and note, or None when a person has to decide."""
    for terminology, rationale in ((False, SYNTACTIC), (True, SEMANTIC)):
        source_items = statement_items(source, terminology)
        target_items = statement_items(target, terminology)
        if " ".join(source_items) == " ".join(target_items):
            return EQUAL, rationale, ""
    if len(source_items) > len(target_items) and is_subsequence(
        target_items, source_items
    ):
        return SUPERSET, SEMANTIC, ADDED_ITEMS_NOTE
    return None


def build_mappings(source_framework: dict, target_framework: dict):
    target_nodes = {
        node["ref_id"]: node
        for node in target_framework["requirement_nodes"]
        if node.get("assessable")
    }
    reviewed = {ref_id: (EQUAL, "") for ref_id in REWORDED} | REVIEWED
    mappings, skipped = [], Counter()
    unsettled, not_in_target = set(), set()

    for source in source_framework["requirement_nodes"]:
        ref_id = source.get("ref_id") or ""
        if source["depth"] == 1:
            skipped["family"] += 1
            continue
        if is_canadian(ref_id):
            skipped["Canada-specific"] += 1
            continue
        target = target_nodes.get(unpad(ref_id))
        if not source["assessable"] or (
            target and NIST_WITHDRAWN_RE.match(target.get("description") or "")
        ):
            skipped["withdrawn"] += 1
            continue
        if target is None:
            skipped["not in the NIST library"] += 1
            not_in_target.add(ref_id)
            continue

        result = compare_statements(source, target)
        if result is None:
            unsettled.add(ref_id)
            relationship, note = reviewed.get(ref_id, (None, ""))
            result = (relationship, SEMANTIC, note)
        mappings.append((source["urn"], target["urn"], *result))

    if not_in_target != NOT_IN_NIST:
        raise ValueError(
            "NOT_IN_NIST is out of date, "
            f"missing: {sorted(not_in_target - NOT_IN_NIST)}, "
            f"stale: {sorted(NOT_IN_NIST - not_in_target)}"
        )
    if unsettled != set(reviewed) or REWORDED & set(REVIEWED):
        raise ValueError(
            "REWORDED and REVIEWED are out of date, "
            f"to review: {sorted(unsettled - set(reviewed))}, "
            f"settled by the normalisation: {sorted(set(reviewed) - unsettled)}, "
            f"listed twice: {sorted(REWORDED & set(REVIEWED))}"
        )
    return mappings, skipped


def node_base_urn(framework: dict) -> str:
    return framework["requirement_nodes"][0]["urn"].rsplit(":", 1)[0]


def write_reference_sheet(workbook: Workbook, title: str, framework: dict) -> None:
    sheet = workbook.create_sheet(title)
    sheet.append(["node_id", "assessable", "urn", "ref_id", "name", "description"])
    for node in framework["requirement_nodes"]:
        sheet.append(
            [
                node["urn"].rsplit(":", 1)[1] if node["assessable"] else "",
                node["assessable"],
                node["urn"],
                node.get("ref_id"),
                node.get("name"),
                node.get("description"),
            ]
        )


def build_excel(output_xlsx: Path = OUTPUT_XLSX) -> Path:
    source_library, source_framework = load_library(SOURCE_YAML)
    target_library, target_framework = load_library(TARGET_YAML)
    mappings, skipped = build_mappings(source_framework, target_framework)

    source_urn = source_framework["urn"]
    target_urn = target_framework["urn"]
    ref_id = f"mapping-{source_urn.split(':')[-1]}-and-{target_urn.split(':')[-1]}"
    name = f"{source_framework['ref_id']} <-> {target_framework['ref_id']}"
    description = (
        f"Mapping between {source_framework['name']} and {target_framework['name']}"
    )

    workbook = Workbook()
    workbook.remove(workbook.active)

    sheet = workbook.create_sheet("library_meta")
    for row in (
        ("type", "library"),
        ("urn", f"urn:{PACKAGER}:risk:library:{ref_id}"),
        ("version", "1"),
        ("locale", "en"),
        ("ref_id", ref_id),
        ("name", name),
        ("description", description),
        ("copyright", PACKAGER),
        ("provider", PACKAGER),
        ("packager", PACKAGER),
        ("dependencies", f"{source_library['urn']}, {target_library['urn']}"),
    ):
        sheet.append(row)

    sheet = workbook.create_sheet("mappings_meta")
    for row in (
        ("type", "requirement_mapping_set"),
        ("urn", f"urn:{PACKAGER}:risk:req_mapping_set:{ref_id}"),
        ("ref_id", ref_id),
        ("name", name),
        ("description", description),
        ("source_framework_urn", source_urn),
        ("target_framework_urn", target_urn),
        ("source_node_base_urn", node_base_urn(source_framework)),
        ("target_node_base_urn", node_base_urn(target_framework)),
    ):
        sheet.append(row)

    sheet = workbook.create_sheet("mappings_content")
    sheet.append(
        [
            "source_node_id",
            "target_node_id",
            "relationship",
            "rationale",
            "strength_of_relationship",
            "annotation",
        ]
    )
    for source_node_urn, target_node_urn, relationship, rationale, note in mappings:
        sheet.append(
            [
                source_node_urn.rsplit(":", 1)[1],
                target_node_urn.rsplit(":", 1)[1],
                relationship,
                rationale,
                None,
                note or None,
            ]
        )

    sheet = workbook.create_sheet("guidelines")
    for row in (
        ("source_node_id", "use the last segment of the source URN"),
        ("target_node_id", "use the last segment of the target URN"),
        ("relationships", "use one of the following values"),
        ("", "subset"),
        ("", "intersect"),
        ("", "equal"),
        ("", "superset"),
        ("", "not_related"),
        ("rationale", "use one of the following values (or leave empty)"),
        ("", "syntactic"),
        ("", "semantic"),
        ("", "functional"),
        ("strength_of_relationship", "use an integer or empty value"),
    ):
        sheet.append(row)

    write_reference_sheet(workbook, "source", source_framework)
    write_reference_sheet(workbook, "target", target_framework)
    workbook.save(output_xlsx)

    relationships = Counter(mapping[2] for mapping in mappings)
    print(f"{len(mappings)} mappings: {dict(relationships.most_common())}")
    print(f"Not mapped: {dict(skipped)}")
    return output_xlsx


def main():
    parser = argparse.ArgumentParser(
        description="Generate the ITSP.10.033 to NIST SP 800-53 rev5 mapping Excel."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_XLSX,
        help=f"Output Excel file path (default: {OUTPUT_XLSX.name})",
    )
    args = parser.parse_args()
    print(f'✅ Export complete: "{build_excel(args.output)}"')


if __name__ == "__main__":
    main()
