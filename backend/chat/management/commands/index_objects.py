"""
Management command to bulk-index existing model objects into Qdrant for chat RAG.

Re-runnable; safe to invoke against a populated index — Qdrant upsert replaces
points by id. Useful to:
  - Backfill the index for a folder after enabling chat for the first time.
  - Refresh the index after extending `_build_object_text` with new fields.
  - Index a single folder ahead of running questionnaire-autopilot on it.
"""

import uuid

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from chat.rag import COLLECTION_NAME, get_qdrant_client
from chat.signals import INDEXED_MODELS
from chat.tasks import _resolve_folder_id
from chat.text import _build_object_text, _normalize_model_name


class Command(BaseCommand):
    help = (
        "Bulk-index existing model objects into Qdrant for chat / agentic RAG. "
        "Restrict with --folder to scope to one folder."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--models",
            nargs="*",
            help="Specific models to index (e.g. core.AppliedControl). "
            "Defaults to all indexed models.",
        )
        parser.add_argument(
            "--folder",
            help="UUID of a folder. Restricts indexing to objects whose resolved "
            "folder is this one. Without this flag, every object is indexed.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of objects to embed and upsert per batch (default: 100)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be indexed without contacting Qdrant or the embedder.",
        )

    def handle(self, *args, **options):
        models_to_index = options["models"] or INDEXED_MODELS
        batch_size = options["batch_size"]
        folder_filter = options.get("folder")
        dry_run = options.get("dry_run", False)

        client = None
        embedder = None
        if not dry_run:
            client = get_qdrant_client()
            collections = [c.name for c in client.get_collections().collections]
            if COLLECTION_NAME not in collections:
                raise CommandError(
                    f"Collection '{COLLECTION_NAME}' does not exist. "
                    "Run 'init_qdrant' first."
                )
            from chat.providers import get_embedder

            embedder = get_embedder()

        scope_label = f"folder={folder_filter}" if folder_filter else "all folders"
        mode_label = "[dry-run] " if dry_run else ""
        self.stdout.write(f"{mode_label}Indexing scope: {scope_label}")

        grand_total_indexed = 0
        grand_total_skipped = 0

        for model_path in models_to_index:
            try:
                app_label, model_name = model_path.split(".")
            except ValueError:
                self.stderr.write(
                    self.style.WARNING(f"Bad model path '{model_path}', skipping")
                )
                continue
            try:
                model_class = apps.get_model(app_label, model_name)
            except LookupError:
                self.stderr.write(
                    self.style.WARNING(f"Model {model_path} not found, skipping")
                )
                continue

            queryset = model_class.objects.all()
            total = queryset.count()
            indexed = 0
            skipped = 0

            self.stdout.write(f"  {model_path}: scanning {total} object(s)…")

            batch_texts: list[str] = []
            batch_objects: list = []

            for obj in queryset.iterator():
                folder_id = _resolve_folder_id(obj)
                if not folder_id:
                    skipped += 1
                    continue
                if folder_filter and folder_id != folder_filter:
                    continue

                text = _build_object_text(obj, model_name)
                if not text:
                    skipped += 1
                    continue

                batch_texts.append(text)
                batch_objects.append((obj, text, folder_id))

                if len(batch_texts) >= batch_size:
                    if not dry_run:
                        indexed += self._flush_batch(
                            client,
                            embedder,
                            batch_objects,
                            batch_texts,
                            app_label,
                            model_name,
                        )
                    else:
                        indexed += len(batch_texts)
                    batch_texts = []
                    batch_objects = []

            if batch_texts:
                if not dry_run:
                    indexed += self._flush_batch(
                        client,
                        embedder,
                        batch_objects,
                        batch_texts,
                        app_label,
                        model_name,
                    )
                else:
                    indexed += len(batch_texts)

            grand_total_indexed += indexed
            grand_total_skipped += skipped
            self.stdout.write(
                f"  {model_path}: indexed {indexed}, skipped {skipped}"
                + (" [dry-run]" if dry_run else "")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"{mode_label}Done — indexed {grand_total_indexed}, "
                f"skipped {grand_total_skipped}."
            )
        )

    def _flush_batch(
        self, client, embedder, batch_objects, batch_texts, app_label, model_name
    ):
        from qdrant_client.models import PointStruct

        embeddings = embedder.embed(batch_texts)
        points = []

        for (obj, text, folder_id), vector in zip(batch_objects, embeddings):
            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{app_label}.{model_name}:{obj.id}",
                )
            )
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": text,
                        "folder_id": folder_id,
                        "source_type": "model",
                        "object_type": _normalize_model_name(model_name),
                        "object_id": str(obj.id),
                        "name": str(obj),
                        "ref_id": getattr(obj, "ref_id", "") or "",
                    },
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        return len(points)
