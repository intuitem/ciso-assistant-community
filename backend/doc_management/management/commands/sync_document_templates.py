from pathlib import Path

from django.core.management.base import BaseCommand

from doc_management.models import DocumentTemplate
from doc_management.template_import import parse_template_markdown
from iam.models import Folder

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "library" / "policy_templates"


class Command(BaseCommand):
    help = (
        "Sync built-in document templates from the filesystem into the DB (idempotent)."
    )

    def handle(self, *args, **options):
        root = Folder.get_root_folder()
        count = 0
        for locale_dir in sorted(TEMPLATES_DIR.glob("*")):
            if not locale_dir.is_dir():
                continue
            locale = locale_dir.name
            for f in sorted(locale_dir.glob("*.md")):
                # A custom template shares the (ref_id, locale) unique key; don't
                # let the built-in sync overwrite it and flip it to builtin.
                existing = DocumentTemplate.objects.filter(
                    ref_id=f.stem, locale=locale
                ).first()
                if existing and not existing.builtin:
                    continue
                data = parse_template_markdown(f.read_text(encoding="utf-8"), f.stem)
                data.pop("ref_id")
                data.pop(
                    "locale", None
                )  # locale comes from the directory, not the file
                DocumentTemplate.objects.update_or_create(
                    ref_id=f.stem,
                    locale=locale,
                    defaults={
                        **data,
                        "builtin": True,
                        "folder": root,
                        "default_locale": locale == "en",
                    },
                )
                count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Synced {count} built-in document templates.")
        )
