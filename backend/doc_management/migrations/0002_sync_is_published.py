from django.db import migrations


def sync_is_published(apps, schema_editor):
    """Sync is_published from parent Policy to existing doc_management objects."""
    ManagedDocument = apps.get_model("doc_management", "ManagedDocument")

    for doc in ManagedDocument.objects.select_related("policy").filter(
        policy__isnull=False
    ):
        published = doc.policy.is_published
        if doc.is_published != published:
            doc.is_published = published
            doc.save(update_fields=["is_published"])
            doc.revisions.exclude(is_published=published).update(is_published=published)
            doc.attachments.exclude(is_published=published).update(
                is_published=published
            )


class Migration(migrations.Migration):
    dependencies = [
        ("doc_management", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sync_is_published, migrations.RunPython.noop),
    ]
