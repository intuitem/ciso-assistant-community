#!/usr/bin/env python3
"""Coverage / audit report for a reference-controls enrichment.

Inputs:
  parsed_framework_json   Output of parse_framework.py
  verdicts_jsonl          One verdict per line

Output (stdout):
  - Coverage: % assessable items with >= 1 target URN
  - Per-section coverage breakdown
  - Histogram of URNs-per-requirement
  - Confidence distribution
  - List of requirements with zero URNs
  - List of low-confidence verdicts (< threshold, default 5)
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    default_controls = (
        Path(__file__).resolve().parents[4]
        / "backend"
        / "library"
        / "libraries"
        / "key-reference-controls.yaml"
    )
    ap = argparse.ArgumentParser(description="Coverage report for enrichment")
    ap.add_argument("parsed_framework_json")
    ap.add_argument("verdicts_jsonl")
    ap.add_argument("--threshold", type=int, default=5)
    ap.add_argument(
        "--controls-file",
        default=str(default_controls),
        help="Reference-controls library YAML (to flag unknown target URNs)",
    )
    args = ap.parse_args()

    fw = json.loads(Path(args.parsed_framework_json).read_text(encoding="utf-8"))
    verdicts: dict[str, dict] = {}
    for line in Path(args.verdicts_jsonl).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        v = json.loads(line)
        verdicts[v["source_urn"]] = v

    # Overall coverage
    total = 0
    covered = 0
    zero_items: list[tuple[str, str, str]] = []  # (ref_id, name, section)
    urn_counts_per_req: list[int] = []
    confs: list[float] = []
    per_section: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))

    per_section_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for it in fw.get("items", []):
        sec_label = (
            f"{it.get('section_ref_id', '')} {it.get('section_name', '')}".strip()
        )
        total += 1
        per_section_counts[sec_label][1] += 1
        v = verdicts.get(it["urn"])
        n = len((v or {}).get("target_urns") or [])
        urn_counts_per_req.append(n)
        if n > 0:
            covered += 1
            per_section_counts[sec_label][0] += 1
            conf = (v or {}).get("confidence")
            if isinstance(conf, (int, float)):
                confs.append(float(conf))
        else:
            zero_items.append((it.get("ref_id", ""), it.get("name", ""), sec_label))
    for sec, (c, t) in per_section_counts.items():
        per_section[sec] = (c, t)

    pct = 100.0 * covered / total if total else 0.0
    print(f"Coverage: {covered}/{total} ({pct:.1f}%)")
    print()
    print("By section:")
    for sec, (c, t) in per_section.items():
        if t == 0:
            continue
        print(f"  {c:4d}/{t:4d}  ({100.0 * c / t:5.1f}%)  {sec[:80]}")

    # URN histogram
    print()
    hist = Counter(urn_counts_per_req)
    print("URNs-per-requirement histogram:")
    for n in sorted(hist.keys()):
        bar = "#" * min(hist[n], 50)
        print(f"  {n}: {hist[n]:4d}  {bar}")

    # Confidence distribution
    if confs:
        print()
        cbuckets = Counter(int(c) for c in confs)
        print("Confidence distribution (of verdicts with a score):")
        for n in range(0, 11):
            if cbuckets.get(n):
                bar = "#" * min(cbuckets[n], 50)
                print(f"  {n:2d}: {cbuckets[n]:4d}  {bar}")

    # Low confidence list
    print()
    lows: list[dict] = []
    for v in verdicts.values():
        conf = v.get("confidence")
        if isinstance(conf, (int, float)) and conf < args.threshold:
            lows.append(v)
    if lows:
        print(f"Low-confidence verdicts (< {args.threshold}): {len(lows)}")
        for v in lows[:30]:
            print(
                f"  conf={v['confidence']}  {v['source_urn'].rsplit(':', 1)[-1]}  "
                f"-> {v.get('target_urns')}"
            )
        if len(lows) > 30:
            print(f"  ... ({len(lows) - 30} more)")
    else:
        print(f"No low-confidence verdicts (< {args.threshold}).")

    # Zero items
    print()
    if zero_items:
        print(f"Requirements with ZERO URNs: {len(zero_items)}")
        for ref, name, sec in zero_items[:20]:
            print(f"  [{sec[:30]}] {ref}  {name[:60]}")
        if len(zero_items) > 20:
            print(f"  ... ({len(zero_items) - 20} more)")
    else:
        print("No uncovered requirements.")

    # Unknown URNs (target URNs not defined in the controls library)
    print()
    cpath = Path(args.controls_file)
    if cpath.exists():
        import yaml  # local import — only needed for this check

        controls_data = yaml.safe_load(cpath.read_text(encoding="utf-8"))
        known_urns = {
            rc["urn"]
            for rc in controls_data.get("objects", {}).get("reference_controls") or []
        }
        unknown: dict[str, list[str]] = {}
        for v in verdicts.values():
            for tgt in v.get("target_urns") or []:
                if tgt not in known_urns:
                    unknown.setdefault(tgt, []).append(
                        v["source_urn"].rsplit(":", 1)[-1]
                    )
        if unknown:
            print(f"UNKNOWN target URNs (not defined in {cpath.name}): {len(unknown)}")
            for urn in sorted(unknown):
                cited = unknown[urn]
                sample = ", ".join(cited[:3]) + (" ..." if len(cited) > 3 else "")
                print(f"  {urn}   (cited by: {sample})")
        else:
            print(f"All target URNs are defined in {cpath.name}.")
    else:
        print(f"(controls file {cpath} not found — skipping URN validation)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
