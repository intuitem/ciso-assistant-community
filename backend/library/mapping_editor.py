"""
Mapping-set editing inside a library draft.

Pure functions over library-document dicts (a framework object, a
requirement mapping set object): no Django, no live rows. The view layer
resolves the frameworks (draft content or stored library content) and
persists the draft.

Pairs are keyed by (source_requirement_urn, target_requirement_urn), the
YAML shape is untouched.
"""

import difflib
import re

from library.builder import BuilderError

RELATIONSHIPS = ("equal", "subset", "superset", "intersect", "not_related")
RATIONALES = ("syntactic", "semantic", "functional")
DEFAULT_RELATIONSHIP = "intersect"
PAIR_FIELDS = ("relationship", "strength_of_relationship", "rationale", "annotation")
REVERSED_RELATIONSHIP = {"subset": "superset", "superset": "subset"}
# Text similarity under which a structurally matched pair is flagged for review.
REWORDED_THRESHOLD = 0.6
# Share of a framework's assessable URN tails another must hold to be its clone origin.
CLONE_THRESHOLD = 0.6


def node_base(framework: dict) -> str:
    return str(framework.get("urn", "")).lower().replace(":framework:", ":req_node:", 1)


def urn_tail(node_urn: str, base: str) -> str:
    """What follows the framework's node base: kept verbatim by a clone,
    which rebases URNs by prefix substitution (builder.build_urn_map)."""
    lowered = str(node_urn).lower()
    if base and lowered.startswith(base + ":"):
        return lowered[len(base) + 1 :]
    return lowered.rsplit(":", 1)[-1]


def assessable_nodes(framework: dict) -> list:
    """Assessable requirement nodes, in document order, with a parent label."""
    nodes = [n for n in framework.get("requirement_nodes") or [] if isinstance(n, dict)]
    labels = {
        str(n.get("urn", "")).lower(): " ".join(
            str(v) for v in (n.get("ref_id"), n.get("name")) if v
        )
        for n in nodes
    }
    return [
        {
            "urn": str(n["urn"]).lower(),
            "ref_id": n.get("ref_id") or "",
            "name": n.get("name") or "",
            "description": n.get("description") or "",
            "parent": labels.get(str(n.get("parent_urn") or "").lower(), ""),
        }
        for n in nodes
        if n.get("assessable") and n.get("urn")
    ]


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def text_similarity(a: dict, b: dict) -> float:
    left = _norm(f"{a.get('name', '')} {a.get('description', '')}")
    right = _norm(f"{b.get('name', '')} {b.get('description', '')}")
    if not left and not right:
        return 1.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def is_reworded(a: dict, b: dict) -> bool:
    return text_similarity(a, b) < REWORDED_THRESHOLD


def apply_pair_ops(
    mapping_set: dict, ops: list, source_urns: set, target_urns: set
) -> list:
    """Return the new requirement_mappings after applying ops, all or none.

    add upserts, update requires the pair, remove is idempotent (so undo
    replays cleanly). Raises BuilderError with an error code.
    """
    if not isinstance(ops, list) or not ops:
        raise BuilderError("opsMustBeANonEmptyList")
    pairs = {}
    order = []
    for pair in mapping_set.get("requirement_mappings") or []:
        key = (
            str(pair.get("source_requirement_urn", "")).lower(),
            str(pair.get("target_requirement_urn", "")).lower(),
        )
        if key not in pairs:
            order.append(key)
        pairs[key] = dict(pair)

    for op in ops:
        if not isinstance(op, dict):
            raise BuilderError("opMustBeADict")
        kind = op.get("op")
        key = (str(op.get("source") or "").lower(), str(op.get("target") or "").lower())
        if kind not in ("add", "update", "remove"):
            raise BuilderError("unknownPairOp")
        if kind == "remove":
            if pairs.pop(key, None) is not None:
                order.remove(key)
            continue
        if key[0] not in source_urns or key[1] not in target_urns:
            raise BuilderError("pairNodeNotAssessable")
        if kind == "update" and key not in pairs:
            raise BuilderError("pairNotFound")
        pair = pairs.get(key) or {
            "source_requirement_urn": key[0],
            "target_requirement_urn": key[1],
            "relationship": DEFAULT_RELATIONSHIP,
        }
        for field in PAIR_FIELDS:
            if field not in op:
                continue
            value = op[field]
            if value in (None, ""):
                if field == "relationship":
                    raise BuilderError("invalidRelationship")
                pair.pop(field, None)
                continue
            if field == "relationship" and value not in RELATIONSHIPS:
                raise BuilderError("invalidRelationship")
            if field == "rationale" and value not in RATIONALES:
                raise BuilderError("invalidRationale")
            if field == "strength_of_relationship" and (
                isinstance(value, bool) or not isinstance(value, int)
            ):
                raise BuilderError("invalidStrength")
            if field == "annotation" and not isinstance(value, str):
                raise BuilderError("invalidAnnotation")
            pair[field] = value
        if key not in pairs:
            order.append(key)
        pairs[key] = pair
    return [pairs[key] for key in order]


def suggest_pairs(
    source_nodes: list,
    target_nodes: list,
    mapped_sources: set,
    source_base: str,
    target_base: str,
) -> list:
    """Deterministic, LLM-free `equal` suggestions for unmapped sources.

    Arms in priority order: URN tail (clone signature, immune to rewording),
    ref_id, name. One-to-one: a target claimed by a stronger arm is not
    offered again.
    """
    arms = (
        ("urn", lambda n, base: urn_tail(n["urn"], base)),
        ("ref_id", lambda n, base: _norm(n["ref_id"])),
        ("name", lambda n, base: _norm(n["name"])),
    )
    pending = [n for n in source_nodes if n["urn"] not in mapped_sources]
    claimed = set()
    suggestions = []
    for reason, key_of in arms:
        index = {}
        for node in target_nodes:
            key = key_of(node, target_base)
            if key and node["urn"] not in claimed:
                # Ambiguous keys (two targets) are not obvious: skip them.
                index[key] = None if key in index else node
        remaining = []
        for node in pending:
            target = index.get(key_of(node, source_base) or None)
            if target is None or target["urn"] in claimed:
                remaining.append(node)
                continue
            claimed.add(target["urn"])
            suggestions.append(
                {
                    "source": node["urn"],
                    "target": target["urn"],
                    "relationship": "equal",
                    "reason": reason,
                    "reworded": is_reworded(node, target),
                }
            )
        pending = remaining
    return suggestions


def reverse_mappings(mapping_set: dict) -> list:
    """B→A pairs derived from A→B: sides swapped, subset↔superset."""
    reversed_pairs = []
    for pair in mapping_set.get("requirement_mappings") or []:
        new_pair = dict(pair)
        new_pair["source_requirement_urn"] = pair.get("target_requirement_urn")
        new_pair["target_requirement_urn"] = pair.get("source_requirement_urn")
        relationship = pair.get("relationship")
        new_pair["relationship"] = REVERSED_RELATIONSHIP.get(relationship, relationship)
        reversed_pairs.append(new_pair)
    return reversed_pairs


def clone_score(clone: dict, candidate: dict) -> float:
    """Share of the clone's assessable URN tails found in the candidate."""
    clone_tails = {
        urn_tail(n["urn"], node_base(clone)) for n in assessable_nodes(clone)
    }
    if not clone_tails:
        return 0.0
    candidate_tails = {
        urn_tail(n["urn"], node_base(candidate)) for n in assessable_nodes(candidate)
    }
    return len(clone_tails & candidate_tails) / len(clone_tails)
