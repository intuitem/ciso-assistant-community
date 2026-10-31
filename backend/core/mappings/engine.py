from django.db.models import Q
from core.models import (
    Framework,
    StoredLibrary,
    ComplianceAssessment,
    RequirementNode,
    rescale_score,
)
from django.db.models.query import QuerySet
from collections import defaultdict, deque
from typing import Optional
import json
import zlib

# What a mapping link proves about its target, from its relationship (the
# source compared with the target) and its source's result, reading compliant
# as all of a requirement met, partially compliant as some of it met and some
# not, and non-compliant as none of it met. Links are approximate: a link
# carries its source's state to the part it shares with the target, taken as
# representative of the source. A pair missing here proves nothing.
# See documentation/architecture/decisions/mapping-inference-proven-facts.md.
LINK_FACTS: dict[tuple[str, str], frozenset[str]] = {
    ("equal", "compliant"): frozenset({"all_met"}),
    ("equal", "partially_compliant"): frozenset({"some_met", "some_unmet"}),
    ("equal", "non_compliant"): frozenset({"all_unmet"}),
    ("equal", "not_applicable"): frozenset({"not_applicable"}),
    ("superset", "compliant"): frozenset({"all_met"}),
    ("superset", "partially_compliant"): frozenset({"some_met", "some_unmet"}),
    ("superset", "non_compliant"): frozenset({"all_unmet"}),
    ("superset", "not_applicable"): frozenset({"not_applicable"}),
    ("subset", "compliant"): frozenset({"some_met"}),
    ("subset", "partially_compliant"): frozenset({"some_met", "some_unmet"}),
    ("subset", "non_compliant"): frozenset({"some_unmet"}),
    ("intersect", "compliant"): frozenset({"some_met"}),
    ("intersect", "partially_compliant"): frozenset({"some_met", "some_unmet"}),
    ("intersect", "non_compliant"): frozenset({"some_unmet"}),
}

# Results from most to least restrictive.
RESULT_ORDER = [
    "non_compliant",
    "partially_compliant",
    "not_assessed",
    "compliant",
    "not_applicable",
]


