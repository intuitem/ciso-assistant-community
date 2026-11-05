"""Framework knowledge for assistants: requirement lookup and cross-framework mappings.

Shared by the REST API (MCP clients) and the embedded chat so both answer the same way.
Content comes from the shipped library graph (chat.knowledge_graph), loaded or not.
Access: the permission type gates library content; loaded frameworks are also
filtered per object; unloaded ones need view_storedlibrary.
"""

import re
import uuid

from django.core.exceptions import PermissionDenied

from chat.knowledge_graph import get_graph
from core.models import Framework, RequirementNode
from iam.models import RoleAssignment


def _tokens(s):
    # "rev5" -> {"rev", "5"}: letters and digits are separate tokens
    return set(re.findall(r"[a-z]+|[0-9]+", (s or "").lower()))


def framework_matches(query, *texts):
    """Every query token prefixes a token of the texts: "NIST SP 800-53 rev 5" matches "NIST SP 800-53 revision 5"."""
    have = set().union(*(_tokens(t) for t in texts))
    return all(any(h.startswith(q) for h in have) for q in _tokens(query))


class _Access:
    def __init__(self, user, codename):
        if not RoleAssignment.has_permission_anywhere(user, codename):
            raise PermissionDenied
        self.unloaded = RoleAssignment.has_permission_anywhere(
            user, "view_storedlibrary"
        )
        viewable = set(RoleAssignment.get_viewable_object_ids(user, Framework))
        self.loaded_all = {
            urn.lower(): fid for urn, fid in Framework.objects.values_list("urn", "id")
        }
        self.loaded = {u: i for u, i in self.loaded_all.items() if i in viewable}

    def framework_ok(self, urn):
        urn = (urn or "").lower()
        return urn in self.loaded or (urn not in self.loaded_all and self.unloaded)


def _frameworks(G, access):
    # shortcut: only shipped libraries are in the graph; add uploaded ones if users ask about them
    return [
        u
        for u, a in G.nodes(data=True)
        if a.get("node_type") == "framework" and access.framework_ok(u)
    ]


def _pick(G, frameworks, query):
    """Frameworks matching `query`; one named with exactly its words beats longer names
    ("NIST CSF 2.0" is not "NIST CSF 2.0 journey")."""
    matches = [
        u
        for u in frameworks
        if framework_matches(query, G[u].get("name"), G[u].get("ref_id"))
    ]
    exact = [
        u
        for u in matches
        if _tokens(query) in (_tokens(G[u].get("name")), _tokens(G[u].get("ref_id")))
    ]
    return exact or matches


def _prefer_loaded(G, access, urns):
    loaded = [u for u in urns if G[u]["framework_urn"].lower() in access.loaded]
    return loaded or urns


def _requirements_of(G, fw_urn):
    for _, urn, d in G.out_edges(fw_urn, data=True):
        if d.get("edge_type") == "has_requirement":
            yield urn


def _search(G, frameworks, ref_id=None, search=None):
    ref = (ref_id or "").strip().lower()
    terms = (search or "").lower().split()
    hits = []
    for fw in frameworks:
        for urn in _requirements_of(G, fw):
            a = G[urn]
            if ref and (a.get("ref_id") or "").lower() != ref:
                continue
            text = f"{a.get('ref_id')} {a.get('name')} {a.get('description')}".lower()
            if all(t in text for t in terms):
                hits.append(urn)
    return hits


def _rows(G, access, urns, extra=None):
    ids = dict(
        (u.lower(), i)
        for u, i in RequirementNode.objects.filter(
            urn__in=[u.lower() for u in urns],
            framework_id__in=access.loaded.values(),
        ).values_list("urn", "id")
    )
    rows = []
    for urn in urns:
        a = G[urn]
        fw = G.get(a.get("framework_urn"), {})
        rows.append(
            {
                "urn": urn,
                "id": ids.get(urn.lower()),
                "loaded": a.get("framework_urn", "").lower() in access.loaded,
                "ref_id": a.get("ref_id"),
                "name": a.get("name"),
                "description": a.get("description"),
                "assessable": a.get("assessable"),
                "framework_urn": a.get("framework_urn"),
                "framework": fw.get("name"),
                "framework_ref_id": fw.get("ref_id"),
                **((extra or {}).get(urn) or {}),
            }
        )
    return rows


