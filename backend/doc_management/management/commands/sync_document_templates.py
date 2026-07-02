from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

from doc_management.models import DocumentContainer, DocumentTemplate
from iam.models import Folder

VALID_DOCUMENT_TYPES = {c[0] for c in DocumentContainer.DocumentType.choices}

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
                raw = f.read_text(encoding="utf-8")
                title = f.stem.replace("_", " ").title()
                description = ""
                document_type = DocumentContainer.DocumentType.POLICY
                content = raw
                if raw.startswith("---"):
                    parts = raw.split("---", 2)
                    if len(parts) >= 3:
                        try:
                            fm = yaml.safe_load(parts[1]) or {}
                            title = fm.get("title", title)
                            description = fm.get("description", "")
                            dt = fm.get("document_type")
                            if dt in VALID_DOCUMENT_TYPES:
                                document_type = dt
                        except yaml.YAMLError:
                            pass
                        content = parts[2].strip()
                DocumentTemplate.objects.update_or_create(
                    ref_id=f.stem,
                    locale=locale,
                    defaults={
                        "name": title,
                        "description": description,
                        "document_type": document_type,
                        "content": content,
                        "builtin": True,
                        "folder": root,
                        "default_locale": locale == "en",
                    },
                )
                count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Synced {count} built-in document templates.")
        )
