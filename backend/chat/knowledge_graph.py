"""
Knowledge graph built from YAML framework libraries.

Provides structural navigation for framework comparison, requirement
hierarchy traversal, cross-framework mappings, and threat-control tracing.

The graph is built lazily on first use from the same YAML files used by
the library system. It lives in-process memory (60k+ nodes fits easily)
and is rebuilt on demand.

Uses a lightweight DiGraph implementation — no external dependency needed.

Node types: framework, requirement_node, threat, reference_control
Edge types: has_requirement, parent_child, addresses_threat,
            implemented_by, has_mapping, maps_to
"""

import structlog
import threading
import time
from pathlib import Path
from typing import Any, Iterator

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lightweight directed graph (replaces NetworkX)
# ---------------------------------------------------------------------------


class DiGraph:
    """Minimal directed graph with node/edge attributes."""

    __slots__ = ("_nodes", "_out", "_in")

    def __init__(self):
        self._nodes: dict[str, dict[str, Any]] = {}
        self._out: dict[str, dict[str, dict[str, Any]]] = {}  # src → {dst → attrs}
        self._in: dict[str, dict[str, dict[str, Any]]] = {}  # dst → {src → attrs}

    def add_node(self, node_id: str, **attrs):
        if node_id in self._nodes:
            self._nodes[node_id].update(attrs)
        else:
            self._nodes[node_id] = attrs
            self._out.setdefault(node_id, {})
            self._in.setdefault(node_id, {})

    def add_edge(self, src: str, dst: str, **attrs):
        # Auto-create nodes if missing
        if src not in self._nodes:
            self._nodes[src] = {}
            self._out.setdefault(src, {})
            self._in.setdefault(src, {})
        if dst not in self._nodes:
            self._nodes[dst] = {}
            self._out.setdefault(dst, {})
            self._in.setdefault(dst, {})
        self._out[src][dst] = attrs
        self._in[dst][src] = attrs

    def nodes(self, data: bool = False) -> Iterator:
        if data:
            return iter(self._nodes.items())
        return iter(self._nodes)

    def out_edges(self, node_id: str, data: bool = False) -> Iterator[tuple]:
        targets = self._out.get(node_id, {})
        if data:
            return ((node_id, dst, attrs) for dst, attrs in targets.items())
        return ((node_id, dst) for dst in targets)

    def in_edges(self, node_id: str, data: bool = False) -> Iterator[tuple]:
        sources = self._in.get(node_id, {})
        if data:
            return ((src, node_id, attrs) for src, attrs in sources.items())
        return ((src, node_id) for src in sources)

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return sum(len(targets) for targets in self._out.values())

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def __getitem__(self, node_id: str) -> dict[str, Any]:
        return self._nodes[node_id]

    def get(self, node_id: str, default=None):
        return self._nodes.get(node_id, default)


# ---------------------------------------------------------------------------
# Singleton graph management
# ---------------------------------------------------------------------------

_graph: DiGraph | None = None
_graph_lock = threading.Lock()

_CACHE_DIR = Path(__file__).resolve().parent.parent / "db" / "cache"
_CACHE_FILE = _CACHE_DIR / "knowledge_graph.pkl"


def get_graph() -> DiGraph:
    """Get or build the singleton knowledge graph, using disk cache when available."""
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                _graph = _load_or_build()
    return _graph


def rebuild_graph() -> DiGraph:
    """Force rebuild of the knowledge graph (invalidates cache)."""
    global _graph
    with _graph_lock:
        _graph = _build_graph()
        _save_cache(_graph)
    return _graph


def _get_library_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "library" / "libraries"


def _get_library_mtime() -> float:
    """Get the most recent modification time across all YAML library files."""
    lib_dir = _get_library_dir()
    if not lib_dir.exists():
        return 0.0
    mtime = lib_dir.stat().st_mtime
    for f in lib_dir.glob("*.yaml"):
        mtime = max(mtime, f.stat().st_mtime)
    return mtime


def _load_or_build() -> DiGraph:
    """Try loading from disk cache; rebuild from YAML if stale or missing."""
    import pickle

    try:
        if _CACHE_FILE.exists():
            cache_mtime = _CACHE_FILE.stat().st_mtime
            lib_mtime = _get_library_mtime()
            if cache_mtime >= lib_mtime:
                t0 = time.time()
                with open(_CACHE_FILE, "rb") as f:
                    graph = pickle.load(f)
                logger.info(
                    "knowledge_graph_loaded_from_cache",
                    duration=round(time.time() - t0, 2),
                    nodes=graph.number_of_nodes(),
                )
                return graph
            else:
                logger.info("knowledge_graph_cache_stale")
    except Exception as e:
        logger.warning("knowledge_graph_cache_load_failed", error=str(e))

    graph = _build_graph()
    _save_cache(graph)
    return graph


