#!/usr/bin/env python3
"""
Demo script showing the RAG POC in action.
Run this after installing dependencies and indexing frameworks.

Usage:
    # First time setup
    pip install -r requirements.txt
    python index.py --max 10  # Index 10 frameworks for quick demo

    # Run demo
    python demo.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

DEMO_QUERIES = [
    "What are the requirements for access control in ISO 27001?",
    "How should I handle encryption of data at rest?",
    "What does NIST CSF say about incident response?",
    "What are the requirements for third-party risk management?",
    "How should I implement logging and monitoring?",
]


def main():
    console.print(
        Panel.fit(
            "[bold green]CISO Assistant RAG Demo[/bold green]\n\n"
            "This demo shows retrieval-augmented generation over security frameworks.",
            border_style="green",
        )
    )

    # Check prerequisites
    try:
        import config

        client = config.get_qdrant_client()
        collections = [c.name for c in client.get_collections().collections]

        if config.COLLECTION_NAME not in collections:
            console.print("[red]Index not found. Creating demo index...[/red]")
            console.print("[dim]Running: python index.py --max 10[/dim]\n")
            import subprocess

            subprocess.run(["python", "index.py", "--max", "10", "--recreate"])
            console.print()
        else:
            info = client.get_collection(config.COLLECTION_NAME)
            console.print(
                f"[green]✓ Index ready ({info.points_count} documents)[/green]\n"
            )
    except ImportError as e:
        console.print(f"[red]Missing dependency: {e}[/red]")
        console.print("[dim]Run: pip install -r requirements.txt[/dim]")
        return
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    # Check Ollama
    from providers import is_ollama_available

    if is_ollama_available():
        console.print("[green]✓ Ollama available - full RAG mode[/green]\n")
    else:
        console.print("[yellow]○ Ollama not available - retrieval only mode[/yellow]")
        console.print(
            "[dim]Install Ollama for full RAG: https://ollama.ai/download[/dim]\n"
        )

    # Run demo queries
    from query import query_rag

    for i, question in enumerate(DEMO_QUERIES, 1):
        console.print(f"\n[bold cyan]Demo Query {i}/{len(DEMO_QUERIES)}:[/bold cyan]")
        console.print(f"[italic]{question}[/italic]\n")

        try:
            query_rag(
                question,
                top_k=3,
                retrieval_only=not is_ollama_available(),
                show_sources=True,
            )
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

        console.print("\n" + "─" * 80)

        # Pause between queries
        if i < len(DEMO_QUERIES):
            try:
                console.input(
                    "[dim]Press Enter for next query (Ctrl+C to stop)...[/dim]"
                )
            except KeyboardInterrupt:
                console.print("\n[dim]Demo stopped[/dim]")
                break

    console.print("\n[green bold]Demo complete![/green bold]")
    console.print("[dim]Try interactive mode: python query.py --interactive[/dim]")


if __name__ == "__main__":
    main()
