from django.core.management.base import BaseCommand
from core.mappings.engine import engine
from core.models import StoredLibrary, ComplianceAssessment
import random
import uuid
import time
from typing import Dict, Tuple
import json
import zlib

from core.utils import sizeof_json

NUM_FRAMEWORKS = 1000
NUM_MAPPINGS = 100
NUM_PIVOTS = 10


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

    def generate_test_data(self) -> Dict[Tuple[str, str], bytes]:
        random.seed(42)  # Fixed seed for reproducibility
        all_rms: Dict[Tuple[str, str], bytes] = {}
        non_pivot_frameworks = [
            f"urn:framework:{i}" for i in range(NUM_FRAMEWORKS - NUM_PIVOTS)
        ]
        pivots = [f"urn:framework:pivot{i}" for i in range(NUM_PIVOTS)]

        # 1. random mappings
        for _ in range(NUM_MAPPINGS):
            source, target = random.sample(non_pivot_frameworks, 2)
            urn = f"urn:rms:{uuid.uuid4()}"
            obj = {
                "urn": urn,
                "library_urn": "urn:library:test",
                "source_framework_urn": source,
                "target_framework_urn": target,
            }
            all_rms[(source, target)] = zlib.compress(
                json.dumps(obj, separators=(",", ":")).encode("utf-8")
            )

        # 2. pivots have mapping to 60% of other frameworks
        for pivot in pivots:
            targets = random.sample(
                non_pivot_frameworks, int(0.6 * len(non_pivot_frameworks))
            )
            for target in targets:
                urn = f"urn:rms:{uuid.uuid4()}"
                obj = {
                    "urn": urn,
                    "library_urn": "urn:library:test",
                    "source_framework_urn": pivot,
                    "target_framework_urn": target,
                }
                all_rms[(pivot, target)] = zlib.compress(
                    json.dumps(obj, separators=(",", ":")).encode("utf-8")
                )

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
            nb_libraries = StoredLibrary.objects.count()
            print(f"📚 Loaded {nb_libraries} libraries from the database.")

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
                audit_from_results = engine.load_audit_fields(audit)
                summary = engine.summary_results(audit_from_results)
                pretty_summary = self.format_summary_inline(summary)

                print(f"\n📋 Audit: {audit.name}")
                print(f"   🧩 Framework: {source_urn} - [{pretty_summary}]")

                for dest_urn in sorted(frameworks_in_mappings):
                    if dest_urn == source_urn:
                        continue  # skip same framework

                    start_time = time.time()
                    best_results, best_path = engine.best_mapping_inferences(
                        audit_from_results, source_urn, dest_urn, max_depth
                    )
                    elapsed_ms = (time.time() - start_time) * 1000

                    if best_results:
                        summary = engine.summary_results(best_results)
                        pretty_summary = self.format_summary_inline(summary)
                        print(f"  🔗 to {dest_urn}: [{pretty_summary}]")
                        print(f"     📍 Path: {' ➝ '.join(best_path)}")
                        print(f"     🕒 Time: {elapsed_ms:.2f} ms")
