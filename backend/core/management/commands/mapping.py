from django.core.management.base import BaseCommand
from core.models import StoredLibrary, ComplianceAssessment
from collections import defaultdict, deque
import random
import uuid
import time
from typing import Dict, Tuple, List, Optional
import json

NUM_FRAMEWORKS = 1000
NUM_MAPPINGS = 100
NUM_PIVOTS = 10


class MappingEngine:

    def __init__(self):
        self.all_rms: Dict[Tuple[str, str], dict] = {}
        self.framework_mappings: Dict[str, List[str]] = defaultdict(list)
        self.direct_mappings: set[Tuple[str, str]] = set()

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
                    self.all_rms[index] = obj

                if "requirement_mapping_sets" in content:
                    for obj in content["requirement_mapping_sets"]:
                        index = (
                            obj["source_framework_urn"],
                            obj["target_framework_urn"],
                        )
                        obj["library_urn"] = library_urn
                        self.all_rms[index] = obj

        for src, tgt in self.all_rms:
            self.framework_mappings[src].append(tgt)
            self.direct_mappings.add((src, tgt))


    def all_paths_between(
        self, source_urn: str, dest_urn: str, max_depth: Optional[int] = None
    ) -> List[List[str]]:
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
    ) -> Tuple[dict, List[str]]:
        paths = self.all_paths_between(source_urn, dest_urn, max_depth)
        results = {}
        best_path = []

        for path in paths:
            tmp_results = source_audit_results.copy()
            tmp_urn = source_urn

            for urn in path[1:]:
                rms = self.all_rms.get((tmp_urn, urn))
                if not rms:
                    break
                tmp_results = self.map_audit_results(tmp_results, rms)
                tmp_urn = urn

            if len(tmp_results) > len(results):
                results = tmp_results
                best_path = path

        return results, best_path

    def load_audit_results(self, audit: ComplianceAssessment) -> Dict[str, str]:
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

    def summary_results(self, audit_results: Dict[str, str]) -> Dict[str, int]:
        """Summarizes audit result counts by status."""
        res = defaultdict(int)
        for _, result in audit_results.items():
            res[result] += 1
        return dict(res)


def sizeof_json(obj) -> int:
    """Returns the size of a JSON-encoded object in bytes."""
    return len(json.dumps(obj).encode("utf-8"))


