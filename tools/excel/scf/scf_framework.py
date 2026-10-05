"""
Build a CISO Assistant v2 library workbook from an official SCF Excel release.

Usage:
    python scf_framework.py secure-controls-framework-scf-2026-3.xlsx 2026.3 [--publication-date 2026-09-21]

Input:
    - Official SCF workbook containing a sheet named "SCF <version>"
    - Relevant columns:
        * "SCF Domain"
        * "SCF Control"
        * "SCF #"
        * "Secure Controls Framework (SCF)\nControl Description"
        * "SCF Control Question"
        * "SCRM Focus\n\nTIER 1\nSTRATEGIC"
        * "SCRM Focus\n\nTIER 2\nOPERATIONAL"
        * "SCRM Focus\n\nTIER 3\nTACTICAL"

Processing:
    - For each new "SCF Domain", insert a depth=1 row (ref_id = control prefix, e.g. "GOV").
    - For each control, insert a depth=2 row with:
        * assessable = "x" (empty for "[deprecated" controls)
        * ref_id = "SCF #"
        * name = "SCF Control"
        * description = control description
        * annotation = control question
        * implementation_groups = comma-separated SCRM tiers (e.g. "tier1,tier3")

Output:
    - "scf-<version>.xlsx", a v2 library workbook ready for convert_library_v2.py
"""

import argparse
import json
from datetime import date

import openpyxl
import pandas as pd

COL_DOMAIN = "SCF Domain"
COL_CONTROL = "SCF Control"
COL_ID = "SCF #"
COL_DESCRIPTION = "Secure Controls Framework (SCF)\nControl Description"
COL_QUESTION = "SCF Control Question"
TIER_COLUMNS = {
    "tier1": "SCRM Focus\n\nTIER 1\nSTRATEGIC",
    "tier2": "SCRM Focus\n\nTIER 2\nOPERATIONAL",
    "tier3": "SCRM Focus\n\nTIER 3\nTACTICAL",
}

IMPLEMENTATION_GROUPS = [
    ("tier1", "Tier 1 - Strategic"),
    ("tier2", "Tier 2 - Operational"),
    ("tier3", "Tier 3 - Tactical"),
]

# Verbatim from the SCF "Cybersecurity & Data Privacy Capability Maturity Model (C|P-CMM)"
SCORES = [
    (
        0,
        "Not Performed",
        (
            "This level of maturity is defined as “non-existence practices,” where the "
            "control is not being performed. Practices are non-existent, where a "
            "reasonable person would conclude the control is not being performed."
        ),
    ),
    (
        1,
        "Performed Informally",
        (
            "This level of maturity is defined as “ad hoc practices,” where the control "
            "is being performed, but lacks completeness & consistency. Performance "
            "depends on specific knowledge and effort of the individual performing the "
            "task(s), where the performance of these practices is not proactively governed."
        ),
    ),
    (
        2,
        "Planned & Tracked",
        (
            "Practices are “requirements-driven” where the intent of control is met in "
            "some circumstances, but not standardized across the entire organization. "
            "Controls are implemented in some, but not all applicable "
            "circumstances/environments (e.g., specific enclaves, facilities or locations)."
        ),
    ),
    (
        3,
        "Well Defined",
        (
            "This level of maturity is defined as “enterprise-wide standardization,” "
            "where the practices are well-defined and standardized across the "
            "organization. Controls are implemented in all applicable "
            "circumstances/environments (deviations are documented and justified)."
        ),
    ),
    (
        4,
        "Quantitatively Controlled",
        (
            "This level of maturity is defined as “metrics-driven practices,” where in "
            "addition to being well-defined and standardized practices across the "
            "organization, there are detailed metrics to enable governance oversight."
        ),
    ),
    (
        5,
        "Continuously Improving",
        (
            "This level of maturity is defined as “world-class practices,” where the "
            "practices are not only well-defined and standardized across the "
            "organization, as well as having detailed metrics, but the process is "
            "continuously improving."
        ),
    ),
]

FIELD_VISIBILITY = {
    "score": {"auditor": "edit", "respondent": "hidden"},
    "is_scored": {"auditor": "edit", "respondent": "hidden"},
    "documentation_score": {"auditor": "hidden", "respondent": "hidden"},
    "result": {"auditor": "edit", "respondent": "edit"},
    "extended_result": {"auditor": "hidden", "respondent": "hidden"},
    "status": {"auditor": "hidden", "respondent": "hidden"},
    "task_templates": {"auditor": "hidden", "respondent": "hidden"},
    "applied_controls": {"auditor": "edit", "respondent": "edit"},
}

