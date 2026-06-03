"""Walk Qdrant model points and delete any whose object_id is no longer in the DB.

Companion to ``index_objects`` — that command upserts; this one cleans up.
Useful after bulk deletes (e.g. dropping a framework or wiping a folder)
where signals weren't connected and the index drifted.

Usage:
    # Across all folders, default safety: dry-run shows what would go
    python manage.py prune_index --dry-run

    # Actually delete
    python manage.py prune_index

    # Scope to one folder
    python manage.py prune_index --folder <uuid>
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from chat.rag import COLLECTION_NAME, get_qdrant_client
from chat.signals import INDEXED_MODELS


class Command(BaseCommand):
    help = "Drop Qdrant model points whose underlying DB object no longer exists."

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            help="Restrict the prune to points scoped to this folder UUID.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without contacting Qdrant.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Scroll page size when walking Qdrant (default: 500).",
        )

    def handle(self, *args, **options):
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
        )

        folder_filter = options.get("folder")
        dry_run = options.get("dry_run", False)
        batch_size = options["batch_size"]

        client = get_qdrant_client()
        try:
            collections = [c.name for c in client.get_collections().collections]
        except Exception as e:
            raise CommandError(f"Qdrant unreachable: {e}")
        if COLLECTION_NAME not in collections:
            raise CommandError(
                f"Collection '{COLLECTION_NAME}' does not exist. "
                "Run 'init_qdrant' first."
            )

        # Build the live (object_type, object_id) set across every indexed
        # model (optionally folder-scoped). Keying by tuple — not by id alone
        # — guarantees we don't false-detect a stale point because some other
        # model happened to share the same UUID (vanishingly rare, but cheap
        # to do right).
        live_keys: set[tuple[str, str]] = set()
        from chat.text import _normalize_model_name

        for model_path in INDEXED_MODELS:
            try:
                app_label, model_name = model_path.split(".")
                model_class = apps.get_model(app_label, model_name)
            except (LookupError, ValueError):
                continue
            object_type = _normalize_model_name(model_name)
            try:
                qs = model_class.objects.all()
                if folder_filter:
                    qs = qs.filter(folder_id=folder_filter)
                for obj_id in qs.values_list("id", flat=True).iterator():
                    live_keys.add((object_type, str(obj_id)))
            except Exception as e:
                # Don't continue with an incomplete live set — proceeding would
                # treat live rows from this model as stale and delete their
                # points. Bail loudly so the operator can investigate.
                raise CommandError(
                    f"Cannot build live-id set: query for {model_path} "
                    f"failed ({e}). Aborting before any delete."
                )

        # Walk every model point in Qdrant (optionally folder-scoped).
        must_clauses = [
            FieldCondition(key="source_type", match=MatchValue(value="model")),
        ]
        if folder_filter:
            must_clauses.insert(
                0,
                FieldCondition(key="folder_id", match=MatchValue(value=folder_filter)),
            )
        scroll_filter = Filter(must=must_clauses)

        next_offset = None
        stale_point_ids: list = []
        scanned = 0
        while True:
            try:
                batch, next_offset = client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=scroll_filter,
                    limit=batch_size,
                    offset=next_offset,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception as e:
                raise CommandError(f"Qdrant scroll failed: {e}")
            for p in batch or []:
                scanned += 1
                payload = getattr(p, "payload", {}) or {}
                obj_id = payload.get("object_id")
                object_type = payload.get("object_type") or ""
                if obj_id and (object_type, str(obj_id)) not in live_keys:
                    stale_point_ids.append(p.id)
            if not next_offset:
                break

        scope = f"folder={folder_filter}" if folder_filter else "all folders"
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] {scope} — scanned {scanned} model points, "
                    f"{len(stale_point_ids)} are stale and would be deleted."
                )
            )
            return

        if not stale_point_ids:
            self.stdout.write(
                f"{scope} — scanned {scanned} model points, nothing stale."
            )
            return

        try:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=stale_point_ids,
            )
        except Exception as e:
            raise CommandError(f"Qdrant delete failed: {e}")
        self.stdout.write(
            self.style.SUCCESS(
                f"{scope} — scanned {scanned} model points, "
                f"deleted {len(stale_point_ids)} stale."
            )
        )
