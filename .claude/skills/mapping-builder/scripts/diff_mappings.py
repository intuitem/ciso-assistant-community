#!/usr/bin/env python3
"""Diff two mapping library YAMLs (or a verdicts JSONL vs a YAML).

Reports:
  - shared pairs (same source+target URN) — with relationship-label agreement
  - pairs only in A
  - pairs only in B
  - per-category coverage summary

Useful for:
  - evaluating a rebuild vs. a published mapping
  - auditing an extended mapping vs. the prior version
  - sanity-checking reverse coverage

Usage
-----
    python diff_mappings.py A.yaml B.yaml
    python diff_mappings.py A.yaml B.jsonl   # .jsonl = running verdicts
    python diff_mappings.py A.yaml B.yaml --sample 5   # show N examples per bucket

Stdlib + pyyaml only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml


def load_pairs(path: Path) -> dict[tuple[str, str], dict]:
    """Return {(src_urn, tgt_urn): mapping_dict} for the forward set.

    Supports:
      - mapping library YAMLs (objects.requirement_mapping_sets[0])
      - raw verdicts JSONL (one verdict per line)
    """
    suffix = path.suffix.lower()
    pairs: dict[tuple[str, str], dict] = {}

    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(open(path))
        sets = (data or {}).get("objects", {}).get("requirement_mapping_sets") or []
        if not sets:
            raise SystemExit(f"{path}: no requirement_mapping_sets found")
        fwd = sets[0].get("requirement_mappings") or []
        for m in fwd:
            key = (m["source_requirement_urn"], m["target_requirement_urn"])
            pairs[key] = m
    elif suffix in {".jsonl", ".ndjson"}:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                v = json.loads(line)
                key = (v["source_requirement_urn"], v["target_requirement_urn"])
                pairs[key] = v
    else:
        raise SystemExit(f"{path}: unsupported extension (want .yaml/.yml/.jsonl)")

    return pairs


def short(urn: str) -> str:
    return urn.split(":")[-1]


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("a", help="Mapping A (.yaml or .jsonl)")
    p.add_argument("b", help="Mapping B (.yaml or .jsonl)")
    p.add_argument(
        "--sample", type=int, default=5, help="Example pairs per bucket (default 5)"
    )
    p.add_argument(
        "--json", action="store_true", help="Emit a machine-readable JSON summary"
    )
    args = p.parse_args()

    a = load_pairs(Path(args.a))
    b = load_pairs(Path(args.b))

    shared = set(a) & set(b)
    only_a = set(a) - set(b)
    only_b = set(b) - set(a)

    same_rel = 0
    label_disagreement: list[tuple[tuple[str, str], str, str]] = []
    for k in shared:
        ra = (a[k].get("relationship") or "").lower()
        rb = (b[k].get("relationship") or "").lower()
        if ra == rb:
            same_rel += 1
        else:
            label_disagreement.append((k, ra, rb))

    if args.json:
        json.dump(
            {
                "a_total": len(a),
                "b_total": len(b),
                "shared": len(shared),
                "shared_same_rel": same_rel,
                "shared_diff_rel": len(shared) - same_rel,
                "only_a": len(only_a),
                "only_b": len(only_b),
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    print(f"A: {args.a}  ({len(a)} forward pairs)")
    print(f"B: {args.b}  ({len(b)} forward pairs)")
    print()
    print(f"Shared pairs:      {len(shared)}")
    print(f"  same rel label:  {same_rel}")
    print(f"  diff rel label:  {len(shared) - same_rel}")
    print(f"Only in A:         {len(only_a)}")
    print(f"Only in B:         {len(only_b)}")

    if label_disagreement and args.sample:
        print()
        print(
            f"Label disagreements (sample of {min(args.sample, len(label_disagreement))}):"
        )
        for k, ra, rb in label_disagreement[: args.sample]:
            print(f"  {short(k[0])} → {short(k[1])}   A={ra}  B={rb}")

    if only_a and args.sample:
        print()
        print(f"Only in A (sample of {min(args.sample, len(only_a))}):")
        for k in list(only_a)[: args.sample]:
            rel = (a[k].get("relationship") or "").lower()
            print(f"  {short(k[0])} → {short(k[1])}  [{rel}]")

    if only_b and args.sample:
        print()
        print(f"Only in B (sample of {min(args.sample, len(only_b))}):")
        for k in list(only_b)[: args.sample]:
            rel = (b[k].get("relationship") or "").lower()
            print(f"  {short(k[0])} → {short(k[1])}  [{rel}]")

    # Distribution by relationship for each side
    print()
    dist_a = Counter((a[k].get("relationship") or "").lower() for k in a)
    dist_b = Counter((b[k].get("relationship") or "").lower() for k in b)
    print(f"Relationship distribution — A: {dict(dist_a)}")
    print(f"Relationship distribution — B: {dict(dist_b)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
