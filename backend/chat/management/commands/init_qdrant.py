"""
Management command to initialize the Qdrant collection for chat RAG.
Creates the collection with proper vector dimensions and payload indexes.
"""

from django.core.management.base import BaseCommand

from chat.rag import COLLECTION_NAME, get_qdrant_client


class Command(BaseCommand):
    help = "Initialize the Qdrant collection for chat RAG indexing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Drop and recreate the collection if it already exists",
        )

    def handle(self, *args, **options):
        from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

        from chat.providers import get_embedder

        client = get_qdrant_client()

        # Check if collection exists
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME in collections:
            if options["recreate"]:
                self.stdout.write(
                    f"Dropping existing collection '{COLLECTION_NAME}'..."
                )
                client.delete_collection(COLLECTION_NAME)
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Collection '{COLLECTION_NAME}' already exists. Use --recreate to drop and recreate."
                    )
                )
                return

        # Get embedding dimensions from the configured embedder
        self.stdout.write("Detecting embedding dimensions...")
        embedder = get_embedder()
        dimensions = embedder.dimensions
        self.stdout.write(f"Embedding dimensions: {dimensions}")

        # Create collection
        self.stdout.write(f"Creating collection '{COLLECTION_NAME}'...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=dimensions,
                distance=Distance.COSINE,
            ),
        )

        # Create payload indexes for efficient filtering
        self.stdout.write("Creating payload indexes...")
        indexes = {
            "folder_id": PayloadSchemaType.KEYWORD,
            "source_type": PayloadSchemaType.KEYWORD,
            "object_type": PayloadSchemaType.KEYWORD,
            "object_id": PayloadSchemaType.KEYWORD,
        }
        for field, schema_type in indexes.items():
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=schema_type,
            )
            self.stdout.write(f"  - {field}: {schema_type.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Collection '{COLLECTION_NAME}' created with {dimensions}-dim vectors and payload indexes."
            )
        )
