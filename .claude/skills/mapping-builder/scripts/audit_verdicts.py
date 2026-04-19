#!/usr/bin/env python3
"""Audit a verdicts JSONL (or mapping YAML) against a parsed source framework.

Reports:
  - source coverage: how many source items got at least one mapping
  - unmapped source items (candidates for missed sections)
  - verdicts by relationship type and strength distribution
  - low-strength (<= threshold) verdicts for borderline review

Usage
-----
    python audit_verdicts.py /tmp/src.json /tmp/verdicts.jsonl
    python audit_verdicts.py /tmp/src.json mapping.yaml --threshold 6

Stdlib + pyyaml only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml


def load_verdicts(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        out = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out
    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(open(path))
        sets = (data or {}).get("objects", {}).get("requirement_mapping_sets") or []
        if not sets:
            raise SystemExit(f"{path}: no requirement_mapping_sets found")
        return sets[0].get("requirement_mappings") or []
    raise SystemExit(f"{path}: unsupported extension (want .jsonl/.yaml)")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "src_parsed", help="Parsed source framework JSON (from parse_framework.py)"
    )
    p.add_argument("verdicts", help="Verdicts JSONL or mapping YAML")
    p.add_argument(
        "--threshold", type=int, default=6, help="Low-strength threshold (default 6)"
    )
    p.add_argument(
        "--show-unmapped", action="store_true", help="List every unmapped source item"
    )
    args = p.parse_args()

    src = json.load(open(args.src_parsed))
    verdicts = load_verdicts(Path(args.verdicts))

    src_items = {it["urn"]: it for it in src["items"]}
    verdict_sources = {v["source_requirement_urn"] for v in verdicts}
    # Only count URNs that actually exist in the parsed source for coverage.
    # URNs in verdicts but not in src are reported separately (typos / wrong direction).
    mapped = verdict_sources & set(src_items)
    unknown_sources = verdict_sources - set(src_items)
    unmapped = set(src_items) - mapped

    rel_dist = Counter((v.get("relationship") or "").lower() for v in verdicts)
    strengths: list[int] = []
    for v in verdicts:
        s = v.get("strength_of_relationship")
        if s is None:
            continue
        try:
            strengths.append(int(s))
        except (TypeError, ValueError):
            pass
    strength_dist: Counter[int] = Counter(strengths)

    print(f"Source: {src.get('framework_name') or src.get('framework_ref_id')}")
    print(f"  {src.get('n_assessable', 0)} assessable items")
    print()
    print(
        f"Coverage: {len(mapped)}/{len(src_items)} source items mapped "
        f"({100.0 * len(mapped) / max(len(src_items), 1):.1f}%)"
    )
    print(f"Total verdicts: {len(verdicts)}")
    if unknown_sources:
        print(
            f"WARNING: {len(unknown_sources)} verdict(s) reference source URNs not in "
            f"parsed framework (typos or reversed direction):"
        )
        for u in sorted(unknown_sources)[:10]:
            print(f"    {u}")
        if len(unknown_sources) > 10:
            print(f"    ... and {len(unknown_sources) - 10} more")
    print(f"Relationship distribution: {dict(rel_dist)}")
    if strength_dist:
        avg = sum(k * v for k, v in strength_dist.items()) / sum(strength_dist.values())
        print(
            f"Avg strength: {avg:.2f}   distribution: {dict(sorted(strength_dist.items()))}"
        )
    print()

    if unmapped:
        print(f"Unmapped source items ({len(unmapped)}):")
        # Flag empty-description items separately — they're usually YAML bugs, not real gaps.
        empty_desc = [
            u for u in unmapped if not (src_items[u].get("description") or "").strip()
        ]
        real_gaps = [u for u in unmapped if u not in set(empty_desc)]
        if empty_desc:
            print(
                f"  {len(empty_desc)} with empty descriptions (likely YAML bugs in source):"
            )
            for u in empty_desc:
                it = src_items[u]
                print(f"    {it['ref_id']}")
        if real_gaps:
            limit = None if args.show_unmapped else 10
            shown = real_gaps if limit is None else real_gaps[:limit]
            print(f"  {len(real_gaps)} with real content (potential missed mappings):")
            for u in shown:
                it = src_items[u]
                print(f"    {it['ref_id']}: {(it.get('description') or '')[:120]}")
            if limit is not None and len(real_gaps) > limit:
                print(
                    f"    ... and {len(real_gaps) - limit} more (use --show-unmapped)"
                )
        print()

    def _strength(v: dict) -> int | None:
        s = v.get("strength_of_relationship")
        if s is None:
            return None
        try:
            return int(s)
        except (TypeError, ValueError):
            return None

    # Missing strength treated as "not rated" → skip the low-strength filter
    # (not treated as 10, which previously hid strength==0 due to `or 10`).
    low = [
        v
        for v in verdicts
        if (_strength(v) is not None and _strength(v) <= args.threshold)
    ]
    if low:
        print(f"Low-strength verdicts (strength <= {args.threshold}, n={len(low)}):")
        for v in low:
            sr = v["source_requirement_urn"].split(":")[-1]
            tr = v["target_requirement_urn"].split(":")[-1]
            rel = v.get("relationship", "?")
            s = v.get("strength_of_relationship", "-")
            print(f"  [{rel} {s}] {sr} → {tr}")
            if v.get("rationale"):
                print(f"      {v['rationale']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
