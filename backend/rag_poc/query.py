#!/usr/bin/env python3
"""
Query the indexed security frameworks using RAG.

Usage:
    python query.py "What are the requirements for access control?"
    python query.py --interactive
    python query.py --retrieval-only "encryption requirements"
"""

import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

import config
from providers import get_embedder, get_llm, is_ollama_available

console = Console()


def search(
    query: str, top_k: int = config.TOP_K, type_filter: str | None = None
) -> list[dict]:
    """Search for relevant documents."""
    client = config.get_qdrant_client()
    embedder = get_embedder()

    # Embed query
    query_vector = embedder.embed_query(query)

    # Build filter
    filter_conditions = None
    if type_filter:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        filter_conditions = Filter(
            must=[FieldCondition(key="type", match=MatchValue(value=type_filter))]
        )

    # Search (using query_points for newer qdrant-client API)
    results = client.query_points(
        collection_name=config.COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        query_filter=filter_conditions,
    )

    return [
        {
            "id": r.id,
            "score": r.score,
            "text": r.payload.get("text", ""),
            "type": r.payload.get("type", ""),
            "framework": r.payload.get("framework", ""),
            "ref_id": r.payload.get("ref_id", ""),
            "name": r.payload.get("name", ""),
        }
        for r in results.points
    ]


def format_context(results: list[dict]) -> str:
    """Format search results as context for LLM."""
    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(
            f"[Source {i}: {r['framework']} - {r['ref_id']}]\n{r['text']}"
        )
    return "\n\n---\n\n".join(context_parts)


def display_results(results: list[dict]):
    """Display search results in a table."""
    table = Table(title="Retrieved Documents", show_lines=True)
    table.add_column("Score", style="cyan", width=6)
    table.add_column("Framework", style="green", width=20)
    table.add_column("Ref ID", style="yellow", width=15)
    table.add_column("Type", style="blue", width=12)
    table.add_column("Preview", style="dim", width=60)

    for r in results:
        preview = r["text"][:100].replace("\n", " ") + "..."
        table.add_row(
            f"{r['score']:.3f}",
            r["framework"][:20],
            r["ref_id"] or "-",
            r["type"],
            preview,
        )

    console.print(table)


def query_rag(
    question: str,
    top_k: int = config.TOP_K,
    retrieval_only: bool = False,
    show_sources: bool = True,
):
    """Run a RAG query."""

    # Search for relevant documents
    console.print(f"\n[dim]Searching for relevant documents...[/dim]")
    results = search(question, top_k=top_k)

    if not results:
        console.print("[yellow]No relevant documents found.[/yellow]")
        return

    if show_sources:
        display_results(results)

    # Build context
    context = format_context(results)

    if retrieval_only:
        console.print("\n[bold]Retrieved Context:[/bold]")
        console.print(Panel(context, title="Context", border_style="blue"))
        return

    # Generate response with LLM
    console.print(f"\n[dim]Generating response...[/dim]\n")
    llm = get_llm()

    console.print(Panel.fit("[bold]Answer[/bold]", border_style="green"))

    # Stream response
    response_text = ""
    for token in llm.stream(question, context):
        console.print(token, end="")
        response_text += token
    console.print("\n")

    # Show sources
    if show_sources:
        console.print("\n[dim]Sources:[/dim]")
        for r in results:
            if r["ref_id"]:
                console.print(f"  [cyan]•[/cyan] {r['framework']} - {r['ref_id']}")


def interactive_mode():
    """Run in interactive mode."""
    console.print(
        Panel.fit(
            "[bold green]CISO Assistant RAG POC[/bold green]\n"
            "Ask questions about security frameworks.\n"
            "Commands: /quit, /sources, /retrieval",
            border_style="green",
        )
    )

    ollama_status = (
        "[green]✓ Ollama available[/green]"
        if is_ollama_available()
        else "[yellow]○ Retrieval only[/yellow]"
    )
    console.print(f"Status: {ollama_status}\n")

    show_sources = True
    retrieval_only = not is_ollama_available()

    while True:
        try:
            question = console.input("[bold cyan]Question:[/bold cyan] ").strip()

            if not question:
                continue

            if question.lower() in ("/quit", "/exit", "/q"):
                break

            if question.lower() == "/sources":
                show_sources = not show_sources
                console.print(f"[dim]Show sources: {show_sources}[/dim]")
                continue

            if question.lower() == "/retrieval":
                retrieval_only = not retrieval_only
                console.print(f"[dim]Retrieval only: {retrieval_only}[/dim]")
                continue

            query_rag(
                question, retrieval_only=retrieval_only, show_sources=show_sources
            )

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted[/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(description="Query security frameworks using RAG")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )
    parser.add_argument(
        "--retrieval-only",
        "-r",
        action="store_true",
        help="Only retrieve, don't generate",
    )
    parser.add_argument(
        "--top-k", "-k", type=int, default=config.TOP_K, help="Number of results"
    )
    parser.add_argument("--no-sources", action="store_true", help="Don't show sources")
    args = parser.parse_args()

    # Check if collection exists
    try:
        client = config.get_qdrant_client()
        collections = [c.name for c in client.get_collections().collections]
        if config.COLLECTION_NAME not in collections:
            console.print(
                "[red]Collection not found. Run 'python index.py' first.[/red]"
            )
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error connecting to Qdrant: {e}[/red]")
        console.print("[dim]Run 'python index.py' first to create the index.[/dim]")
        sys.exit(1)

    if args.interactive:
        interactive_mode()
    elif args.question:
        query_rag(
            args.question,
            top_k=args.top_k,
            retrieval_only=args.retrieval_only,
            show_sources=not args.no_sources,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
