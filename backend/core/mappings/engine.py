from icecream import ic
from core.models import Framework, StoredLibrary, ComplianceAssessment
from collections import defaultdict, deque
from typing import Optional
import json
import zlib


class MappingEngine:
    frameworks = None
    direct_mappings = None

    def __init__(self):
        # Values are compressed (zlib) JSON bytes of the RMS object.
        self.all_rms: dict[tuple[str, str], bytes] = {}
        self.framework_mappings: dict[str, list[str]] = defaultdict(list)

        if self.frameworks == None:
            self.frameworks = defaultdict(dict)
            self.load_frameworks()

        if self.direct_mappings == None:
            self.direct_mappings: set[tuple[str, str]] = set()
            self.load_rms_data()

        self.fields_to_map: list[str] = [
            "result",
            "status",
            "score",
            "is_scored",
            "observation",
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
            # NOTE: Only allowing direct mappings for now
            # self.framework_mappings[src].append(tgt)
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
    ) -> dict[str, dict[str, str]]:
        if not source_audit.get("requirement_assessments"):
            return {}
        target_audit = defaultdict(dict)
        ic(self.frameworks[requirement_mapping_set["target_framework_urn"]])
        for mapping in requirement_mapping_set["requirement_mappings"]:
            src = mapping["source_requirement_urn"]
            dst = mapping["target_requirement_urn"]
            rel = mapping["relationship"]

            if (
                rel in ("equal", "superset")
                and src in source_audit["requirement_assessments"]
            ):
                if self.frameworks[requirement_mapping_set["target_framework_urn"]].get(
                    "min_score"
                ) == source_audit.get("min_score") and self.frameworks[
                    requirement_mapping_set["target_framework_urn"]
                ].get("max_score") == source_audit.get("max_score"):
                    target_audit[dst] = source_audit["requirement_assessments"][src]
                else:
                    for field in self.fields_to_map:
                        if field not in ["score", "is_scored"]:
                            target_audit[dst][field] = source_audit[
                                "requirement_assessments"
                            ][src][field]

            elif (
                rel in ("subset", "intersect")
                and src in source_audit["requirement_assessments"]
            ):
                result = source_audit["requirement_assessments"][src]["result"]
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
        return audit_results

    def summary_results(
        self, audit_results: dict[str, dict[str, str]]
    ) -> dict[str, int]:
        """Summarizes audit result counts by status."""
        res = defaultdict(int)
        for _, audit in audit_results.items():
            res[audit["result"]] += 1
        return dict(res)


engine = MappingEngine()
