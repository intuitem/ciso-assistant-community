from core.models import StoredLibrary, ComplianceAssessment
from collections import defaultdict, deque
from typing import Optional
import json
import zlib


class MappingEngine:
    def __init__(self):
        # Values are compressed (zlib) JSON bytes of the RMS object.
        self.all_rms: dict[tuple[str, str], bytes] = {}
        self.framework_mappings: dict[str, list[str]] = defaultdict(list)
        self.direct_mappings: set[tuple[str, str]] = set()

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

    def map_audit_results(self, source_audit_results: dict, rms: dict) -> dict:
        if not source_audit_results:
            return {}
        target_results = {}
        for mapping in rms["requirement_mappings"]:
            src = mapping["source_requirement_urn"]
            dst = mapping["target_requirement_urn"]
            rel = mapping["relationship"]

            if rel in ("equal", "superset") and src in source_audit_results:
                target_results[dst] = source_audit_results[src]
            elif rel in ("subset", "intersect") and src in source_audit_results:
                r = source_audit_results[src]
                if r in ("not_assessed", "non_compliant"):
                    target_results[dst] = r
                elif r in ("compliant", "partially_compliant"):
                    target_results[dst] = "partially_compliant"
        return target_results

    def best_mapping_results(
        self,
        source_audit_results: dict,
        source_urn: str,
        dest_urn: str,
        max_depth: Optional[int] = None,
    ) -> tuple[dict, list[str]]:
        paths = self.all_paths_between(source_urn, dest_urn, max_depth)
        results = {}
        best_path = []

        for path in paths:
            tmp_results = source_audit_results.copy()
            tmp_urn = source_urn

            for urn in path[1:]:
                rms = self.get_rms((tmp_urn, urn))
                if not rms:
                    break
                tmp_results = self.map_audit_results(tmp_results, rms)
                tmp_urn = urn

            if len(tmp_results) > len(results):
                results = tmp_results
                best_path = path

        return results, best_path

    def load_audit_results(self, audit: ComplianceAssessment) -> dict[str, str]:
        """
        Extracts requirement assessments from a compliance audit.
        Args:
            audit: The compliance assessment object.
        Returns:
            A dictionary mapping requirement URNs to their result status.
        """
        all_ra = audit.get_requirement_assessments(include_non_assessable=False)
        audit_results = {}
        for ra in all_ra:
            audit_results[ra.requirement.urn] = ra.result
        return audit_results

    def summary_results(self, audit_results: dict[str, str]) -> dict[str, int]:
        """Summarizes audit result counts by status."""
        res = defaultdict(int)
        for _, result in audit_results.items():
            res[result] += 1
        return dict(res)
