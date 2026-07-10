"""Shared parsing/import logic for markdown document templates.

Used by both the ``sync_document_templates`` management command (filesystem →
DB) and the DocumentTemplate ``import`` API action (user-uploaded .zip → DB).
"""

import zipfile
from pathlib import Path

import yaml

from doc_management.models import DocumentContainer, DocumentTemplate

VALID_DOCUMENT_TYPES = {c[0] for c in DocumentContainer.DocumentType.choices}

# Bound the import so a permissioned user can't exhaust memory with a zip bomb.
MAX_TEMPLATE_FILES = 1000
MAX_TEMPLATE_BYTES = 10 * 1024 * 1024
MAX_TEMPLATE_TOTAL_BYTES = 50 * 1024 * 1024


def parse_template_markdown(raw: str, stem: str) -> dict:
    """Parse a template markdown file into DocumentTemplate fields.

    Reads an optional YAML frontmatter block for ``title``, ``description``,
    ``document_type`` (validated, defaults to ``policy``) and ``locale``; the
    remainder is the content. ``ref_id`` is derived from the filename stem.
    ``locale`` is None when absent (the caller resolves it, e.g. from the path).
    """
    title = stem.replace("_", " ").title()
    description = ""
    document_type = DocumentContainer.DocumentType.POLICY
    locale = None
    provider = ""
    content = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if isinstance(fm, dict):
                    title = fm.get("title", title)
                    description = fm.get("description", "")
                    dt = fm.get("document_type")
                    if dt in VALID_DOCUMENT_TYPES:
                        document_type = dt
                    loc = fm.get("locale")
                    if isinstance(loc, str) and loc.strip():
                        locale = loc.strip().lower()
                    prov = fm.get("provider")
                    if isinstance(prov, str):
                        provider = prov.strip()
            except yaml.YAMLError:
                # Malformed frontmatter: keep the derived defaults.
                pass
            content = parts[2].strip()
    return {
        "ref_id": stem,
        "name": title,
        "description": description,
        "document_type": document_type,
        "locale": locale,
        "provider": provider,
        "content": content,
    }


def import_templates_from_zip(zip_file, folder) -> dict:
    """Import templates from a .zip whose entries follow ``<locale>/<name>.md``
    (mirroring ``library/policy_templates/``). Upserts one custom DocumentTemplate
    per file. Returns a summary ``{created, updated, errors}``.
    """
    created = 0
    updated = 0
    errors: list[str] = []

    with zipfile.ZipFile(zip_file) as zf:
        members = [
            i
            for i in zf.infolist()
            if not i.is_dir() and i.filename.lower().endswith(".md")
        ][:MAX_TEMPLATE_FILES]
        total_bytes = 0
        for info in members:
            path = Path(info.filename)
            if info.file_size > MAX_TEMPLATE_BYTES:
                errors.append(f"{info.filename}: exceeds size limit")
                continue
            total_bytes += info.file_size
            if total_bytes > MAX_TEMPLATE_TOTAL_BYTES:
                errors.append("import exceeds total size limit")
                break
            stem = path.stem
            try:
                raw = zf.read(info).decode("utf-8")
            except UnicodeDecodeError, KeyError:
                errors.append(f"{info.filename}: not valid UTF-8")
                continue

            data = parse_template_markdown(raw, stem)
            # The <locale>/<name>.md directory (robust to a wrapper folder, e.g.
            # "bundle/en/foo.md") is the primary locale source; a `locale:`
            # frontmatter key is the fallback for flat, single-file bundles.
            fm_locale = data.pop("locale", None)
            locale = path.parts[-2] if len(path.parts) >= 2 else fm_locale
            if not locale:
                errors.append(
                    f"{info.filename}: no locale (use <locale>/<name>.md or a `locale:` frontmatter)"
                )
                continue

            # Never let a custom import clobber a built-in template that shares
            # the (ref_id, locale) unique key.
            if DocumentTemplate.objects.filter(
                ref_id=stem, locale=locale, builtin=True
            ).exists():
                errors.append(f"{info.filename}: conflicts with a built-in template")
                continue

            data.pop("ref_id")
            _, was_created = DocumentTemplate.objects.update_or_create(
                ref_id=stem,
                locale=locale,
                defaults={
                    **data,
                    "builtin": False,
                    "folder": folder,
                    "default_locale": locale == "en",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

    return {"created": created, "updated": updated, "errors": errors}