class MappingEngine:
    def __init__(self):
        """Reads the mapping graph from the database.

        Nothing is kept between instances on purpose. A module-level one is a
        cache per gunicorn worker, refreshed only in the worker that handled
        the write, so the others answer from a graph that predates a library
        loaded elsewhere (#4791). Callers build one per request instead.
        """
        self._frameworks = self.load_frameworks()
        (
            self._all_rms,
            self._framework_mappings,
            self._direct_mappings,
        ) = self.load_rms_data()
        self.own_scales = {
            urn: (min_score, max_score)
            for urn, min_score, max_score in RequirementNode.objects.exclude(
                min_score__isnull=True, max_score__isnull=True
            ).values_list("urn", "min_score", "max_score")
        }

        self.fields_to_map: list[str] = [
            "result",
            "status",
            "score",
            "is_scored",
            "observation",
            "documentation_score",
        ]

        self.m2m_fields = [
            "applied_controls",
            "security_exceptions",
            "evidences",
        ]

    @property
    def all_rms(self):
        return self._all_rms

    @all_rms.setter
    def all_rms(self, value):
        self._all_rms = value

    @property
    def framework_mappings(self):
        return self._framework_mappings

    @framework_mappings.setter
    def framework_mappings(self, value):
        self._framework_mappings = value

    @property
    def frameworks(self):
        return self._frameworks

    @frameworks.setter
    def frameworks(self, value):
        self._frameworks = value

    @property
    def direct_mappings(self):
        return self._direct_mappings

    @direct_mappings.setter
    def direct_mappings(self, value):
        self._direct_mappings = value

    # --- Compression helpers ---
    def _compress_rms(self, obj: dict) -> bytes:
        return zlib.compress(json.dumps(obj, separators=(",", ":")).encode("utf-8"))

    def _decompress_rms(self, data: bytes) -> dict:
        return json.loads(zlib.decompress(data).decode("utf-8"))

    def get_rms(self, index: tuple[str, str]) -> Optional[dict]:
        data = self.all_rms.get(index)
        if data is None:
            return None
        return self._decompress_rms(data)

    def load_rms_data(
        self,
    ) -> tuple[dict, "defaultdict[str, list[str]]", set[tuple[str, str]]]:
        """
        Loads requirement mapping sets (RMS) from libraries.

        Returns the tuple ``(all_rms, framework_mappings, direct_mappings)``
        built from the database. The caller is responsible for swapping these
        into the instance attributes once the load is known to have succeeded.
        """
        all_rms: dict = {}
        framework_mappings: "defaultdict[str, list[str]]" = defaultdict(list)
        direct_mappings: set[tuple[str, str]] = set()

        for lib in StoredLibrary.objects.filter(
            Q(content__requirement_mapping_set__isnull=False)
            | Q(content__requirement_mapping_sets__isnull=False),
            is_loaded=True,
        ):
            library_urn = lib.urn
            lib_id = lib.id
            content = lib.content

            if isinstance(content, dict):
                if "requirement_mapping_set" in content:
                    obj = content["requirement_mapping_set"]
                    index = (obj["source_framework_urn"], obj["target_framework_urn"])
                    obj["library_urn"] = library_urn
                    obj["id"] = str(lib_id)
                    all_rms[index] = self._compress_rms(obj)

                if "requirement_mapping_sets" in content:
                    for obj in content["requirement_mapping_sets"]:
                        index = (
                            obj["source_framework_urn"],
                            obj["target_framework_urn"],
                        )
                        obj["library_urn"] = library_urn
                        obj["id"] = str(lib_id)
                        all_rms[index] = self._compress_rms(obj)

        for src, tgt in all_rms:
            framework_mappings[src].append(tgt)
            direct_mappings.add((src, tgt))

        return all_rms, framework_mappings, direct_mappings

    def load_frameworks(self) -> dict:
        """Returns the frameworks mapping loaded from the database.

        The caller is responsible for swapping the returned dict into the
        instance attribute after the full reload succeeds.
        """
        return dict(
            [
                (
                    f.urn,
                    {
                        "min_score": f.min_score,
                        "max_score": f.max_score,
                        "id": str(f.id),
                        "name": str(f),
                    },
                )
                for f in Framework.objects.all()
            ]
        )

    def all_paths_between(
        self, source_urn: str, dest_urn: str, max_depth: Optional[int] = None
    ) -> list[list[str]]:
        # ✅ 1. Return only direct path if it exists
        if (source_urn, dest_urn) in self.direct_mappings:
            return [[source_urn, dest_urn]]

        # 🔄 2. BFS for shortest paths
        queue = deque()
        queue.append(([source_urn], {source_urn}))
        shortest_paths = []
        shortest_length = None

        while queue:
            path, visited = queue.popleft()
            current = path[-1]

            if current == dest_urn:
                if shortest_length is None:
                    shortest_length = len(path)
                if len(path) == shortest_length:
                    shortest_paths.append(path)
                continue

            if max_depth and len(path) >= max_depth:
                continue

            for neighbor in self.framework_mappings.get(current, []):
                if neighbor in visited:
                    continue
                queue.append((path + [neighbor], visited | {neighbor}))

        return shortest_paths

    def get_framework_neighbors(self, source_urn: str) -> list[str]:
        # retruns the second element of the tuple in the direct mapping set if the first one is equal to source_urn
        neighbors = []
        for couple in self.direct_mappings:
            if couple[0] == source_urn:
                neighbors.append(couple[1])
        return neighbors

    def paths_and_coverages(self, source_urn: str) -> dict[str, (int, int)]:
        # Base algo is the same as all_paths_from except than we also add the count of covered / partially-covered requirements
        # the coverage variable is a dict with key = destination and value = (number of partial coverage, number of total coverage)
        # as we are in direct mapping only for the moment, the "current" variable is always the destination
        coverage = {}
        for neighbor in self.get_framework_neighbors(source_urn):
            index = (source_urn, neighbor)
            rms = self.get_rms(index)
            if not rms:
                continue
            full_cov = 0
            partial_cov = 0
            for requirement in rms["requirement_mappings"]:
                if requirement["relationship"] in ("subset", "intersect"):
                    partial_cov += 1
                elif requirement["relationship"] in ("equal", "superset"):
                    full_cov += 1
                else:
                    continue
            coverage[neighbor] = (partial_cov, full_cov)

        return coverage

    def get_source_framework_urns(
        self, target_urn: str, max_depth: int = 3
    ) -> set[str]:
        """Return all framework URNs that can reach *target_urn* via mapping
        paths (reverse BFS on the framework_mappings graph).

        The target framework itself is always included (same-framework mapping).
        """
        reverse_graph: defaultdict[str, list[str]] = defaultdict(list)
        for src, targets in self.framework_mappings.items():
            for tgt in targets:
                reverse_graph[tgt].append(src)

        reachable: set[str] = {target_urn}
        queue: deque[tuple[str, int]] = deque([(target_urn, 0)])

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth - 1:
                continue
            for predecessor in reverse_graph.get(current, []):
                if predecessor not in reachable:
                    reachable.add(predecessor)
                    queue.append((predecessor, depth + 1))

        return reachable

    def all_paths_from(self, source_urn, max_depth=None):
        """
        Breadth-first search returning shortest paths from a source to all reachable targets.
        Yields only minimal-length paths to each destination.
        """
        queue = deque()
        queue.append(([source_urn], {source_urn}))
        shortest_lengths = defaultdict(set)
        shortest_lengths[source_urn].add(0)

        paths = defaultdict(list)

        while queue:
            path, visited = queue.popleft()
            current = path[-1]

            length = len(path) - 1
            paths[(source_urn, current)].append(path)

            if max_depth and len(path) >= max_depth:
                continue

            for neighbor in self.framework_mappings.get(current, []):
                if neighbor in visited:
                    continue

                next_length = length + 1

                # added if never seen, or we explore a new minimal length to this node
                if neighbor not in shortest_lengths or next_length <= min(
                    shortest_lengths[neighbor]
                ):
                    shortest_lengths[neighbor].add(next_length)
                    queue.append((path + [neighbor], visited | {neighbor}))

        # return all found paths grouped by (source, destination)
        for path_list in paths.values():
            yield from path_list

    def get_mapping_graph(self, max_depth: int = 3) -> list[list[str]]:
        """
        Generates a graph of all connected frameworks by finding all
        simple paths (no cycles) up to a given max_depth.

        The `max_depth` refers to the number of nodes in the path.
        - max_depth = 2 (minimum): Returns only direct mappings [A, B]
        - max_depth = 3 (default): Returns [A, B] and [A, B, C]

        Args:
            max_depth: The maximum length (number of nodes) for any
                       mapping path. Defaults to 3.

        Returns:
            A list of all unique mapping paths found, where each path
            is a list of framework URNs.
        """
        # Enforce minimum max_depth of 2 (for a direct A -> B mapping)
        if max_depth < 2:
            max_depth = 2

        all_paths: list[list[str]] = []
        found_paths_set: set[tuple[str, ...]] = set()

        # start a search from every framework as a potential source
        for start_node in self.frameworks.keys():
            # The queue will store the path explored so far
            queue: deque[list[str]] = deque()
            queue.append([start_node])

            while queue:
                current_path = queue.popleft()
                current_node = current_path[-1]

                # Store the path if it's a valid mapping (len >= 2)
                #    and we haven't seen it before.
                if len(current_path) >= 2:
                    path_tuple = tuple(current_path)
                    if path_tuple not in found_paths_set:
                        all_paths.append(current_path)
                        found_paths_set.add(path_tuple)

                # If we are not yet at max_depth, explore neighbors
                if len(current_path) < max_depth:
                    for neighbor in self.framework_mappings.get(current_node, []):
                        # Avoid cycles within the *current* path
                        if neighbor not in current_path:
                            # Create and enqueue the new path
                            new_path = current_path + [neighbor]
                            queue.append(new_path)

        return all_paths

    def map_audit_results(
        self,
        source_audit: dict[str, str | dict[str, str]],
        requirement_mapping_set: dict,
        hop_index: int,
        path: list[str],
        target_range: Optional[tuple[int, int]] = None,
    ) -> dict[str, str | dict[str, str]]:
        # Hop_index allows us to know if the source_audit is the 'real' source, or a transition audit.
        # The first hop in 1.
        if not source_audit.get("requirement_assessments"):
            return {}
        target_audit: dict[str, str | dict[str, str | dict[str, str]]] = {
            "requirement_assessments": defaultdict(dict)
        }

        # Framework info may be missing (library references frameworks not in DB).
        # Use .get() and treat missing info as "non equal" so we don't attempt
        # to copy scores that cannot be validated against a target framework.
        target_framework_urn = requirement_mapping_set.get("target_framework_urn", "")
        target_framework = self.frameworks.get(target_framework_urn)

        source_range = (source_audit.get("min_score"), source_audit.get("max_score"))
        if target_range is not None:
            target_range = tuple(target_range)
            scores_compatible = None not in (*source_range, *target_range)
        else:
            scores_compatible = (
                target_framework
                and target_framework.get("min_score") == source_range[0]
                and target_framework.get("max_score") == source_range[1]
            )

        def scaled(field, value, own_scale):
            if (
                own_scale is None
                and field in ("score", "documentation_score")
                and value is not None
                and target_range is not None
                and source_range != target_range
            ):
                return rescale_score(value, source_range, target_range)
            return value

        # Per target: the facts its links prove (LINK_FACTS), the facts its
        # full-coverage links prove alone, and the most restrictive result of
        # the latter, for inputs that contradict themselves. Its full-coverage
        # and partial links, as (source urn, source assessment, own scale,
        # copy_scores), supply its other fields after the loop.
        target_facts: defaultdict[str, set[str]] = defaultdict(set)
        full_facts: defaultdict[str, set[str]] = defaultdict(set)
        full_results: dict[str, Optional[str]] = {}
        full_links: defaultdict[str, list[tuple]] = defaultdict(list)
        partial_links: defaultdict[str, list[tuple]] = defaultdict(list)

        for mapping in requirement_mapping_set["requirement_mappings"]:
            src = mapping["source_requirement_urn"]
            dst = mapping["target_requirement_urn"]
            rel = mapping["relationship"]

            # Fix 1: Use .get() to avoid defaultdict auto-creation for
            # non-existent source requirements.
            src_assessment = source_audit["requirement_assessments"].get(src)
            if src_assessment is None:
                continue
            own_scale = self.own_scales.get(src)
            copy_scores = own_scale == self.own_scales.get(dst) and (
                own_scale is not None or scores_compatible
            )

            # Track whether this mapping entry actually wrote data.
            mapped = False

            if rel in ("equal", "superset"):
                # Scores are copied when both sides are comparable: converted
                # into the target audit's range, or kept as-is on a requirement
                # scale shared by source and target. Otherwise only non-score
                # fields are copied, to avoid misrepresenting scores. The
                # mapped fields themselves are set after the loop.
                if copy_scores:
                    # Fix 2: Use .get() for collision detection instead of
                    # defaultdict auto-creation.  An empty dict {} (from a
                    # previous defaultdict miss) is falsy, so this is safe.
                    existing_target = target_audit["requirement_assessments"].get(dst)
                    if existing_target:
                        # Handle collision: merge m2m fields
                        for m2m_field in self.m2m_fields:
                            if m2m_field in src_assessment:
                                existing = set(existing_target.get(m2m_field, []))
                                new_values = set(src_assessment.get(m2m_field, []))
                                existing_target[m2m_field] = list(existing | new_values)
                    else:
                        # mapping_inference is built for this target below:
                        # copying the source's would share one dict between
                        # every target of that source (hop 2 and beyond).
                        target_audit["requirement_assessments"][dst] = {
                            k: v
                            for k, v in src_assessment.items()
                            if k != "mapping_inference" and k not in self.fields_to_map
                        }
                    mapped = True
                else:
                    target_assessment = target_audit["requirement_assessments"][dst]

                    # Merge m2m fields for collisions
                    for m2m_field in self.m2m_fields:
                        if m2m_field in src_assessment:
                            existing_target = target_audit[
                                "requirement_assessments"
                            ].get(dst)
                            if existing_target and m2m_field in existing_target:
                                existing = set(existing_target.get(m2m_field, []))
                                new_values = set(src_assessment.get(m2m_field, []))
                                target_assessment[m2m_field] = list(
                                    existing | new_values
                                )
                            else:
                                target_assessment[m2m_field] = src_assessment.get(
                                    m2m_field
                                )
                    mapped = True

            elif rel in ("subset", "intersect"):
                target_assessment = target_audit["requirement_assessments"][dst]

                # Merge applied_controls for collisions
                src_applied_controls = src_assessment.get("applied_controls", [])
                existing_target = target_audit["requirement_assessments"].get(dst)
                if existing_target and "applied_controls" in existing_target:
                    existing = set(existing_target["applied_controls"])
                    new_values = set(src_applied_controls)
                    target_assessment["applied_controls"] = list(existing | new_values)
                else:
                    target_assessment["applied_controls"] = src_applied_controls

                # Merge other m2m fields
                for m2m_field in self.m2m_fields:
                    if m2m_field != "applied_controls" and m2m_field in src_assessment:
                        src_values = src_assessment.get(m2m_field, [])
                        existing_target = target_audit["requirement_assessments"].get(
                            dst
                        )
                        if existing_target and m2m_field in existing_target:
                            existing = set(existing_target[m2m_field])
                            new_values = set(src_values)
                            target_assessment[m2m_field] = list(existing | new_values)
                        else:
                            target_assessment[m2m_field] = src_values
                mapped = True

            # Fix 3: Only build mapping_inference for recognized relationships
            # that actually produced data.
            if not mapped:
                continue

            target_assessment = target_audit["requirement_assessments"][dst]

            # Result: what this link proves about the target, gathered over
            # all its links. The target's result is read from the facts after
            # the loop, once all its links are in, so their order doesn't
            # matter.
            link_facts = LINK_FACTS.get(
                (rel, src_assessment.get("result")), frozenset()
            )
            target_facts[dst] |= link_facts
            link = (src, src_assessment, own_scale, copy_scores)
            if rel in ("equal", "superset"):
                full_facts[dst] |= link_facts
                full_results[dst] = self._most_restrictive_result(
                    full_results.get(dst), src_assessment.get("result")
                )
                full_links[dst].append(link)
            else:
                partial_links[dst].append(link)

            mapping_set_info = {
                k: v
                for k, v in {
                    "urn": requirement_mapping_set.get("urn"),
                    "name": requirement_mapping_set.get("name"),
                    "ref_id": requirement_mapping_set.get("ref_id"),
                    "id": requirement_mapping_set.get("id"),
                    "library_urn": requirement_mapping_set.get("library_urn"),
                }.items()
                if v
            }

            mapping_inference = target_assessment.get("mapping_inference", {})
            source_requirement_assessments = mapping_inference.get(
                "source_requirement_assessments", {}
            )

            mapping_inference["used_path"] = path
            incoming_annotation = src_assessment.get("mapping_inference", {}).get(
                "annotation", ""
            )
            if incoming_annotation:
                mapping_inference["annotation"] = incoming_annotation
            else:
                mapping_inference.setdefault("annotation", "")

            target_assessment["mapping_inference"] = mapping_inference
            target_assessment["mapping_inference"]["source_requirement_assessments"] = (
                source_requirement_assessments
            )

            def merge_source_requirement_assessment(key: str, new_value: dict) -> None:
                existing = source_requirement_assessments.get(key, {}).copy()
                existing_cov = existing.get("coverage")
                new_cov = new_value.get("coverage")

                if new_cov:
                    if existing_cov == "full" or new_cov == "full":
                        existing["coverage"] = "full"
                    else:
                        existing["coverage"] = "partial"

                for field, value in new_value.items():
                    if field == "coverage" or value is None:
                        continue
                    if field == "used_mapping_set":
                        if value and not existing.get("used_mapping_set"):
                            existing["used_mapping_set"] = value
                        continue
                    if existing.get(field) in (None, "", []):
                        existing[field] = value

                source_requirement_assessments[key] = existing

            if hop_index == 1:
                ra = source_audit["requirement_assessments"][src]
                merge_source_requirement_assessment(
                    src,
                    {
                        "id": ra.get("id"),
                        "urn": src,
                        "str": ra.get("name"),
                        "coverage": "full"
                        if rel in ("equal", "superset")
                        else "partial",
                        "score": ra.get("score"),
                        "is_scored": ra.get("is_scored"),
                        "source_framework": ra.get("source_framework"),
                        "used_mapping_set": mapping_set_info,
                    },
                )
            else:
                # Coverage is weakest-link along a path: an earlier-hop source
                # can only remain "full" through this hop if this hop is also
                # full (equal/superset). Otherwise it degrades to "partial".
                hop_full = rel in ("equal", "superset")

                # Propagate sources from earlier hops.
                for mif_id, mif_value in (
                    src_assessment.get("mapping_inference", {})
                    .get("source_requirement_assessments", {})
                    .items()
                ):
                    copied_value = mif_value.copy()
                    if not hop_full and copied_value.get("coverage") == "full":
                        copied_value["coverage"] = "partial"
                    if mapping_set_info and not copied_value.get("used_mapping_set"):
                        copied_value["used_mapping_set"] = mapping_set_info
                    merge_source_requirement_assessment(mif_id, copied_value)

                # Also record the intermediate requirement itself so
                # the user sees which mapping set was used for this hop.
                src_fw_urn = requirement_mapping_set.get("source_framework_urn", "")
                src_fw_info = self.frameworks.get(src_fw_urn, {})
                merge_source_requirement_assessment(
                    src,
                    {
                        "urn": src,
                        "str": src_assessment.get("name"),
                        "coverage": "full"
                        if rel in ("equal", "superset")
                        else "partial",
                        "score": src_assessment.get("score"),
                        "is_scored": src_assessment.get("is_scored"),
                        "source_framework": {
                            "id": src_fw_info.get("id", ""),
                            "name": src_fw_info.get("name", src_fw_urn),
                        },
                        "used_mapping_set": mapping_set_info,
                    },
                )

        # Each target's result, now that all its links are in. No rule settles
        # inputs that contradict themselves, so the full-coverage links are
        # believed, and if they clash too, the most restrictive of their
        # results.
        for dst, facts in target_facts.items():
            if self._facts_contradict(facts):
                facts = full_facts[dst]
            if self._facts_contradict(facts):
                result = full_results[dst]
            else:
                result = self._result_from_facts(facts)
            target_assessment = target_audit["requirement_assessments"][dst]
            target_assessment["result"] = result
            target_assessment["mapping_inference"]["result"] = result

            # Status and observation come from the full-coverage links, scores
            # from those whose scores are comparable, or else from the partial
            # links whose scores are. One link supplies each group
            # (_decisive_link), so the order of the links doesn't matter.
            status_link = self._decisive_link(full_links[dst])
            if status_link is not None:
                _, src_assessment, _, _ = status_link
                for field in ("status", "observation"):
                    if field in src_assessment:
                        target_assessment[field] = src_assessment[field]
            score_link = self._decisive_link(
                [link for link in full_links[dst] if link[3]]
            ) or self._decisive_link([link for link in partial_links[dst] if link[3]])
            if score_link is not None:
                _, src_assessment, own_scale, _ = score_link
                for field in ("score", "is_scored", "documentation_score"):
                    if field in src_assessment:
                        target_assessment[field] = scaled(
                            field, src_assessment[field], own_scale
                        )

        return target_audit

    def _decisive_link(self, links):
        """Returns the link that supplies a target's fields among several, the
        same whatever their order: the most restrictive result, then the
        lowest score, then the first source urn. None when there is none."""
        return min(
            links,
            key=lambda link: (
                self._result_rank(link[1].get("result")),
                link[1].get("score") is None,
                link[1].get("score") or 0,
                link[0],
            ),
            default=None,
        )

    def _result_rank(self, result):
        """Position of a result in RESULT_ORDER, unknown results last."""
        try:
            return RESULT_ORDER.index(result)
        except ValueError:
            return len(RESULT_ORDER)

    def _facts_contradict(self, facts):
        """Whether facts about one requirement contradict each other: all of
        it met with a part unmet, or none of it met with a part met."""
        return ("all_met" in facts and bool(facts & {"some_unmet", "all_unmet"})) or (
            "all_unmet" in facts and bool(facts & {"some_met", "all_met"})
        )

    def _result_from_facts(self, facts):
        """Returns the result that consistent facts prove, at its lowest.

        Exact when the facts settle it: a met part and an unmet part make the
        requirement partially compliant. Otherwise the lowest result they
        allow, so the result never overstates what the links prove. Facts
        that say nothing give not_assessed, the "no information" result.
        """
        if "all_met" in facts:
            return "compliant"
        if "some_met" in facts:
            return "partially_compliant"
        if facts & {"some_unmet", "all_unmet"}:
            return "non_compliant"
        if "not_applicable" in facts:
            return "not_applicable"
        return "not_assessed"

    def _most_restrictive_result(self, result1, result2):
        """Returns the most restrictive result between two results.

        A minimum over a fixed order, with None as "no result": folding the
        links to one target gives the same answer whatever their order.
        """
        if result1 is None:
            return result2
        if result2 is None:
            return result1
        if self._result_rank(result1) < self._result_rank(result2):
            return result1
        return result2

    def best_mapping_inferences(
        self,
        source_audit: dict[str, str | dict[str, str]],
        source_urn: str,
        dest_urn: str,
        max_depth: Optional[int] = None,
        target_range: Optional[tuple[int, int]] = None,
    ) -> tuple[dict, list[str]]:
        paths = self.all_paths_between(source_urn, dest_urn, max_depth)
        inferences = {}
        best_path = []

        for path in paths:
            tmp_inferences = source_audit.copy()
            tmp_urn = source_urn
            hop_index = 1
            for urn in path[1:]:
                rms = self.get_rms((tmp_urn, urn))
                if not rms:
                    break
                tmp_inferences = self.map_audit_results(
                    tmp_inferences,
                    rms,
                    hop_index=hop_index,
                    path=path,
                    target_range=target_range if urn == path[-1] else None,
                )
                hop_index += 1
                tmp_urn = urn

            if len(tmp_inferences) > len(inferences):
                inferences = tmp_inferences
                best_path = path
        return inferences, best_path

    def load_audit_fields(
        self,
        audit: ComplianceAssessment,
    ) -> dict[str, str | dict[str, str]]:
        """
        Extracts requirement assessments from a compliance audit.
        Args:
            audit: The compliance assessment object.
            fields: The fields to extrract from each requirement assessment.
        Returns:
            A dictionary mapping requirement URNs to their requested fields.
        """
        fields = self.fields_to_map
        all_ra = audit.get_requirement_assessments(include_non_assessable=False)
        audit_results = {
            "min_score": audit.min_score,
            "max_score": audit.max_score,
            "requirement_assessments": defaultdict(dict),
        }
        for ra in all_ra:
            audit_results["requirement_assessments"][ra.requirement.urn] = {
                field: getattr(ra, field) for field in fields
            }
            audit_results["requirement_assessments"][ra.requirement.urn]["name"] = str(
                ra
            )
            audit_results["requirement_assessments"][ra.requirement.urn]["id"] = str(
                ra.id
            )
            audit_results["requirement_assessments"][ra.requirement.urn][
                "source_framework"
            ] = {
                "id": str(audit.framework.id),
                "name": str(audit.framework),
            }
            for m2m_field in self.m2m_fields:
                attr = getattr(ra, m2m_field)
                if isinstance(attr, QuerySet) or hasattr(attr, "all"):
                    related_items = list(attr.all())
                    audit_results["requirement_assessments"][ra.requirement.urn][
                        m2m_field
                    ] = [item.id for item in related_items]
                else:
                    audit_results["requirement_assessments"][ra.requirement.urn][
                        m2m_field
                    ] = attr
        return audit_results

    def summary_results(
        self,
        audit_results: dict[str, dict[str, str]],
        filter_urns: Optional[set[str]] = None,
    ) -> dict[str, int]:
        """Summarizes audit result counts by status.

        Args:
            audit_results: The audit results dictionary.
            filter_urns: Optional set of URNs to filter results by. If provided,
                only requirements with URNs in this set will be counted.
        """
        res = defaultdict(int)
        if (
            isinstance(audit_results, dict)
            and "requirement_assessments" in audit_results
        ):
            iterable = audit_results["requirement_assessments"].items()
        else:
            iterable = getattr(audit_results, "items", lambda: [])()

        for urn, audit in iterable:
            if filter_urns is not None and urn not in filter_urns:
                continue
            result = audit.get("result")
            if result is None:
                continue

            res[result] += 1

        return dict(res)
