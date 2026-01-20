#!/usr/bin/env python3
"""
Index security framework YAML files into Qdrant for RAG.

Usage:
    python index.py                    # Index all frameworks
    python index.py --max 5            # Index only 5 frameworks (for testing)
    python index.py --frameworks nist-csf-2.0.yaml iso27001-2022.yaml
"""

import argparse
import uuid
from pathlib import Path

import yaml
from qdrant_client.models import Distance, VectorParams, PointStruct
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

import config
from providers import get_embedder

console = Console()


def parse_framework(yaml_path: Path) -> list[dict]:
    """Parse a framework YAML file and extract indexable documents."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    documents = []

    # Extract library metadata
    library_name = data.get("name", yaml_path.stem)
    library_urn = data.get("urn", "")
    library_provider = data.get("provider", "")
    library_description = data.get("description", "")

    # Index library-level document
    documents.append(
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, library_urn or yaml_path.name)),
            "text": f"Framework: {library_name}\nProvider: {library_provider}\nDescription: {library_description}",
            "metadata": {
                "type": "framework",
                "framework": library_name,
                "urn": library_urn,
                "provider": library_provider,
                "source_file": yaml_path.name,
            },
        }
    )

    # Extract framework requirements
    objects = data.get("objects", {})
    framework = objects.get("framework", {})
    requirement_nodes = framework.get("requirement_nodes", [])

    # Build parent name lookup for context
    parent_names = {}
    for node in requirement_nodes:
        urn = node.get("urn", "")
        ref_id = node.get("ref_id", "")
        name = node.get("name", "")
        if urn:
            parent_names[urn] = f"{ref_id} {name}".strip()

    # Index each requirement node
    for node in requirement_nodes:
        # Skip non-assessable nodes (they're just categories)
        if not node.get("assessable", False):
            continue

        urn = node.get("urn", "")
        ref_id = node.get("ref_id", "")
        name = node.get("name", "")
        description = node.get("description", "")
        annotation = node.get("annotation", "")
        parent_urn = node.get("parent_urn", "")

        # Get parent context
        parent_context = parent_names.get(parent_urn, "")

        # Build searchable text
        text_parts = [
            f"Framework: {library_name}",
            f"Requirement ID: {ref_id}",
        ]
        if parent_context:
            text_parts.append(f"Category: {parent_context}")
        if name:
            text_parts.append(f"Name: {name}")
        if description:
            text_parts.append(f"Description: {description}")
        if annotation:
            text_parts.append(f"Implementation Guidance: {annotation}")

        text = "\n".join(text_parts)

        documents.append(
            {
                "id": str(
                    uuid.uuid5(uuid.NAMESPACE_URL, urn or f"{yaml_path.name}:{ref_id}")
                ),
                "text": text,
                "metadata": {
                    "type": "requirement",
                    "framework": library_name,
                    "framework_urn": library_urn,
                    "urn": urn,
                    "ref_id": ref_id,
                    "name": name,
                    "parent": parent_context,
                    "source_file": yaml_path.name,
                },
            }
        )

    # Also index threats if present
    threats = objects.get("threats", [])
    for threat in threats:
        urn = threat.get("urn", "")
        ref_id = threat.get("ref_id", "")
        name = threat.get("name", "")
        description = threat.get("description", "")
        provider = threat.get("provider", library_provider)

        text = f"Threat: {name}\nProvider: {provider}\nRef ID: {ref_id}\nDescription: {description}"

        documents.append(
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, urn or f"threat:{ref_id}")),
                "text": text,
                "metadata": {
                    "type": "threat",
                    "provider": provider,
                    "urn": urn,
                    "ref_id": ref_id,
                    "name": name,
                    "source_file": yaml_path.name,
                },
            }
        )

    return documents


def index_frameworks(
    framework_files: list[Path] | None = None,
    max_frameworks: int = 0,
    recreate: bool = False,
):
    """Index framework files into Qdrant."""

    # Initialize Qdrant client (local/embedded mode)
    console.print(f"[blue]Initializing Qdrant at {config.QDRANT_PATH}[/blue]")
    client = config.get_qdrant_client()

    # Initialize embedder
    console.print("[blue]Loading embedder...[/blue]")
    embedder = get_embedder()
    console.print(
        f"[green]Using embedder with {embedder.dimensions} dimensions[/green]"
    )

    # Create or recreate collection
    collections = [c.name for c in client.get_collections().collections]

    if config.COLLECTION_NAME in collections:
        if recreate:
            console.print(
                f"[yellow]Recreating collection '{config.COLLECTION_NAME}'[/yellow]"
            )
            client.delete_collection(config.COLLECTION_NAME)
        else:
            console.print(
                f"[yellow]Collection '{config.COLLECTION_NAME}' exists. Use --recreate to rebuild.[/yellow]"
            )
            info = client.get_collection(config.COLLECTION_NAME)
            console.print(f"[dim]Current points: {info.points_count}[/dim]")
            return

    client.create_collection(
        collection_name=config.COLLECTION_NAME,
        vectors_config=VectorParams(size=embedder.dimensions, distance=Distance.COSINE),
    )

    # Discover framework files
    if framework_files:
        yaml_files = [config.LIBRARY_DIR / f for f in framework_files]
    else:
        yaml_files = sorted(config.LIBRARY_DIR.glob("*.yaml"))

    if max_frameworks > 0:
        yaml_files = yaml_files[:max_frameworks]

    console.print(f"[blue]Found {len(yaml_files)} framework files to index[/blue]")

    # Parse all frameworks
    all_documents = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing frameworks...", total=len(yaml_files))

        for yaml_file in yaml_files:
            try:
                docs = parse_framework(yaml_file)
                all_documents.extend(docs)
                progress.update(task, advance=1, description=f"Parsed {yaml_file.name}")
            except Exception as e:
                console.print(f"[red]Error parsing {yaml_file.name}: {e}[/red]")
                progress.update(task, advance=1)

    console.print(f"[green]Extracted {len(all_documents)} documents[/green]")

    # Embed and index in batches
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding & indexing...", total=len(all_documents))

        for i in range(0, len(all_documents), config.BATCH_SIZE):
            batch = all_documents[i : i + config.BATCH_SIZE]
            texts = [doc["text"] for doc in batch]

            # Embed batch
            embeddings = embedder.embed(texts)

            # Create points
            points = [
                PointStruct(
                    id=doc["id"],
                    vector=embedding,
                    payload={"text": doc["text"], **doc["metadata"]},
                )
                for doc, embedding in zip(batch, embeddings)
            ]

            # Upsert to Qdrant
            client.upsert(collection_name=config.COLLECTION_NAME, points=points)
            progress.update(task, advance=len(batch))

    # Final stats
    info = client.get_collection(config.COLLECTION_NAME)
    console.print(f"\n[green bold]Indexing complete![/green bold]")
    console.print(f"[dim]Total documents: {info.points_count}[/dim]")


def main():
    parser = argparse.ArgumentParser(description="Index security frameworks for RAG")
    parser.add_argument(
        "--max", type=int, default=0, help="Max frameworks to index (0=all)"
    )
    parser.add_argument(
        "--recreate", action="store_true", help="Recreate collection from scratch"
    )
    parser.add_argument(
        "--frameworks", nargs="+", help="Specific framework files to index"
    )
    args = parser.parse_args()

    index_frameworks(
        framework_files=args.frameworks, max_frameworks=args.max, recreate=args.recreate
    )


if __name__ == "__main__":
    main()
