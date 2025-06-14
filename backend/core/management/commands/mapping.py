from django.core.management.base import BaseCommand
from core.models import StoredLibrary, ComplianceAssessment
from collections import defaultdict, deque
import random
import uuid
import time


NUM_FRAMEWORKS = 1000
NUM_MAPPINGS = 100
NUM_PIVOTS = 10


class Command(BaseCommand):
    help = "Displays mappings with optional test data and pruning"

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Utilise des données de test simulées (1000 frameworks, pivots, etc.)'
        )
        parser.add_argument(
            '--depth',
            type=int,
            default=None,
            help='Profondeur maximale des chemins à explorer (optionnel)'
        )

    def all_paths_from(self, source_urn, max_depth=None):
        """
        Improved BFS:
        - Returns all paths to each node,
        - Only yields paths of the shortest known length to that node.
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
                if neighbor not in shortest_lengths or next_length <= min(shortest_lengths[neighbor]):
                    shortest_lengths[neighbor].add(next_length)
                    queue.append((path + [neighbor], visited | {neighbor}))

        # Retourne tous les chemins retenus (groupés par (source, destination))
        for path_list in paths.values():
            yield from path_list

    def all_paths_between(self, source_urn, dest_urn, max_depth=None):
        """
        Returns all shortest paths from source_urn to dest_urn
        using BFS with pruning logic similar to all_paths_from.
        Only returns paths that end exactly at dest_urn.
        """
        queue = deque()
        queue.append(([source_urn], {source_urn}))
        shortest_lengths = defaultdict(set)
        shortest_lengths[source_urn].add(0)

        found_paths = []
        while queue:
            path, visited = queue.popleft()
            current = path[-1]

            if current == dest_urn:
                found_paths.append(path)
                continue  # do not expand further once destination is reached

            if max_depth and len(path) >= max_depth:
                continue

            for neighbor in self.framework_mappings.get(current, []):
                if neighbor in visited:
                    continue

                next_length = len(path) + 1
                if neighbor not in shortest_lengths or next_length <= min(shortest_lengths[neighbor]):
                    shortest_lengths[neighbor].add(next_length)
                    queue.append((path + [neighbor], visited | {neighbor}))

        return found_paths

    def best_mapping_results(self, source_audit_results, source_urn, dest_urn, max_depth=None):
        paths = self.all_paths_between(source_urn, dest_urn, max_depth)
        results = {}
        best_path = []

        for path in paths:
            tmp_urn = source_urn
            tmp_audit_results = source_audit_results.copy()

            for framework_urn in path:
                if framework_urn == tmp_urn:
                    continue
                rms = self.all_rms.get((tmp_urn, framework_urn))
                if not rms:
                    continue
                tmp_audit_results = self.map_audit_results(tmp_audit_results, rms)
                tmp_urn = framework_urn

            # Keep the most complete result set
            if len(tmp_audit_results) > len(results):
                results = tmp_audit_results
                best_path = path

        return results, best_path


    def load_audit_results(self, audit):
        all_ra = audit.get_requirement_assessments(include_non_assessable=False)
        audit_results = {}
        for ra in all_ra:
            audit_results[ra.requirement.urn] = ra.result
        return audit_results

    def summary_results(self, audit_results):
        res = defaultdict(int)
        for _, result in audit_results.items():
            res[result] += 1
        return dict(res)

    def map_audit_results(self, source_audit_results, rms):
        if not source_audit_results:
            return {}
        target_audit_results = {}
        for mapping in rms['requirement_mappings']:
            src = mapping["source_requirement_urn"]
            dst = mapping["target_requirement_urn"]
            relationship = mapping["relationship"]
            if relationship in ('equal', 'superset'):
                if src in source_audit_results:
                    target_audit_results[dst] = source_audit_results[src]
            elif relationship in ('subset', 'intersect'):
                if src in source_audit_results:
                    r = source_audit_results[src]
                    if r in ('not_assessed', 'non_compliant'):
                        target_audit_results[dst] = r
                    elif r in ('compliant', 'partially_compliant'):
                        target_audit_results[dst] = 'partially_compliant'
        return target_audit_results


    def generate_test_data(self):
        random.seed(42)  # Fixed seed for reproducibility
        all_rms = {}
        non_pivot_frameworks = [f"urn:framework:{i}" for i in range(NUM_FRAMEWORKS - NUM_PIVOTS)]
        pivots = [f"urn:framework:pivot{i}" for i in range(NUM_PIVOTS)]
        frameworks = non_pivot_frameworks + pivots

        # 1. random mappings
        for _ in range(NUM_MAPPINGS):
            source, target = random.sample(non_pivot_frameworks, 2)
            urn = f"urn:rms:{uuid.uuid4()}"
            all_rms[(source, target)] = {
                "urn": urn,
                "library_urn": "urn:library:test",
                "source_framework_urn": source,
                "target_framework_urn": target
            }

        # 2. pivots have mapping to 60% of other frameworks
        for pivot in pivots:
            targets = random.sample(non_pivot_frameworks, int(0.6 * len(non_pivot_frameworks)))
            for target in targets:
                urn = f"urn:rms:{uuid.uuid4()}"
                all_rms[(pivot, target)] = {
                    "urn": urn,
                    "library_urn": "urn:library:test",
                    "source_framework_urn": pivot,
                    "target_framework_urn": target
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
            "not_assessed": "❓"
        }

        ordered_keys = [
            "compliant", "partially_compliant", "non_compliant",
            "not_applicable", "not_assessed"
        ]

        parts = [
            f"{status_labels[k]} {summary.get(k, 0)}"
            for k in ordered_keys if summary.get(k, 0) > 0
        ]

        return " | ".join(parts) if parts else "No results"


    def handle(self, *args, **options):
        test_mode = options.get('test')
        max_depth = options.get('depth')
        self.framework_mappings = defaultdict(list)
        self.all_rms = {} # all rms indexed by (source_urn, dest_urn)

        if test_mode:
            print("🔧 Test mode enabled: generating simulated data...")
            self.all_rms = self.generate_test_data()
            # Build graph from mappings
            start_explore = time.time()
            for (src, tgt), rms in self.all_rms.items():
                self.framework_mappings[src].append(tgt)

            # Collect all paths using optimized exploration
            print("\n🌿 Optimized paths (with dynamic pruning):\n")
            all_paths = []
            for source in self.framework_mappings:
                for path in self.all_paths_from(source, max_depth=max_depth):
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
            start_load = time.time()
            nb_libraries = StoredLibrary.objects.count()
            print(f"📚 Libraries loaded: {nb_libraries}")

            for lib in StoredLibrary.objects.all():
                library_urn = lib.urn
                if isinstance(lib.content, dict):
                    if 'requirement_mapping_set' in lib.content:
                        obj = lib.content['requirement_mapping_set']
                        index = obj['source_framework_urn'], obj['target_framework_urn']
                        self.all_rms[index] = obj
                        self.all_rms[index]['library_urn'] = library_urn
                    if 'requirement_mapping_sets' in lib.content:
                        for obj in lib.content['requirement_mapping_sets']:
                            index = obj['source_framework_urn'], obj['target_framework_urn']
                            self.all_rms[index] = obj
                            self.all_rms[index]['library_urn'] = library_urn

            for (src, tgt), rms in self.all_rms.items():
                self.framework_mappings[src].append(tgt)

            load_duration = time.time() - start_load
            print(f"⏱️ Load time: {load_duration * 1000:.2f} ms")


            # Get all unique frameworks from the mappings
            frameworks_in_mappings = set()
            for src, tgt in self.all_rms.keys():
                frameworks_in_mappings.add(src)
                frameworks_in_mappings.add(tgt)

            audits = list(ComplianceAssessment.objects.all())

            for audit in audits:
                source_urn = audit.framework.urn
                audit_from_results = self.load_audit_results(audit)
                summary = self.summary_results(audit_from_results)
                pretty_summary = self.format_summary_inline(summary)

                print(f"\n📋 Audit: {audit.name}")
                print(f"   🧩 Framework: {source_urn} - [{pretty_summary}]")

                for dest_urn in sorted(frameworks_in_mappings):
                    if dest_urn == source_urn:
                        continue  # skip same framework

                    start_time = time.time()
                    best_results, best_path = self.best_mapping_results(
                        audit_from_results, source_urn, dest_urn, max_depth
                    )
                    elapsed_ms = (time.time() - start_time) * 1000

                    if best_results:
                        summary = self.summary_results(best_results)
                        pretty_summary = self.format_summary_inline(summary)
                        print(f"  🔗 to {dest_urn}: [{pretty_summary}]")
                        print(f"     📍 Path: {' ➝ '.join(best_path)}")
                        print(f"     ⏱️ Time: {elapsed_ms:.2f} ms")
