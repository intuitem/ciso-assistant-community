#!/usr/bin/env python3
"""Apply reference-control URN assignments to a framework YAML.

Inputs:
  framework_yaml   Path to the framework YAML to patch (in place).
  verdicts_jsonl   JSON-lines file with one verdict per line:
                   {"source_urn": "...", "target_urns": ["...", ...],
                    "rationale": "...", "confidence": 0-10}
  --controls-lib-urn   Library URN to add to `dependencies`
                       (default: urn:intuitem:risk:library:doc-pol)

Behaviour:
  - For each verdict, find the requirement_node by source_urn.
  - Append target_urns to its `reference_controls` list, keeping order and
    deduplicating against pre-existing entries.
  - If any URN was added, ensure `controls-lib-urn` is in the top-level
    `dependencies` list.
  - Version bump optional via --bump.
  - Write the YAML back (pyyaml dump; non-ASCII escaped to minimize diff
    churn on existing libraries that use the same style).

Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def load_verdicts(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(json.loads(line))
    return out


def main() -> int:
    default_controls = (
        Path(__file__).resolve().parents[4]
        / "backend"
        / "library"
        / "libraries"
        / "key-reference-controls.yaml"
    )
    ap = argparse.ArgumentParser(
        description="Apply reference-control URN assignments to a framework YAML"
    )
    ap.add_argument("framework_yaml")
    ap.add_argument("verdicts_jsonl")
    ap.add_argument("--controls-lib-urn", default="urn:intuitem:risk:library:doc-pol")
    ap.add_argument(
        "--controls-file",
        default=str(default_controls),
        help="Path to the reference-controls library YAML used to validate target URNs",
    )
    ap.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation that target URNs exist in --controls-file",
    )
    ap.add_argument("--bump", action="store_true", help="Increment library version")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fpath = Path(args.framework_yaml)
    vpath = Path(args.verdicts_jsonl)

    data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
    verdicts = load_verdicts(vpath)

    # Validate that every target URN exists in the controls library.
    # This catches typos and stale slugs before they're written into the framework.
    if not args.skip_validation:
        cpath = Path(args.controls_file)
        if not cpath.exists():
            print(
                f"ERROR: controls file not found: {cpath}\n"
                f"Pass --controls-file <path> or --skip-validation.",
                file=sys.stderr,
            )
            return 2
        controls_data = yaml.safe_load(cpath.read_text(encoding="utf-8"))
        known_urns = {
            rc["urn"]
            for rc in controls_data.get("objects", {}).get("reference_controls") or []
        }
        unknown: dict[str, list[str]] = {}
        for v in verdicts:
            for tgt in v.get("target_urns") or []:
                if tgt not in known_urns:
                    unknown.setdefault(tgt, []).append(
                        v["source_urn"].rsplit(":", 1)[-1]
                    )
        if unknown:
            print(
                f"ERROR: {len(unknown)} unknown target URN(s) in verdicts "
                f"(not defined in {cpath.name}):",
                file=sys.stderr,
            )
            for urn in sorted(unknown):
                cited = unknown[urn]
                sample = ", ".join(cited[:3]) + (" ..." if len(cited) > 3 else "")
                print(f"  {urn}   (cited by: {sample})", file=sys.stderr)
            print(
                "Fix the verdicts file, or re-run with --skip-validation to bypass.",
                file=sys.stderr,
            )
            return 2

    nodes = data["objects"]["framework"]["requirement_nodes"]
    by_urn = {n["urn"]: n for n in nodes}

    urns_added = 0
    reqs_touched = 0
    missing: list[str] = []

    for v in verdicts:
        src = v["source_urn"]
        tgts = v.get("target_urns") or []
        if not tgts:
            continue
        node = by_urn.get(src)
        if node is None:
            missing.append(src)
            continue
        existing = list(node.get("reference_controls") or [])
        added_this = 0
        for t in tgts:
            if t not in existing:
                existing.append(t)
                urns_added += 1
                added_this += 1
        if added_this:
            node["reference_controls"] = existing
            reqs_touched += 1

    # Ensure dependency
    if urns_added:
        deps = list(data.get("dependencies") or [])
        if args.controls_lib_urn not in deps:
            deps.append(args.controls_lib_urn)
            data["dependencies"] = deps

    if args.bump and urns_added:
        try:
            data["version"] = int(data.get("version", 1)) + 1
        except (TypeError, ValueError):
            pass

    print(f"URNs added: {urns_added}", file=sys.stderr)
    print(f"Requirements touched: {reqs_touched}", file=sys.stderr)
    if missing:
        print(f"WARN: {len(missing)} verdict source URNs not found", file=sys.stderr)
        for m in missing[:5]:
            print(f"  {m}", file=sys.stderr)

    if args.dry_run:
        print("[dry-run] not writing", file=sys.stderr)
        return 0

    out = yaml.dump(
        data,
        allow_unicode=False,
        sort_keys=False,
        width=80,
        default_flow_style=False,
    )
    fpath.write_text(out, encoding="utf-8")
    print(f"Wrote {fpath}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