def _save_cache(graph: DiGraph) -> None:
    """Persist the graph to disk for fast loading."""
    import pickle

    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("knowledge_graph_cache_saved", path=str(_CACHE_FILE))
    except Exception as e:
        logger.warning("knowledge_graph_cache_save_failed", error=str(e))


def _build_graph() -> DiGraph:
    """Parse all YAML library files and build the knowledge graph."""
    import time
    import yaml

    t0 = time.time()
    G = DiGraph()
    library_dir = _get_library_dir()

    if not library_dir.exists():
        logger.warning("library_dir_not_found", path=str(library_dir))
        return G

    yaml_files = sorted(library_dir.glob("*.yaml"))
    logger.info("knowledge_graph_build_started", file_count=len(yaml_files))

    for filepath in yaml_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.warning("yaml_parse_failed", file=filepath.name, error=str(e))
            continue

        if not isinstance(data, dict):
            continue

        _process_library(G, data)

    logger.info(
        "knowledge_graph_build_complete",
        nodes=G.number_of_nodes(),
        edges=G.number_of_edges(),
        duration=round(time.time() - t0, 2),
    )
    return G


def _process_library(G: DiGraph, data: dict):
    """Process a single YAML library file into graph nodes and edges."""
    library_urn = data.get("urn", "")
    library_name = data.get("name", "")
    library_ref_id = data.get("ref_id", "")
    locale = data.get("locale", "en")
    provider = data.get("provider", "")
    description = data.get("description", "")

    objects = data.get("objects", {})

    # --- Framework and its requirement nodes ---
    framework = objects.get("framework", {})
    if isinstance(framework, dict) and framework:
        fw_urn = framework.get("urn", library_urn)
        fw_name = framework.get("name", library_name)
        fw_ref_id = framework.get("ref_id", library_ref_id)
        fw_description = framework.get("description", description)

        G.add_node(
            fw_urn,
            node_type="framework",
            name=fw_name,
            ref_id=fw_ref_id,
            description=fw_description,
            provider=provider,
            locale=locale,
            library_urn=library_urn,
        )

        for node in framework.get("requirement_nodes", []):
            node_urn = node.get("urn", "")
            if not node_urn:
                continue

            G.add_node(
                node_urn,
                node_type="requirement_node",
                name=node.get("name", ""),
                ref_id=node.get("ref_id", ""),
                description=node.get("description", ""),
                annotation=node.get("annotation", ""),
                assessable=node.get("assessable", False),
                depth=node.get("depth", 1),
                implementation_groups=node.get("implementation_groups", []),
                framework_urn=fw_urn,
                framework_name=fw_name,
            )

            G.add_edge(fw_urn, node_urn, edge_type="has_requirement")

            parent_urn = node.get("parent_urn")
            if parent_urn:
                G.add_edge(parent_urn, node_urn, edge_type="parent_child")

            for threat_urn in node.get("threats", []):
                G.add_edge(node_urn, threat_urn, edge_type="addresses_threat")

            for ctrl_urn in node.get("reference_controls", []):
                G.add_edge(node_urn, ctrl_urn, edge_type="implemented_by")

    # --- Threats ---
    for threat in objects.get("threats", []):
        threat_urn = threat.get("urn", "")
        if not threat_urn:
            continue
        G.add_node(
            threat_urn,
            node_type="threat",
            name=threat.get("name", ""),
            ref_id=threat.get("ref_id", ""),
            description=threat.get("description", ""),
            provider=provider,
            locale=locale,
        )

    # --- Reference controls ---
    for ctrl in objects.get("reference_controls", []):
        ctrl_urn = ctrl.get("urn", "")
        if not ctrl_urn:
            continue
        G.add_node(
            ctrl_urn,
            node_type="reference_control",
            name=ctrl.get("name", ""),
            ref_id=ctrl.get("ref_id", ""),
            description=ctrl.get("description", ""),
            category=ctrl.get("category", ""),
            csf_function=ctrl.get("csf_function", ""),
            provider=provider,
            locale=locale,
        )

    # --- Cross-framework mappings ---
    mapping_set = objects.get("requirement_mapping_set", {})
    if isinstance(mapping_set, dict) and mapping_set:
        source_fw = mapping_set.get("source_framework_urn", "")
        target_fw = mapping_set.get("target_framework_urn", "")

        if source_fw and target_fw:
            G.add_edge(
                source_fw,
                target_fw,
                edge_type="has_mapping",
                mapping_urn=mapping_set.get("urn", ""),
            )

            for mapping in mapping_set.get("requirement_mappings", []):
                source_req = mapping.get("source_requirement_urn", "")
                target_req = mapping.get("target_requirement_urn", "")
                if source_req and target_req:
                    G.add_edge(
                        source_req,
                        target_req,
                        edge_type="maps_to",
                        relationship=mapping.get("relationship", ""),
                        rationale=mapping.get("rationale", ""),
                        annotation=mapping.get("annotation", ""),
                    )


