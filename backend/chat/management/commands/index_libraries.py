"""
Management command to index all YAML framework libraries into the RAG knowledge base.
This creates a shared knowledge partition accessible to all authenticated users.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Index all YAML framework libraries into the RAG knowledge base"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run synchronously instead of queuing as a background task",
        )

    def handle(self, *args, **options):
        from chat.tasks import index_library_knowledge_base

        if options["sync"]:
            self.stdout.write("Indexing libraries synchronously...")
            # Call the function directly (not as a Huey task)
            index_library_knowledge_base.call_local()
            self.stdout.write(self.style.SUCCESS("Library indexing complete."))
        else:
            self.stdout.write("Queuing library indexing as background task...")
            index_library_knowledge_base()
            self.stdout.write(
                self.style.SUCCESS(
                    "Library indexing task queued. Check logs for progress."
                )
            )
