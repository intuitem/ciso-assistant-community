from django.core.management.base import BaseCommand

from chat.signals import index_document_revision, index_evidence_revision
from core.models import EvidenceRevision
from doc_management.models import DocumentRevision


class Command(BaseCommand):
    help = (
        "Queue evidence attachments and published documents that are missing "
        "from the chat index."
    )

    def add_arguments(self, parser):
        parser.add_argument("--folder", help="Restrict to this folder UUID.")

    def handle(self, *args, **options):
        evidence = EvidenceRevision.objects.exclude(attachment="").exclude(
            attachment__isnull=True
        )
        documents = DocumentRevision.objects.filter(
            status=DocumentRevision.Status.PUBLISHED
        )
        if options["folder"]:
            evidence = evidence.filter(folder_id=options["folder"])
            documents = documents.filter(folder_id=options["folder"])
        for revision in evidence.iterator():
            index_evidence_revision(revision)
        for revision in documents.iterator():
            index_document_revision(revision)
        self.stdout.write(
            f"Checked {evidence.count()} evidence revisions and "
            f"{documents.count()} published documents."
        )
