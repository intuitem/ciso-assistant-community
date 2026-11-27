"""
Mapping-set editing inside a library draft.

Pure functions over library-document dicts (a framework object, a
requirement mapping set object): no Django, no live rows. The view layer
resolves the frameworks (draft content or stored library content) and
persists the draft.

Pairs are keyed by (source_requirement_urn, target_requirement_urn), the
YAML shape is untouched.
"""

import collections
import difflib
import math
import re
import unicodedata

import numpy

from library.builder import BuilderError

RELATIONSHIPS = ("equal", "subset", "superset", "intersect", "not_related")
RATIONALES = ("syntactic", "semantic", "functional")
DEFAULT_RELATIONSHIP = "intersect"
PAIR_FIELDS = ("relationship", "strength_of_relationship", "rationale", "annotation")
REVERSED_RELATIONSHIP = {"subset": "superset", "superset": "subset"}
# Every BuilderError apply_pair_ops raises: what reaches the client is one of
# these constants, never text taken from the exception.
PAIR_ERROR_CODES = (
    "opsMustBeANonEmptyList",
    "opMustBeADict",
    "unknownPairOp",
    "pairNodeNotAssessable",
    "pairNotFound",
    "invalidRelationship",
    "invalidRationale",
    "invalidStrength",
    "invalidAnnotation",
)


def pair_error_code(error: Exception) -> str:
    text = str(error)
    return next((code for code in PAIR_ERROR_CODES if code == text), "invalidPairOps")


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
        # The loader forces splash nodes non-assessable: never map them.
        if n.get("assessable") and n.get("urn") and n.get("display_mode") != "splash"
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
    entries = []
    pairs = {}
    order = []
    for pair in mapping_set.get("requirement_mappings") or []:
        key = (
            str(pair.get("source_requirement_urn", "")).lower(),
            str(pair.get("target_requirement_urn", "")).lower(),
        )
        entries.append((key, pair))
        if key not in pairs:
            order.append(key)
        pairs[key] = dict(pair)
    touched = set()

    for op in ops:
        if not isinstance(op, dict):
            raise BuilderError("opMustBeADict")
        kind = op.get("op")
        key = (str(op.get("source") or "").lower(), str(op.get("target") or "").lower())
        if kind not in ("add", "update", "remove"):
            raise BuilderError("unknownPairOp")
        touched.add(key)
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
    # A pair the ops addressed collapses to one entry (that resolves its
    # conflict); every other entry is kept as recorded, duplicates included.
    result, emitted = [], set()
    for key, pair in entries:
        if key not in touched:
            result.append(pair)
        elif key in pairs and key not in emitted:
            result.append(pairs[key])
            emitted.add(key)
    known = {key for key, _ in entries}
    result += [pairs[key] for key in order if key not in known and key in pairs]
    return result


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
        # A malformed value (list, dict) is copied as-is; Validate reports it.
        if isinstance(relationship, str):
            relationship = REVERSED_RELATIONSHIP.get(relationship, relationship)
        new_pair["relationship"] = relationship
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


# --- Suggestions from stored mapping sets ------------------------------------


def compose_relationship(first: str, second: str):
    """A→P then P→B as A→B; None when the chain proves nothing (two
    overlaps need not overlap each other)."""
    if first not in RELATIONSHIPS or second not in RELATIONSHIPS:
        return None
    if "not_related" in (first, second):
        return None
    if first == "equal":
        return second
    if second == "equal":
        return first
    if first == second and first in ("subset", "superset"):
        return first
    return None


def oriented_pairs(mapping_sets: list, source_urn: str, target_urn: str) -> list:
    """(source node, target node, relationship) from source_urn to target_urn,
    read from a set in that direction, else from the reverse one turned
    around."""
    source_urn, target_urn = source_urn.lower(), target_urn.lower()
    reverse = None
    for mapping_set in mapping_sets:
        ends = (
            str(mapping_set.get("source_framework_urn", "")).lower(),
            str(mapping_set.get("target_framework_urn", "")).lower(),
        )
        if ends == (source_urn, target_urn):
            return [
                (
                    str(p.get("source_requirement_urn", "")).lower(),
                    str(p.get("target_requirement_urn", "")).lower(),
                    p.get("relationship"),
                )
                for p in mapping_set.get("requirement_mappings") or []
            ]
        if ends == (target_urn, source_urn):
            reverse = mapping_set
    if reverse is None:
        return []
    return [
        (
            str(p.get("source_requirement_urn", "")).lower(),
            str(p.get("target_requirement_urn", "")).lower(),
            p.get("relationship"),
        )
        for p in reverse_mappings(reverse)
    ]


def compose_pairs(first: list, second: list) -> dict:
    """{(a, b): relationship} through the pivot nodes shared by A→P and P→B.
    Pivots that disagree on a pair fall back to intersect."""
    by_pivot: dict = {}
    for pivot, target, relationship in second:
        by_pivot.setdefault(pivot, []).append((target, relationship))
    composed: dict = {}
    for source, pivot, first_rel in first:
        for target, second_rel in by_pivot.get(pivot, ()):
            relationship = compose_relationship(first_rel, second_rel)
            if relationship is None:
                continue
            key = (source, target)
            if composed.get(key, relationship) != relationship:
                relationship = "intersect"
            composed[key] = relationship
    return composed


