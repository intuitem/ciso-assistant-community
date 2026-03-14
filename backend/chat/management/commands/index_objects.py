"""
Management command to bulk-index existing model objects into Qdrant for chat RAG.
"""

import uuid

from django.apps import apps
from django.core.management.base import BaseCommand

from chat.rag import COLLECTION_NAME, get_qdrant_client
from chat.signals import INDEXED_MODELS
from chat.tasks import _build_object_text, _normalize_model_name


class Command(BaseCommand):
    help = "Bulk-index existing model objects into Qdrant for chat RAG"

    def add_arguments(self, parser):
        parser.add_argument(
            "--models",
            nargs="*",
            help="Specific models to index (e.g. core.AppliedControl). Defaults to all indexed models.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of objects to embed and upsert per batch (default: 100)",
        )

    def handle(self, *args, **options):
        from qdrant_client.models import PointStruct

        from chat.providers import get_embedder

        models_to_index = options["models"] or INDEXED_MODELS
        batch_size = options["batch_size"]

        # Verify collection exists
        client = get_qdrant_client()
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self.stderr.write(
                self.style.ERROR(
                    f"Collection '{COLLECTION_NAME}' does not exist. Run 'init_qdrant' first."
                )
            )
            return

        embedder = get_embedder()
        total_indexed = 0

        for model_path in models_to_index:
            app_label, model_name = model_path.split(".")
            try:
                model_class = apps.get_model(app_label, model_name)
            except LookupError:
                self.stderr.write(
                    self.style.WARNING(f"Model {model_path} not found, skipping")
                )
                continue

            queryset = model_class.objects.all()
            count = queryset.count()
            self.stdout.write(f"Indexing {count} {model_path} objects...")

            batch_texts = []
            batch_objects = []

            for obj in queryset.iterator():
                text = _build_object_text(obj, model_name)
                folder_id = str(getattr(obj, "folder_id", ""))
                if not text or not folder_id:
                    continue

                batch_texts.append(text)
                batch_objects.append((obj, text, folder_id))

                if len(batch_texts) >= batch_size:
                    total_indexed += self._flush_batch(
                        client,
                        embedder,
                        batch_objects,
                        batch_texts,
                        app_label,
                        model_name,
                    )
                    batch_texts = []
                    batch_objects = []

            # Flush remaining
            if batch_texts:
                total_indexed += self._flush_batch(
                    client, embedder, batch_objects, batch_texts, app_label, model_name
                )

            self.stdout.write(f"  Done: {model_path}")

        self.stdout.write(self.style.SUCCESS(f"Indexed {total_indexed} objects total."))

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