def find_requirements(user, framework=None, ref_id=None, search=None, limit=50):
    """Requirements by framework (loosely matched) and exact ref_id and/or search words.

    When nothing matches, reference-like terms are retried as ref_ids in every
    framework: models often look a ref_id up in the other framework of a mapping
    question, or pass a whole phrase as search.
    """
    access = _Access(user, "view_requirementnode")
    G = get_graph()
    frameworks = _frameworks(G, access)
    wanted = frameworks
    if framework:
        wanted = _pick(G, frameworks, framework)
        if not wanted:
            return {
                "requirements": [],
                "unknown_framework": framework,
                "frameworks": sorted(
                    str(G[u].get("ref_id") or G[u].get("name")) for u in frameworks
                ),
            }
    hits = _search(G, wanted, ref_id, search) if (ref_id or search) else []
    note = None
    if not hits and (ref_id or search):
        terms = (
            [ref_id] if ref_id else [t for t in search.split() if re.search(r"\d", t)]
        )
        for term in terms:
            hits = _search(G, frameworks, ref_id=term)
            # the user's loaded frameworks first: they are the likelier target
            hits.sort(key=lambda u: G[u]["framework_urn"].lower() not in access.loaded)
            if hits:
                note = f"Nothing matches {framework or 'the query'} as given; '{term}' is a requirement of the framework(s) below."
                break
    return {
        "requirements": _rows(G, access, hits[:limit]),
        "total": len(hits),
        "note": note,
    }


def requirement_mappings(
    user, requirement=None, framework=None, source_framework=None, ref_id=None
):
    """Requirements of other frameworks that one requirement maps to.

    The requirement is its urn or loaded id, or `ref_id` (with `source_framework`,
    loosely matched): small models do better without copying identifiers around.
    With `framework`, only that framework's; if none are there, `elsewhere` gives
    the per-framework counts so the caller can retry or answer "none".
    Returns None when the requirement is unknown or not visible, and
    {"ambiguous": rows} when the ref_id exists in several frameworks.
    """
    access = _Access(user, "view_requirementmappingset")
    G = get_graph()
    frameworks = _frameworks(G, access)
    urn, note = requirement, None
    if ref_id:
        sources = _pick(G, frameworks, source_framework) if source_framework else []
        hits = _search(G, sources or frameworks, ref_id=ref_id)
        if not hits and framework:
            # models swap the two frameworks of "which X requirements map to Y ref?"
            hits = _search(G, _pick(G, frameworks, framework), ref_id=ref_id)
            if hits:
                note = f"'{ref_id}' is not in '{source_framework}' but in '{framework}': mappings are from '{framework}' to '{source_framework}'."
                framework = source_framework
        if not hits:
            hits = _search(G, frameworks, ref_id=ref_id)
            if hits:
                note = f"'{ref_id}' is not in '{source_framework}'; using the framework(s) that have it."
        hits = _prefer_loaded(G, access, hits)
        if len(hits) > 1:
            return {"ambiguous": _rows(G, access, hits[:20])}
        urn = hits[0] if hits else None
    elif requirement and requirement not in G:
        try:
            requirement_id = uuid.UUID(requirement)
        except ValueError:
            requirement_id = None
        urn = (
            RequirementNode.objects.filter(
                id=requirement_id, framework_id__in=access.loaded.values()
            )
            .values_list("urn", flat=True)
            .first()
            if requirement_id
            else None
        )
        urn = next((u for u in (urn, (urn or "").lower()) if u in G), None)
    if not urn or G[urn].get("node_type") != "requirement_node":
        return None
    if not access.framework_ok(G[urn].get("framework_urn")):
        return None
    targets = {}
    for _, t, d in G.out_edges(urn, data=True):
        if (
            d.get("edge_type") == "maps_to"
            and d.get("relationship") != "not_related"
            # add_edge creates bare nodes for targets no shipped framework defines
            and G.get(t, {}).get("node_type") == "requirement_node"
            and access.framework_ok(G[t].get("framework_urn"))
        ):
            targets[t] = {"relationship": d.get("relationship")}
    rows = _rows(G, access, list(targets), extra=targets)
    wanted = {u.lower() for u in _pick(G, frameworks, framework)} if framework else None
    kept = [r for r in rows if wanted is None or r["framework_urn"].lower() in wanted]
    elsewhere = {}
    if rows and not kept:
        for r in rows:
            elsewhere[r["framework"]] = elsewhere.get(r["framework"], 0) + 1
    return {
        "note": note,
        "source": _rows(G, access, [urn])[0],
        "mappings": kept,
        "elsewhere": elsewhere,
    }
