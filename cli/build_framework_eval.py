"""Build a framework-knowledge eval set from the embedded library YAMLs.

Every expected answer comes straight from backend/library/libraries, so the set
is exact and regenerates when libraries change. Three question kinds:
  lookup   "What is A.5.1 in ISO/IEC 27001:2022?"      -> name/description + urn
  reverse  "Which requirement of X is titled '...'?"   -> ref_id + urn
  mapping  "Which Y requirements map to X GV.OC-01?"   -> set of target ref_ids

  ../.venv/bin/python cli/build_framework_eval.py --out cli/evals/framework_questions.jsonl
"""

import argparse
import json
import random
from pathlib import Path

import yaml

LIBRARIES = Path(__file__).resolve().parent.parent / "backend/library/libraries"


def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def frameworks(lib):
    objs = lib.get("objects") or {}
    fw = objs.get("framework")
    # a library holds one framework dict, presets/combined libs may hold a list
    return [fw] if isinstance(fw, dict) else (fw or [])


def mapping_sets(lib):
    objs = lib.get("objects") or {}
    ms = objs.get("requirement_mapping_set") or objs.get("requirement_mapping_sets")
    return [ms] if isinstance(ms, dict) else (ms or [])


def answerable(nodes):
    """Assessable nodes whose ref_id is unique in the framework, so a question has one answer."""
    counts = {}
    for n in nodes:
        if n.get("ref_id"):
            counts[n["ref_id"]] = counts.get(n["ref_id"], 0) + 1
    return [
        n
        for n in nodes
        if n.get("assessable")
        and n.get("ref_id")
        and counts[n["ref_id"]] == 1
        and (n.get("name") or n.get("description"))
    ]


def build(lookup_k, reverse_k, mapping_k, seed):
    rng = random.Random(seed)
    libs = [(p, load(p)) for p in sorted(LIBRARIES.glob("*.yaml"))]
    node_by_urn, fw_label = {}, {}
    questions = []

    for path, lib in libs:
        for fw in frameworks(lib):
            label = fw.get("ref_id") or fw.get("name") or lib.get("ref_id")
            fw_label[fw["urn"]] = label
            nodes = fw.get("requirement_nodes") or []
            for n in nodes:
                node_by_urn[n["urn"]] = n
            pool = answerable(nodes)
            for n in rng.sample(pool, min(lookup_k, len(pool))):
                questions.append(
                    {
                        "kind": "lookup",
                        "framework_urn": fw["urn"],
                        "question": f"What is requirement {n['ref_id']} in {label}?",
                        "expected": {
                            "urn": n["urn"],
                            "ref_id": n["ref_id"],
                            "name": n.get("name"),
                            "description": n.get("description"),
                        },
                        "source": path.name,
                    }
                )
            # reverse needs a name that identifies exactly one node
            names = {}
            for n in pool:
                if n.get("name"):
                    names.setdefault(n["name"].strip().lower(), []).append(n)
            named = [ns[0] for ns in names.values() if len(ns) == 1]
            for n in rng.sample(named, min(reverse_k, len(named))):
                questions.append(
                    {
                        "kind": "reverse",
                        "framework_urn": fw["urn"],
                        "question": f"Which requirement of {label} is titled '{n['name']}'? Give its reference.",
                        "expected": {"urn": n["urn"], "ref_id": n["ref_id"]},
                        "source": path.name,
                    }
                )

    for path, lib in libs:
        for ms in mapping_sets(lib):
            src, tgt = ms.get("source_framework_urn"), ms.get("target_framework_urn")
            if src not in fw_label or tgt not in fw_label:
                continue
            targets = {}
            for m in ms.get("requirement_mappings") or []:
                if m.get("relationship") == "not_related":
                    continue
                targets.setdefault(m["source_requirement_urn"], set()).add(
                    m["target_requirement_urn"]
                )
            sources = sorted(u for u in targets if node_by_urn.get(u, {}).get("ref_id"))
            for s in rng.sample(sources, min(mapping_k, len(sources))):
                expected = sorted(
                    t for t in targets[s] if node_by_urn.get(t, {}).get("ref_id")
                )
                if not expected:
                    continue
                questions.append(
                    {
                        "kind": "mapping",
                        "framework_urn": src,
                        "question": f"Which {fw_label[tgt]} requirements map to {fw_label[src]} {node_by_urn[s]['ref_id']}?",
                        "expected": {
                            "urns": expected,
                            "ref_ids": [node_by_urn[t]["ref_id"] for t in expected],
                        },
                        "source": path.name,
                    }
                )
    return questions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="cli/evals/framework_questions.jsonl")
    ap.add_argument(
        "--lookup", type=int, default=3, help="lookup questions per framework"
    )
    ap.add_argument(
        "--reverse", type=int, default=1, help="reverse questions per framework"
    )
    ap.add_argument("--mapping", type=int, default=2, help="questions per mapping set")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    qs = build(args.lookup, args.reverse, args.mapping, args.seed)
    for q in qs:
        assert q["question"] and q["expected"], q
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for i, q in enumerate(qs):
            f.write(
                json.dumps({"id": f"{q['kind']}-{i:04d}", **q}, ensure_ascii=False)
                + "\n"
            )
    kinds = {}
    for q in qs:
        kinds[q["kind"]] = kinds.get(q["kind"], 0) + 1
    print(f"{len(qs)} questions -> {out}  {kinds}")


if __name__ == "__main__":
    main()