def clone_translation(clone: dict, original: dict) -> dict:
    """{original node urn: clone node urn} for the tails both share."""
    clone_base, original_base = node_base(clone), node_base(original)
    by_tail = {
        urn_tail(n["urn"], clone_base): n["urn"] for n in assessable_nodes(clone)
    }
    return {
        n["urn"]: by_tail[tail]
        for n in assessable_nodes(original)
        if (tail := urn_tail(n["urn"], original_base)) in by_tail
    }


# --- Wording hints -------------------------------------------------------------

# Cosine floor under which a wording hint is noise. Measured on the shipped
# mapping sets: keeps 98% of right hints; different languages score 0.
HINT_MIN_SCORE = 0.1
HINT_COUNT = 3


def _tokens(text: str) -> list:
    text = unicodedata.normalize("NFKD", str(text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.findall(r"\w\w+", text)


def wording_hints(source_nodes: list, target_nodes: list) -> dict:
    """{source urn: [[target urn, score], ...]}: the closest targets by
    TF-IDF cosine over name + description (sublinear tf, smoothed idf, the
    scikit-learn defaults), best first, at most HINT_COUNT above
    HINT_MIN_SCORE."""
    if not source_nodes or not target_nodes:
        return {}
    docs = [
        collections.Counter(_tokens(f"{n['name']} {n['description']}"))
        for n in source_nodes + target_nodes
    ]
    df = collections.Counter(term for doc in docs for term in doc)
    idf = {t: math.log((1 + len(docs)) / (1 + count)) + 1 for t, count in df.items()}
    sources, targets = docs[: len(source_nodes)], docs[len(source_nodes) :]
    # Only terms on both sides move the dot product; norms use every term.
    shared = sorted(
        {t for doc in sources for t in doc} & {t for doc in targets for t in doc}
    )
    if not shared:
        return {}
    column = {t: i for i, t in enumerate(shared)}

    def matrix(group):
        out = numpy.zeros((len(group), len(shared)), dtype=numpy.float32)
        for row, doc in enumerate(group):
            weights = {t: (1 + math.log(c)) * idf[t] for t, c in doc.items()}
            norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
            for term, weight in weights.items():
                if term in column:
                    out[row, column[term]] = weight / norm
        return out

    similarity = matrix(sources) @ matrix(targets).T
    hints = {}
    for row, node in enumerate(source_nodes):
        scores = similarity[row]
        best = numpy.argsort(-scores)[:HINT_COUNT]
        picked = [
            [target_nodes[i]["urn"], round(float(scores[i]), 3)]
            for i in best
            if scores[i] >= HINT_MIN_SCORE
        ]
        if picked:
            hints[node["urn"]] = picked
    return hints


# --- Consistency checks ----------------------------------------------------------


def mapping_issues(
    mapping_set: dict, source_urns=None, target_urns=None, reverse_set=None
) -> list:
    """Inconsistencies of a mapping set, as {code, source, target, detail}.

    pairConflict: one pair recorded with several relationships (the editor
      keeps the last one on its next edit of that pair).
    pairDuplicate: one pair recorded twice with the same relationship.
    pairNodeMissing: a side is not an assessable item of its framework
      (checked only when the urn sets are given).
    equalFanOut: an item declared equal to several items of the other side.
    reverseConflict: the reverse set links the same items with a
      relationship that is not the mirror of this one.
    """
    issues = []
    seen: dict = {}
    for pair in mapping_set.get("requirement_mappings") or []:
        key = (
            str(pair.get("source_requirement_urn", "")).lower(),
            str(pair.get("target_requirement_urn", "")).lower(),
        )
        seen.setdefault(key, []).append(pair.get("relationship"))
    for (source, target), relationships in seen.items():
        if len(relationships) > 1:
            distinct = sorted(set(map(str, relationships)))
            issues.append(
                {
                    "code": "pairConflict" if len(distinct) > 1 else "pairDuplicate",
                    "source": source,
                    "target": target,
                    "detail": distinct,
                }
            )
        missing = [
            side
            for side, urn, urns in (
                ("source", source, source_urns),
                ("target", target, target_urns),
            )
            if urns is not None and urn not in urns
        ]
        if missing:
            issues.append(
                {
                    "code": "pairNodeMissing",
                    "source": source,
                    "target": target,
                    "detail": missing,
                }
            )
    equal_by: dict = {"source": {}, "target": {}}
    for (source, target), relationships in seen.items():
        if relationships[-1] == "equal":
            equal_by["source"].setdefault(source, []).append(target)
            equal_by["target"].setdefault(target, []).append(source)
    for side, groups in equal_by.items():
        for urn, others in groups.items():
            if len(others) > 1:
                issues.append(
                    {
                        "code": "equalFanOut",
                        "source": urn if side == "source" else None,
                        "target": urn if side == "target" else None,
                        "detail": sorted(others),
                    }
                )
    if reverse_set is not None:
        mirrored = {
            (
                str(p.get("source_requirement_urn", "")).lower(),
                str(p.get("target_requirement_urn", "")).lower(),
            ): p.get("relationship")
            for p in reverse_mappings(reverse_set)
        }
        for key, relationships in seen.items():
            other = mirrored.get(key)
            if other is not None and other != relationships[-1]:
                issues.append(
                    {
                        "code": "reverseConflict",
                        "source": key[0],
                        "target": key[1],
                        "detail": [relationships[-1], other],
                    }
                )
    return issues
