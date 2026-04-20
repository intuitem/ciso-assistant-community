#!/usr/bin/env python3
"""Slice items from a parsed framework JSON by Category.

Top-level NIST CSF Functions (ID/PR/DE/RS/RC/GV) are too coarse to drive
section-affinity mapping. This helper groups items by Category level
(e.g. ID.AM, PR.AC, GV.OC) — where real cross-framework mapping happens.

Usage
-----
    python cat_slice.py /tmp/src.json ID.AM
    python cat_slice.py /tmp/tgt.json ID.AM,GV.OC,GV.RR

    # List category counts (no filter arg)
    python cat_slice.py /tmp/src.json

Also supports `PRAC_TYPO` as a special pseudo-category for frameworks
where `R.AC-*` items are typos for `PR.AC-*` (e.g. ccb-cff-2023-03-01).
Combine with real categories: `PR.AC,PRAC_TYPO`.

Emits JSON (list of {ref_id, urn, desc}) to stdout, or a summary table
to stderr when no filter is given.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict


# Strip CCB-style level prefixes: BASIC_/IMPORTANT_/KEY_
_LEVEL_PREFIX = re.compile(r"^(BASIC_|IMPORTANT_|KEY_)")
# NIST CSF function + category: e.g. ID.AM, PR.AA, GV.OC
_CSF_CAT = re.compile(r"^(GV|ID|PR|DE|RS|RC)\.([A-Z]{2})")
# ISO Annex A: A.5.1 → A.5
_ISO_ANNEX = re.compile(r"^A\.(\d+)")
# Generic numeric-prefixed ref_ids: 10.1.1 → 10, 5.1 → 5
_NUMERIC = re.compile(r"^(\d+)\.")


def extract_category(ref_id: str) -> str | None:
    """Return a Category label for a ref_id, or None if no pattern matches.

    Tries: NIST CSF (ID.AM) → ISO Annex A (A.5) → numeric prefix (5).
    """
    if not ref_id:
        return None
    stripped = _LEVEL_PREFIX.sub("", ref_id.upper())
    m = _CSF_CAT.match(stripped)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    m = _ISO_ANNEX.match(stripped)
    if m:
        return f"A.{m.group(1)}"
    m = _NUMERIC.match(stripped)
    if m:
        return m.group(1)
    return None


def _matches_typos(ref_id: str) -> bool:
    """CCB-style source typo: R.AC-* (missing the 'P').

    Case-insensitive and strips CCB level prefixes (BASIC_/IMPORTANT_/KEY_)
    so variants like `BASIC_R.AC-3.4` or `important_r.ac-3.4` are caught.
    """
    if not ref_id:
        return False
    stripped = _LEVEL_PREFIX.sub("", ref_id.upper())
    return stripped.startswith("R.AC-")


def slice_by_category(parsed: dict, cats: set[str]) -> list[dict]:
    include_typos = "PRAC_TYPO" in cats
    out: list[dict] = []
    for it in parsed["items"]:
        c = extract_category(it["ref_id"])
        hit = (c is not None and c in cats) or (
            include_typos and _matches_typos(it["ref_id"])
        )
        if not hit:
            continue
        out.append(
            {
                "ref_id": it["ref_id"],
                "urn": it["urn"],
                "desc": (it.get("description") or "").strip(),
            }
        )
    return out


def summarize_categories(parsed: dict) -> dict[str, list[str]]:
    """Group ref_ids by extracted category (None bucket for unmatched)."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for it in parsed["items"]:
        c = extract_category(it["ref_id"]) or "OTHER"
        buckets[c].append(it["ref_id"])
    return dict(sorted(buckets.items(), key=lambda kv: (kv[0] == "OTHER", kv[0])))


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("parsed_json", help="Output of parse_framework.py")
    p.add_argument(
        "categories",
        nargs="?",
        default=None,
        help="Comma-separated categories (e.g. 'ID.AM,GV.OC'). Omit to print summary.",
    )
    args = p.parse_args()

    parsed = json.load(open(args.parsed_json))

    if not args.categories:
        buckets = summarize_categories(parsed)
        print(
            f"{parsed.get('framework_name') or parsed.get('framework_ref_id')} — "
            f"{parsed.get('n_assessable', 0)} items",
            file=sys.stderr,
        )
        for cat, refs in buckets.items():
            print(
                f"  {cat:10s} : {len(refs):3d} items   e.g. {refs[0]}", file=sys.stderr
            )
        return 0

    cats = set(c.strip() for c in args.categories.split(","))
    out = slice_by_category(parsed, cats)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
