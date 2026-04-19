#!/usr/bin/env python3
"""Emit a CISO Assistant mapping library YAML.

Reads a JSON file describing the mapping (metadata + verdicts) and writes a
.yaml file matching the schema used by backend/library/libraries/mapping-*.yaml.

The emitted library contains TWO requirement_mapping_sets:
  - forward (source → target) using the verdicts as-is
  - reverse (target → source) auto-derived: relationships flip
    (subset ↔ superset; equal/intersect/not_related stay the same)

Input JSON shape (keys with TODO must be filled by the caller):
{
  "ref_id": "mapping-foo-and-bar",
  "name": "Foo <-> Bar",
  "description": "Mapping between Foo and Bar",
  "version": 1,
  "publication_date": "2026-04-19",
  "copyright": "...",
  "provider": "...",
  "packager": "...",
  "source_library_urn": "urn:intuitem:risk:library:foo",
  "source_framework_urn": "urn:intuitem:risk:framework:foo",
  "target_library_urn": "urn:intuitem:risk:library:bar",
  "target_framework_urn": "urn:intuitem:risk:framework:bar",
  "verdicts": [
    {
      "source_requirement_urn": "...",
      "target_requirement_urn": "...",
      "relationship": "equal|intersect|subset|superset",
      "strength_of_relationship": 8           # optional, 0-10
    },
    ...
  ]
}

Stdlib + pyyaml only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml


VALID_RELATIONSHIPS = {"equal", "intersect", "subset", "superset"}


REVERSE_RELATIONSHIP = {
    "equal": "equal",
    "intersect": "intersect",
    "subset": "superset",
    "superset": "subset",
}


def _validate(spec: dict) -> None:
    required = [
        "ref_id",
        "name",
        "source_library_urn",
        "source_framework_urn",
        "target_library_urn",
        "target_framework_urn",
        "verdicts",
    ]
    missing = [k for k in required if not spec.get(k)]
    if missing:
        raise SystemExit(f"missing required fields: {missing}")
    for i, v in enumerate(spec["verdicts"]):
        for k in ("source_requirement_urn", "target_requirement_urn", "relationship"):
            if not v.get(k):
                raise SystemExit(f"verdict[{i}] missing {k}")
        rel = v["relationship"]
        if rel not in VALID_RELATIONSHIPS:
            raise SystemExit(
                f"verdict[{i}] has invalid relationship {rel!r} "
                f"(must be one of {sorted(VALID_RELATIONSHIPS)})"
            )
        s = v.get("strength_of_relationship")
        if s is not None:
            try:
                s_int = int(s)
            except (TypeError, ValueError):
                raise SystemExit(
                    f"verdict[{i}] strength_of_relationship must be an int 0-10, got {s!r}"
                )
            if not 0 <= s_int <= 10:
                raise SystemExit(
                    f"verdict[{i}] strength_of_relationship {s_int} out of range 0-10"
                )


def _build_mapping_set(
    set_urn_prefix: str,
    ref_id: str,
    name: str,
    description: str,
    source_framework_urn: str,
    target_framework_urn: str,
    verdicts: list[dict],
    *,
    reverse: bool = False,
) -> dict:
    mappings: list[dict] = []
    for v in verdicts:
        if reverse:
            src = v["target_requirement_urn"]
            tgt = v["source_requirement_urn"]
            rel = REVERSE_RELATIONSHIP[v["relationship"]]
        else:
            src = v["source_requirement_urn"]
            tgt = v["target_requirement_urn"]
            rel = v["relationship"]

        m = {
            "source_requirement_urn": src,
            "target_requirement_urn": tgt,
            "relationship": rel,
        }
        # strength_of_relationship is optional in the schema but useful when present.
        if (
            "strength_of_relationship" in v
            and v["strength_of_relationship"] is not None
        ):
            try:
                m["strength_of_relationship"] = int(v["strength_of_relationship"])
            except (TypeError, ValueError):
                pass
        if v.get("rationale"):
            m["rationale"] = v["rationale"]
        mappings.append(m)

    return {
        "urn": f"{set_urn_prefix}:{ref_id}",
        "ref_id": ref_id,
        "name": name,
        "description": description,
        "source_framework_urn": source_framework_urn,
        "target_framework_urn": target_framework_urn,
        "requirement_mappings": mappings,
    }


def build_library(spec: dict) -> dict:
    _validate(spec)
    ref_id = spec["ref_id"]
    name = spec["name"]
    description = spec.get("description", name)
    version = int(spec.get("version", 1))
    pub_date = spec.get("publication_date") or date.today().isoformat()

    library_urn = f"urn:intuitem:risk:library:{ref_id}"
    set_urn_prefix = "urn:intuitem:risk:req_mapping_set"

    forward = _build_mapping_set(
        set_urn_prefix,
        ref_id,
        name,
        description,
        spec["source_framework_urn"],
        spec["target_framework_urn"],
        spec["verdicts"],
        reverse=False,
    )
    # Reverse set requires a distinct urn/ref_id because RequirementMappingSet
    # enforces unique=True on urn. Published mappings use the `-revert` suffix.
    reverse_ref_id = f"{ref_id}-revert"
    reverse = _build_mapping_set(
        set_urn_prefix,
        reverse_ref_id,
        name,
        description,
        spec["target_framework_urn"],
        spec["source_framework_urn"],
        spec["verdicts"],
        reverse=True,
    )

    library = {
        "urn": library_urn,
        "locale": spec.get("locale", "en"),
        "ref_id": ref_id,
        "name": name,
        "description": description,
        "copyright": spec.get("copyright", ""),
        "version": version,
        "publication_date": pub_date,
        "provider": spec.get("provider", ""),
        "packager": spec.get("packager", ""),
        "dependencies": [
            spec["source_library_urn"],
            spec["target_library_urn"],
        ],
        "objects": {"requirement_mapping_sets": [forward, reverse]},
    }
    return library


# --- YAML emission ---------------------------------------------------------


class _LiteralStr(str):
    """Marker for strings that should be emitted as YAML block literals."""


def _literal_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_LiteralStr, _literal_representer, Dumper=yaml.SafeDumper)


def _maybe_block(s: str) -> str | _LiteralStr:
    # Use block-literal style for multi-line strings to keep the YAML readable.
    if isinstance(s, str) and ("\n" in s or len(s) > 120):
        return _LiteralStr(s)
    return s


def _prep_for_yaml(obj):
    if isinstance(obj, dict):
        return {k: _prep_for_yaml(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_prep_for_yaml(v) for v in obj]
    if isinstance(obj, str):
        return _maybe_block(obj)
    return obj


def write_yaml(library: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            _prep_for_yaml(library),
            f,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=120,
        )


def main() -> int:
    p = argparse.ArgumentParser(
        description="Write a CISO Assistant mapping library YAML."
    )
    p.add_argument(
        "spec_json", help="Path to the JSON spec file (see module docstring)"
    )
    p.add_argument("output_yaml", help="Path to write the library YAML to")
    args = p.parse_args()

    with open(args.spec_json, "r", encoding="utf-8") as f:
        spec = json.load(f)
    library = build_library(spec)
    write_yaml(library, Path(args.output_yaml))

    n_mappings = len(
        library["objects"]["requirement_mapping_sets"][0]["requirement_mappings"]
    )
    print(
        f"wrote {args.output_yaml}: {n_mappings} forward mappings + "
        f"{n_mappings} reverse mappings"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