# ---------------------------------------------------------------------------
# Query functions — called by tool dispatch
# ---------------------------------------------------------------------------


def find_frameworks(
    query: str = "", provider: str = "", locale: str = ""
) -> list[dict]:
    """Search frameworks by name, provider, or locale."""
    G = get_graph()
    results = []
    query_lower = query.lower()

    for node_id, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "framework":
            continue
        if provider and attrs.get("provider", "").lower() != provider.lower():
            continue
        if locale and attrs.get("locale", "") != locale:
            continue
        if query_lower:
            searchable = (
                f"{attrs.get('name', '')} {attrs.get('ref_id', '')} "
                f"{attrs.get('description', '')} {attrs.get('provider', '')}"
            ).lower()
            if query_lower not in searchable:
                continue

        req_count = sum(
            1
            for _, _, d in G.out_edges(node_id, data=True)
            if d.get("edge_type") == "has_requirement"
        )

        results.append(
            {
                "urn": node_id,
                "name": attrs.get("name", ""),
                "ref_id": attrs.get("ref_id", ""),
                "description": (attrs.get("description", "") or "")[:200],
                "provider": attrs.get("provider", ""),
                "locale": attrs.get("locale", ""),
                "requirement_count": req_count,
            }
        )

    return sorted(results, key=lambda x: x["name"])


def get_framework_detail(identifier: str) -> dict | None:
    """Get detailed info about a framework by URN, ref_id, or name."""
    G = get_graph()
    fw_urn = _resolve_framework(G, identifier)
    if not fw_urn:
        return None

    attrs = G[fw_urn]

    # Collect requirement nodes
    req_nodes = [
        (target, G[target])
        for _, target, d in G.out_edges(fw_urn, data=True)
        if d.get("edge_type") == "has_requirement"
    ]

    # Top-level sections
    sections = []
    total_assessable = 0
    for node_id, node_attrs in req_nodes:
        if node_attrs.get("assessable"):
            total_assessable += 1
        if node_attrs.get("depth", 1) == 1:
            child_count = sum(
                1
                for _, _, d in G.out_edges(node_id, data=True)
                if d.get("edge_type") == "parent_child"
            )
            sections.append(
                {
                    "ref_id": node_attrs.get("ref_id", ""),
                    "name": node_attrs.get("name", ""),
                    "child_count": child_count,
                }
            )

    # Mappings to/from other frameworks
    mappings_to = []
    mappings_from = []
    for _, target, d in G.out_edges(fw_urn, data=True):
        if d.get("edge_type") == "has_mapping" and target in G:
            target_attrs = G[target]
            if target_attrs.get("node_type") == "framework":
                mappings_to.append(
                    {"urn": target, "name": target_attrs.get("name", target)}
                )
    for source, _, d in G.in_edges(fw_urn, data=True):
        if d.get("edge_type") == "has_mapping" and source in G:
            source_attrs = G[source]
            if source_attrs.get("node_type") == "framework":
                mappings_from.append(
                    {"urn": source, "name": source_attrs.get("name", source)}
                )

    # Cap sections to avoid overwhelming the LLM
    sections_summary = sections[:15]
    if len(sections) > 15:
        sections_summary.append({"note": f"... and {len(sections) - 15} more sections"})

    return {
        "urn": fw_urn,
        "name": attrs.get("name", ""),
        "ref_id": attrs.get("ref_id", ""),
        "description": attrs.get("description", ""),
        "provider": attrs.get("provider", ""),
        "locale": attrs.get("locale", ""),
        "total_requirements": len(req_nodes),
        "assessable_requirements": total_assessable,
        "sections": sections_summary,
        "mappings_to": mappings_to,
        "mappings_from": mappings_from,
    }


