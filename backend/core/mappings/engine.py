from ctypes import sizeof
from icecream import ic
from core.models import (
    Framework,
    StoredLibrary,
    ComplianceAssessment,
)
from django.db.models.query import QuerySet
from collections import defaultdict, deque
from typing import Optional
import json
import zlib


class MappingEngine:
    def __init__(self):
        # Values are compressed (zlib) JSON bytes of the RMS object.
        self.all_rms: dict[tuple[str, str], bytes] = {}
        self.framework_mappings: dict[str, list[str]] = defaultdict(list)
        self.frameworks: dict[str, dict[str, int]] = defaultdict(dict)
        self.direct_mappings: set[tuple[str, str]] = set()

        if not self.frameworks:
            self.load_frameworks()

        if not self.direct_mappings:
            self.load_rms_data()

        self.fields_to_map: list[str] = [
            "result",
            "status",
            "score",
            "is_scored",
            "observation",
        ]

        self.m2m_fields = [
            "applied_controls",
            "security_exceptions",
            "evidences",
            "mapping_inference",
        ]

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

    def load_rms_data(self) -> None:
        """
        Loads requirement mapping sets (RMS) from libraries.
        Builds internal structures: all_rms and framework_mappings.
        """
        for lib in StoredLibrary.objects.all():
            library_urn = lib.urn
            content = lib.content

            if isinstance(content, dict):
                if "requirement_mapping_set" in content:
                    obj = content["requirement_mapping_set"]
                    index = (obj["source_framework_urn"], obj["target_framework_urn"])
                    obj["library_urn"] = library_urn
                    self.all_rms[index] = self._compress_rms(obj)

                if "requirement_mapping_sets" in content:
                    for obj in content["requirement_mapping_sets"]:
                        index = (
                            obj["source_framework_urn"],
                            obj["target_framework_urn"],
                        )
                        obj["library_urn"] = library_urn
                        self.all_rms[index] = self._compress_rms(obj)

        for src, tgt in self.all_rms:
            self.framework_mappings[src].append(tgt)
            self.direct_mappings.add((src, tgt))

    def load_frameworks(self) -> None:
        self.frameworks = dict(
            [
                (f.urn, {"min_score": f.min_score, "max_score": f.max_score})
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

    def map_audit_results(
        self,
        source_audit: dict[str, str | dict[str, str]],
        requirement_mapping_set: dict,
    ) -> dict[str, str | dict[str, str]]:
        if not source_audit.get("requirement_assessments"):
            return {}
        target_audit: dict[str, str | dict[str, str]] = defaultdict(dict)
        # Framework info may be missing (library references frameworks not in DB).
        # Use .get() and treat missing info as "non equal" so we don't attempt
        # to copy scores that cannot be validated against a target framework.
        target_framework_urn = requirement_mapping_set.get("target_framework_urn", "")
        target_framework = self.frameworks.get(target_framework_urn)
        # TODO: Make this more resilient
        if target_framework is not None:
            ic(target_framework)
        for mapping in requirement_mapping_set["requirement_mappings"]:
            src = mapping["source_requirement_urn"]
            dst = mapping["target_requirement_urn"]
            rel = mapping["relationship"]

            if (
                rel in ("equal", "superset")
                and src in source_audit["requirement_assessments"]
            ):
                # If we have matching score ranges on the target framework, copy
                # the whole assessment (including score fields). Otherwise only
                # copy non-score fields to avoid misrepresenting scores.
                src_assessment = source_audit["requirement_assessments"][src]
                if (
                    target_framework
                    and target_framework.get("min_score")
                    == source_audit.get("min_score")
                    and target_framework.get("max_score")
                    == source_audit.get("max_score")
                ):
                    target_audit[dst] = src_assessment
                else:
                    for field in self.fields_to_map:
                        if field not in ["score", "is_scored"]:
                            target_audit[dst][field] = src_assessment.get(field)

            elif (
                rel in ("subset", "intersect")
                and src in source_audit["requirement_assessments"]
            ):
                result = source_audit["requirement_assessments"][src]["result"]
                target_audit[dst]["applied_controls"] = source_audit[
                    "requirement_assessments"
                ][src]["applied_controls"]
                if result in ("not_assessed", "non_compliant"):
                    target_audit[dst]["result"] = result
                elif result in ("compliant", "partially_compliant"):
                    target_audit[dst]["result"] = "partially_compliant"
        return target_audit

    def best_mapping_inferrences(
        self,
        source_audit: dict[str, str | dict[str, str]],
        source_urn: str,
        dest_urn: str,
        max_depth: Optional[int] = None,
    ) -> tuple[dict, list[str]]:
        paths = self.all_paths_between(source_urn, dest_urn, max_depth)
        inferrences = {}
        best_path = []

        for path in paths:
            tmp_inferrences = source_audit.copy()
            tmp_urn = source_urn

            for urn in path[1:]:
                rms = self.get_rms((tmp_urn, urn))
                if not rms:
                    break
                tmp_inferrences = self.map_audit_results(tmp_inferrences, rms)
                tmp_urn = urn

            if len(tmp_inferrences) > len(inferrences):
                inferrences = tmp_inferrences
                best_path = path

        return inferrences, best_path

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
            "requirement_assessments": {},
        }
        for ra in all_ra:
            audit_results["requirement_assessments"][ra.requirement.urn] = {
                field: getattr(ra, field) for field in fields
            }
            for m2m_field in self.m2m_fields:
                attr = getattr(ra, m2m_field)
                if isinstance(attr, QuerySet) or hasattr(attr, "all"):
                    audit_results["requirement_assessments"][ra.requirement.urn][
                        m2m_field
                    ] = attr.all().values_list("id", flat=True)
                else:
                    audit_results["requirement_assessments"][ra.requirement.urn][
                        m2m_field
                    ] = attr

        return audit_results

    def summary_results(
        self, audit_results: dict[str, dict[str, str]]
    ) -> dict[str, int]:
        """Summarizes audit result counts by status."""
        res = defaultdict(int)
        if (
            isinstance(audit_results, dict)
            and "requirement_assessments" in audit_results
        ):
            iterable = audit_results["requirement_assessments"].items()
        else:
            iterable = getattr(audit_results, "items", lambda: [])()

        for _, audit in iterable:
            result = audit.get("result")
            if result is None:
                continue

            res[result] += 1

        return dict(res)


engine = MappingEngine()
