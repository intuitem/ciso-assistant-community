#!/usr/bin/env python3
"""Parse a CISO Assistant framework YAML.

Outputs JSON to stdout with framework metadata and assessable items grouped
by top-level section, ready for Claude to reason over.

Usage
-----
    python parse_framework.py path/to/framework.yaml > parsed.json

Each item carries:
  - ref_id, urn, name, description
  - depth, parent_urn
  - section_urn / section_ref_id / section_name (the depth-1 ancestor)
  - full_sentence: name + description + parent/grandparent context, joined with " | "

Stdlib + pyyaml only. No third-party ML deps.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def _build_full_sentence(node: dict, all_nodes: dict[str, dict]) -> str:
    name = (node.get("name") or "").strip()
    desc = (node.get("description") or "").strip()
    if name and desc:
        current = f"{name}: {desc}"
    else:
        current = desc or name
    parts = [current] if current else []

    # Walk up to two ancestors of context.
    parent_urn = node.get("parent_urn")
    ancestors: list[str] = []
    depth_seen = 0
    while parent_urn and depth_seen < 2 and parent_urn in all_nodes:
        p = all_nodes[parent_urn]
        p_name = (p.get("name") or "").strip()
        p_desc = (p.get("description") or "").strip()
        if p_name and p_desc:
            ancestors.insert(0, f"{p_name}: {p_desc}")
        elif p_desc:
            ancestors.insert(0, p_desc)
        elif p_name:
            ancestors.insert(0, p_name)
        parent_urn = p.get("parent_urn")
        depth_seen += 1

    return " | ".join(ancestors + parts) if (ancestors or parts) else "No description"


def _find_section(node: dict, all_nodes: dict[str, dict]) -> dict | None:
    """Return the depth-1 ancestor (or self if depth 1, or None for depth 0)."""
    cur = node
    while cur is not None:
        if cur.get("depth") == 1:
            return cur
        parent_urn = cur.get("parent_urn")
        if not parent_urn:
            return None
        cur = all_nodes.get(parent_urn)
    return None


def parse(yaml_path: Path) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    library_urn = data.get("urn") or ""
    library_ref_id = data.get("ref_id") or ""

    framework = data.get("objects", {}).get("framework") or {}
    framework_urn = framework.get("urn") or ""
    framework_ref_id = framework.get("ref_id") or ""
    framework_name = framework.get("name") or ""
    nodes = framework.get("requirement_nodes") or []

    all_nodes = {n.get("urn"): n for n in nodes if n.get("urn")}

    items: list[dict] = []
    for node in nodes:
        if not node.get("assessable"):
            continue
        section = _find_section(node, all_nodes)
        items.append(
            {
                "ref_id": node.get("ref_id") or "",
                "urn": node.get("urn") or "",
                "name": node.get("name") or "",
                "description": node.get("description") or "",
                "depth": node.get("depth", 0),
                "parent_urn": node.get("parent_urn"),
                "section_urn": (section or {}).get("urn") or "",
                "section_ref_id": (section or {}).get("ref_id") or "",
                "section_name": (section or {}).get("name") or "",
                "full_sentence": _build_full_sentence(node, all_nodes),
            }
        )

    # Build a section index too: ordered list of (section_urn, ref_id, name).
    seen: set[str] = set()
    sections: list[dict] = []
    for it in items:
        s_urn = it["section_urn"]
        if s_urn and s_urn not in seen:
            seen.add(s_urn)
            sections.append(
                {
                    "urn": s_urn,
                    "ref_id": it["section_ref_id"],
                    "name": it["section_name"],
                }
            )

    return {
        "source_path": str(yaml_path),
        "library_urn": library_urn,
        "library_ref_id": library_ref_id,
        "framework_urn": framework_urn,
        "framework_ref_id": framework_ref_id,
        "framework_name": framework_name,
        "n_assessable": len(items),
        "n_sections": len(sections),
        "sections": sections,
        "items": items,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Parse a CISO Assistant framework YAML.")
    p.add_argument("yaml_path", help="Path to framework YAML")
    p.add_argument(
        "--items-only",
        action="store_true",
        help="Output only the items list (not metadata)",
    )
    args = p.parse_args()

    parsed = parse(Path(args.yaml_path))
    if args.items_only:
        json.dump(parsed["items"], sys.stdout, ensure_ascii=False, indent=2)
    else:
        json.dump(parsed, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