def compare_frameworks(identifier_a: str, identifier_b: str) -> dict:
    """Compare two frameworks side by side."""
    G = get_graph()
    detail_a = get_framework_detail(identifier_a)
    detail_b = get_framework_detail(identifier_b)

    result: dict = {"framework_a": detail_a, "framework_b": detail_b}

    if detail_a and detail_b:
        # Count requirement-level mappings between them
        a_reqs = {
            target
            for _, target, d in G.out_edges(detail_a["urn"], data=True)
            if d.get("edge_type") == "has_requirement"
        }
        b_reqs = {
            target
            for _, target, d in G.out_edges(detail_b["urn"], data=True)
            if d.get("edge_type") == "has_requirement"
        }

        mapping_count = 0
        sample_mappings = []
        # A→B mappings
        for req_urn in a_reqs:
            for _, target, d in G.out_edges(req_urn, data=True):
                if d.get("edge_type") == "maps_to" and target in b_reqs:
                    mapping_count += 1
                    if len(sample_mappings) < 5:
                        src = G.get(req_urn, {})
                        tgt = G.get(target, {})
                        sample_mappings.append(
                            {
                                "source": f"{src.get('ref_id', '')} {src.get('name', '')}".strip(),
                                "target": f"{tgt.get('ref_id', '')} {tgt.get('name', '')}".strip(),
                                "relationship": d.get("relationship", ""),
                            }
                        )
        # B→A mappings
        for req_urn in b_reqs:
            for _, target, d in G.out_edges(req_urn, data=True):
                if d.get("edge_type") == "maps_to" and target in a_reqs:
                    mapping_count += 1

        result["mapping_count"] = mapping_count
        result["has_mapping"] = mapping_count > 0
        result["sample_mappings"] = sample_mappings

    return result


def search_requirements(query: str, framework: str = "", limit: int = 20) -> list[dict]:
    """Search requirement nodes by text, optionally within a specific framework."""
    G = get_graph()
    query_lower = query.lower()
    results = []

    fw_urn = _resolve_framework(G, framework) if framework else None

    for node_id, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "requirement_node":
            continue
        if fw_urn and attrs.get("framework_urn") != fw_urn:
            continue

        searchable = (
            f"{attrs.get('name', '')} {attrs.get('ref_id', '')} "
            f"{attrs.get('description', '')}"
        ).lower()
        if query_lower not in searchable:
            continue

        results.append(
            {
                "urn": node_id,
                "ref_id": attrs.get("ref_id", ""),
                "name": attrs.get("name", ""),
                "description": (attrs.get("description", "") or "")[:200],
                "framework": attrs.get("framework_name", ""),
                "assessable": attrs.get("assessable", False),
                "depth": attrs.get("depth", 1),
            }
        )

        if len(results) >= limit:
            break

    return results


def find_mappings(
    source_framework: str, target_framework: str = "", limit: int = 50
) -> list[dict]:
    """Find cross-framework requirement mappings."""
    G = get_graph()
    source_urn = _resolve_framework(G, source_framework)
    if not source_urn:
        return []

    target_urn = _resolve_framework(G, target_framework) if target_framework else None

    source_reqs = {
        target
        for _, target, d in G.out_edges(source_urn, data=True)
        if d.get("edge_type") == "has_requirement"
    }

    mappings = []
    total = 0
    for req_urn in source_reqs:
        for _, target_id, md in G.out_edges(req_urn, data=True):
            if md.get("edge_type") != "maps_to":
                continue
            target_attrs = G.get(target_id, {})
            if target_urn and target_attrs.get("framework_urn") != target_urn:
                continue

            total += 1
            if len(mappings) < limit:
                source_attrs = G.get(req_urn, {})
                mappings.append(
                    {
                        "source_ref_id": source_attrs.get("ref_id", ""),
                        "source_name": source_attrs.get("name", ""),
                        "target_ref_id": target_attrs.get("ref_id", ""),
                        "target_name": target_attrs.get("name", ""),
                        "target_framework": target_attrs.get("framework_name", ""),
                        "relationship": md.get("relationship", ""),
                        "annotation": md.get("annotation", ""),
                    }
                )

    if total > limit:
        mappings.append({"note": f"Showing {limit} of {total} total mappings"})

    return mappings