class Command(BaseCommand):
    help = "Displays mappings with optional test data and pruning"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test",
            action="store_true",
            help="Utilise des données de test simulées (1000 frameworks, pivots, etc.)",
        )
        parser.add_argument(
            "--depth",
            type=int,
            default=None,
            help="Profondeur maximale des chemins à explorer (optionnel)",
        )

    def generate_test_data(self) -> Dict[Tuple[str, str], dict]:
        random.seed(42)  # Fixed seed for reproducibility
        all_rms = {}
        non_pivot_frameworks = [
            f"urn:framework:{i}" for i in range(NUM_FRAMEWORKS - NUM_PIVOTS)
        ]
        pivots = [f"urn:framework:pivot{i}" for i in range(NUM_PIVOTS)]

        # 1. random mappings
        for _ in range(NUM_MAPPINGS):
            source, target = random.sample(non_pivot_frameworks, 2)
            urn = f"urn:rms:{uuid.uuid4()}"
            all_rms[(source, target)] = {
                "urn": urn,
                "library_urn": "urn:library:test",
                "source_framework_urn": source,
                "target_framework_urn": target,
            }

        # 2. pivots have mapping to 60% of other frameworks
        for pivot in pivots:
            targets = random.sample(
                non_pivot_frameworks, int(0.6 * len(non_pivot_frameworks))
            )
            for target in targets:
                urn = f"urn:rms:{uuid.uuid4()}"
                all_rms[(pivot, target)] = {
                    "urn": urn,
                    "library_urn": "urn:library:test",
                    "source_framework_urn": pivot,
                    "target_framework_urn": target,
                }

        return all_rms

    def format_summary_inline(self, summary):
        """
        Return a prettified single-line summary of audit results.
        """
        status_labels = {
            "compliant": "✅",
            "partially_compliant": "🟡",
            "non_compliant": "❌",
            "not_applicable": "🚫",
            "not_assessed": "❓",
        }

        ordered_keys = [
            "compliant",
            "partially_compliant",
            "non_compliant",
            "not_applicable",
            "not_assessed",
        ]

        parts = [
            f"{status_labels[k]} {summary.get(k, 0)}"
            for k in ordered_keys
            if summary.get(k, 0) > 0
        ]

        return " | ".join(parts) if parts else "No results"

    def handle(self, *args, **options):
        test_mode = options.get("test")
        max_depth = options.get("depth")

        engine = MappingEngine()

        if test_mode:
            print("🔧 Test mode enabled: generating simulated data...")
            engine.all_rms = self.generate_test_data()
            # Build graph from mappings
            start_explore = time.time()
            for src, tgt in engine.all_rms:
                engine.framework_mappings[src].append(tgt)

            # Collect all paths using optimized exploration
            print("\n🌿 Optimized paths (with dynamic pruning):\n")
            all_paths = []
            for source in engine.framework_mappings:
                for path in engine.all_paths_from(source, max_depth=max_depth):
                    if len(path) > 1:
                        all_paths.append(path)

            # Sort paths by (source ➝ destination)
            all_paths.sort(key=lambda p: (p[0], p[-1]))
            explore_duration = time.time() - start_explore

            # Display all sorted paths
            last_key = None
            for path in all_paths:
                key = (path[0], path[-1])
                if key != last_key:
                    print("")  # visual break between groups
                print(" ➝ ".join(path))
                last_key = key

            print(f"\n✅ Total paths displayed: {len(all_paths)}")
            print(f"⏱️ Path exploration time: {explore_duration * 1000:.2f} ms")

        else:
            # ⏱️ Measure data loading time
            start_load = time.time()
            nb_libraries = StoredLibrary.objects.count()
            print(f"📚 Loaded {nb_libraries} libraries from the database.")
            engine.load_rms_data()
            load_duration = time.time() - start_load
            print(f"🕒 Data load completed in {load_duration * 1000:.2f} ms.")

            # 📦 Estimate serialized sizes
            rms_size_bytes = sum(sizeof_json(obj) for obj in engine.all_rms.values())
            map_size_bytes = sizeof_json(
                dict(engine.framework_mappings)
            )  # Convert defaultdict to dict for serialization

            print(
                f"💾 Data sizes: all_rms = {rms_size_bytes / 1024:.1f} KB, "
                f"framework_mappings = {map_size_bytes / 1024:.1f} KB"
            )

            # Get all unique frameworks from the mappings
            frameworks_in_mappings = set()
            for src, tgt in engine.all_rms.keys():
                frameworks_in_mappings.add(src)
                frameworks_in_mappings.add(tgt)

            audits = list(ComplianceAssessment.objects.all())

            for audit in audits:
                source_urn = audit.framework.urn
                audit_from_results = engine.load_audit_results(audit)
                summary = engine.summary_results(audit_from_results)
                pretty_summary = self.format_summary_inline(summary)

                print(f"\n📋 Audit: {audit.name}")
                print(f"   🧩 Framework: {source_urn} - [{pretty_summary}]")

                for dest_urn in sorted(frameworks_in_mappings):
                    if dest_urn == source_urn:
                        continue  # skip same framework

                    start_time = time.time()
                    best_results, best_path = engine.best_mapping_results(
                        audit_from_results, source_urn, dest_urn, max_depth
                    )
                    elapsed_ms = (time.time() - start_time) * 1000

                    if best_results:
                        summary = engine.summary_results(best_results)
                        pretty_summary = self.format_summary_inline(summary)
                        print(f"  🔗 to {dest_urn}: [{pretty_summary}]")
                        print(f"     📍 Path: {' ➝ '.join(best_path)}")
                        print(f"     🕒 Time: {elapsed_ms:.2f} ms")