DESCRIPTION = (
    "SCF: Secure Controls Framework\nhttps://securecontrolsframework.com/about-us/"
)


def clean(value):
    if pd.isna(value):
        return None
    return str(value).strip() or None


def build_content(source_file, sheet_name):
    df = pd.read_excel(
        source_file,
        sheet_name=sheet_name,
        usecols=[COL_DOMAIN, COL_CONTROL, COL_ID, COL_DESCRIPTION, COL_QUESTION]
        + list(TIER_COLUMNS.values()),
    )
    rows = []
    previous_domain = None
    for _, row in df.iterrows():
        ref_id = clean(row[COL_ID])
        if not ref_id:
            continue
        domain = clean(row[COL_DOMAIN])
        if not domain:
            raise ValueError(f'Control "{ref_id}" has no "{COL_DOMAIN}"')
        if domain != previous_domain:
            rows.append((None, 1, ref_id.split("-")[0], domain, None, None, None))
            previous_domain = domain

        tiers = [
            tier
            for tier, column in TIER_COLUMNS.items()
            if str(row[column]).strip().lower() == "x"
        ]
        description = clean(row[COL_DESCRIPTION])
        is_deprecated = bool(description) and description.lower().startswith(
            "[deprecated"
        )
        rows.append(
            (
                None if is_deprecated else "x",
                2,
                ref_id,
                clean(row[COL_CONTROL]),
                description,
                clean(row[COL_QUESTION]),
                ",".join(tiers) or None,
            )
        )
    return rows


def write_workbook(destination_file, version, publication_date, content_rows):
    ref_id = f"scf-{version}"
    name = f"SCF: Secure Controls Framework ({version})"

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    def sheet(title, rows):
        ws = wb.create_sheet(title)
        for r in rows:
            ws.append(list(r))
            for cell in ws[ws.max_row]:
                if cell.data_type == "f":
                    cell.data_type = "s"

    library_meta = [
        ("type", "library"),
        ("urn", f"urn:intuitem:risk:library:{ref_id}"),
        ("version", "1"),
        ("locale", "en"),
        ("ref_id", ref_id),
        ("name", name),
        ("description", DESCRIPTION),
        ("copyright", "SCF - https://securecontrolsframework.com/terms-conditions/"),
        ("provider", "SCF"),
        ("packager", "intuitem"),
    ]
    if publication_date:
        library_meta.append(("publication_date", publication_date))
    sheet("library_meta", library_meta)
    sheet(
        "scf_meta",
        [
            ("type", "framework"),
            ("base_urn", f"urn:intuitem:risk:req_node:{ref_id}"),
            ("urn", f"urn:intuitem:risk:framework:{ref_id}"),
            ("ref_id", ref_id),
            ("name", name),
            ("description", DESCRIPTION),
            ("implementation_groups_definition", "imp-grp"),
            ("min_score", 0),
            ("max_score", 5),
            ("scores_definition", "scores"),
            ("field_visibility", json.dumps(FIELD_VISIBILITY)),
        ],
    )
    sheet(
        "scf_content",
        [
            (
                "assessable",
                "depth",
                "ref_id",
                "name",
                "description",
                "annotation",
                "implementation_groups",
            )
        ]
        + content_rows,
    )
    sheet("imp-grp_meta", [("type", "implementation_groups"), ("name", "imp-grp")])
    sheet(
        "imp-grp_content",
        [("ref_id", "name", "description")]
        + [(r, n, None) for r, n in IMPLEMENTATION_GROUPS],
    )
    sheet("scores_meta", [("type", "scores"), ("name", "scores")])
    sheet(
        "scores_content",
        [("score", "name", "description")] + SCORES,
    )
    wb.save(destination_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("source_file", help="Official SCF workbook")
    parser.add_argument("version", help='SCF version, e.g. "2026.3"')
    parser.add_argument(
        "--publication-date", type=date.fromisoformat, help="YYYY-MM-DD"
    )
    parser.add_argument("--output", help='Defaults to "scf-<version>.xlsx"')
    args = parser.parse_args()

    content_rows = build_content(args.source_file, f"SCF {args.version}")
    destination_file = args.output or f"scf-{args.version}.xlsx"
    write_workbook(destination_file, args.version, args.publication_date, content_rows)
    controls = sum(1 for r in content_rows if r[1] == 2)
    domains = sum(1 for r in content_rows if r[1] == 1)
    print(
        f'✅ Destination file created: "{destination_file}" ({domains} domains, {controls} controls)'
    )


if __name__ == "__main__":
    main()