def find_controls_for_threat(threat_query: str) -> list[dict]:
    """Given a threat name, find requirements and controls that address it."""
    G = get_graph()
    query_lower = threat_query.lower()

    # Find matching threats
    threat_urns = []
    for node_id, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "threat":
            continue
        searchable = (
            f"{attrs.get('name', '')} {attrs.get('ref_id', '')} "
            f"{attrs.get('description', '')}"
        ).lower()
        if query_lower in searchable:
            threat_urns.append(node_id)

    if not threat_urns:
        return []

    # Find requirements that address these threats (reverse edges)
    results = []
    for threat_urn in threat_urns:
        threat_attrs = G[threat_urn]
        for req_id, _, d in G.in_edges(threat_urn, data=True):
            if d.get("edge_type") != "addresses_threat":
                continue
            req_attrs = G.get(req_id, {})

            # Find controls linked to this requirement
            controls = []
            for _, ctrl_id, cd in G.out_edges(req_id, data=True):
                if cd.get("edge_type") != "implemented_by":
                    continue
                ctrl_attrs = G.get(ctrl_id, {})
                controls.append(
                    {
                        "urn": ctrl_id,
                        "ref_id": ctrl_attrs.get("ref_id", ""),
                        "name": ctrl_attrs.get("name", ""),
                    }
                )

            results.append(
                {
                    "threat": {
                        "urn": threat_urn,
                        "name": threat_attrs.get("name", ""),
                        "ref_id": threat_attrs.get("ref_id", ""),
                    },
                    "requirement": {
                        "urn": req_id,
                        "ref_id": req_attrs.get("ref_id", ""),
                        "name": req_attrs.get("name", ""),
                        "framework": req_attrs.get("framework_name", ""),
                    },
                    "controls": controls,
                }
            )

    return results


def get_graph_stats() -> dict:
    """Return summary statistics about the knowledge graph."""
    G = get_graph()
    type_counts: dict[str, int] = {}
    for _, attrs in G.nodes(data=True):
        nt = attrs.get("node_type", "unknown")
        type_counts[nt] = type_counts.get(nt, 0) + 1

    edge_counts: dict[str, int] = {}
    for node_id in G._out:
        for _, edge_attrs in G._out[node_id].items():
            et = edge_attrs.get("edge_type", "unknown")
            edge_counts[et] = edge_counts.get(et, 0) + 1

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "node_types": type_counts,
        "edge_types": edge_counts,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_framework(G: DiGraph, identifier: str) -> str | None:
    """Resolve a framework identifier (URN, ref_id, or name) to its URN."""
    if not identifier:
        return None

    identifier_lower = identifier.lower().strip()

    # Direct URN match
    if identifier in G and G[identifier].get("node_type") == "framework":
        return identifier

    # Search by ref_id or name
    best_match = None
    best_score = 0.0

    for node_id, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "framework":
            continue

        ref_id = (attrs.get("ref_id", "") or "").lower()
        name = (attrs.get("name", "") or "").lower()

        # Exact ref_id match
        if ref_id == identifier_lower:
            return node_id

        # Exact name match
        if name == identifier_lower:
            return node_id

        # Partial match scoring — take the best of all matches
        score = 0.0
        if identifier_lower in ref_id:
            score = max(score, len(identifier_lower) / max(len(ref_id), 1))
        if identifier_lower in name:
            score = max(score, len(identifier_lower) / max(len(name), 1))
        if ref_id and ref_id in identifier_lower:
            score = max(score, len(ref_id) / max(len(identifier_lower), 1) * 0.8)
        if name and name in identifier_lower:
            score = max(score, len(name) / max(len(identifier_lower), 1) * 0.8)

        if score > best_score:
            best_score = score
            best_match = node_id

    # Require a minimum match quality to avoid false positives.
    # Threshold is low (0.25) because short abbreviations like "3CF"
    # score 0.3 against "3CF-ed1-v1". Callers filter tokens < 3 chars
    # to prevent common words from matching.
    if best_score < 0.25:
        return None
    return best_match


def format_graph_result(result: dict | list | None) -> str:
    """Format a graph query result as readable text for the LLM context."""
    if result is None:
        return "No results found."

    if isinstance(result, list):
        if not result:
            return "No results found."
        parts = []
        for item in result:
            if isinstance(item, dict):
                parts.append(_format_dict(item))
            else:
                parts.append(str(item))
        return "\n\n".join(parts)

    if isinstance(result, dict):
        return _format_dict(result)

    return str(result)


def _format_dict(d: dict, indent: int = 0) -> str:
    """Format a dict as readable text."""
    prefix = "  " * indent
    parts = []
    for k, v in d.items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, dict):
            parts.append(f"{prefix}{k}:")
            parts.append(_format_dict(v, indent + 1))
        elif isinstance(v, list):
            parts.append(f"{prefix}{k}:")
            for item in v:
                if isinstance(item, dict):
                    parts.append(_format_dict(item, indent + 1))
                else:
                    parts.append(f"{prefix}  - {item}")
        else:
            parts.append(f"{prefix}{k}: {v}")
    return "\n".join(parts)
