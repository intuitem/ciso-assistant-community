from django.core.management.base import BaseCommand

from chat.signals import index_missing_documents


class Command(BaseCommand):
    help = (
        "Queue evidence attachments and published documents that are missing "
        "from the chat index."
    )

    def add_arguments(self, parser):
        parser.add_argument("--folder", help="Restrict to this folder UUID.")

    def handle(self, *args, **options):
        evidence, documents = index_missing_documents(options["folder"])
        self.stdout.write(
            f"Checked {evidence} evidence revisions and {documents} published documents."
        )
