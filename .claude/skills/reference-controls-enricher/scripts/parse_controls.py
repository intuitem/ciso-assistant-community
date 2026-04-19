#!/usr/bin/env python3
"""Parse a reference-control library YAML (typically key-reference-controls.yaml).

Outputs JSON to stdout with:
  - library_urn, library_ref_id, library_name, control_count
  - controls: list of {urn, slug, prefix, ref_id, name, category, csf_function,
                       description, annotation, typical_evidence, has_fr}
  - by_prefix: {doc: [slug,...], pol: [...], proc: [...], tech: [...],
                phys: [...], train: [...]}  (slug lists for quick narrowing)
  - slug_index: {slug: urn}

Stdlib + pyyaml only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml


def parse(yaml_path: Path) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    library_urn = data.get("urn") or ""
    library_ref_id = data.get("ref_id") or ""
    library_name = data.get("name") or ""

    controls = []
    by_prefix: dict[str, list[str]] = defaultdict(list)
    slug_index: dict[str, str] = {}

    for rc in data.get("objects", {}).get("reference_controls", []) or []:
        urn = rc["urn"]
        slug = urn.rsplit(":", 1)[-1]
        prefix = slug.split(".")[0] if "." in slug else ""
        fr = (rc.get("translations") or {}).get("fr") or {}

        controls.append(
            {
                "urn": urn,
                "slug": slug,
                "prefix": prefix,
                "ref_id": rc.get("ref_id", ""),
                "name": rc.get("name", ""),
                "name_fr": fr.get("name", ""),
                "category": rc.get("category", ""),
                "csf_function": rc.get("csf_function", ""),
                "description": (rc.get("description") or "").replace("\n", " "),
                "annotation": (rc.get("annotation") or "").replace("\n", "; "),
                "typical_evidence": rc.get("typical_evidence") or [],
                "has_fr": bool(fr.get("name")),
            }
        )
        by_prefix[prefix].append(slug)
        slug_index[slug] = urn

    return {
        "library_urn": library_urn,
        "library_ref_id": library_ref_id,
        "library_name": library_name,
        "control_count": len(controls),
        "controls": controls,
        "by_prefix": dict(by_prefix),
        "slug_index": slug_index,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse a reference-control library YAML")
    ap.add_argument("yaml_path")
    args = ap.parse_args()

    parsed = parse(Path(args.yaml_path))

    # Summary to stderr for visibility
    print(
        f"[parse_controls] {parsed['library_ref_id']}: "
        f"{parsed['control_count']} controls; "
        f"by prefix: "
        + ", ".join(f"{p}={len(v)}" for p, v in sorted(parsed["by_prefix"].items())),
        file=sys.stderr,
    )
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
