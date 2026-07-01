from collections import defaultdict

from django.db import migrations


def backfill_containers(apps, schema_editor):
    """Group existing policy-anchored documents under one DocumentContainer per
    policy (locale variants share a policy), and give standalone documents their
    own container. Populates container.policies with the source policy.
    """
    ManagedDocument = apps.get_model("doc_management", "ManagedDocument")
    DocumentContainer = apps.get_model("doc_management", "DocumentContainer")
    AppliedControl = apps.get_model("core", "AppliedControl")
    db = schema_editor.connection.alias

    by_policy = defaultdict(list)
    orphans = []
    for doc in ManagedDocument.objects.using(db).filter(container__isnull=True):
        if doc.policy_id:
            by_policy[doc.policy_id].append(doc)
        else:
            orphans.append(doc)

    policy_names = dict(
        AppliedControl.objects.using(db)
        .filter(id__in=list(by_policy.keys()))
        .values_list("id", "name")
    )

    def default_of(docs):
        return next((d for d in docs if d.default_locale), docs[0])

    for policy_id, docs in by_policy.items():
        default = default_of(docs)
        container = DocumentContainer.objects.using(db).create(
            document_type=default.document_type,
            name=default.name or policy_names.get(policy_id, ""),
            folder_id=default.folder_id,
            is_published=default.is_published,
        )
        container.policies.add(policy_id)
        for d in docs:
            d.container = container
        ManagedDocument.objects.using(db).bulk_update(docs, ["container"])

    for doc in orphans:
        container = DocumentContainer.objects.using(db).create(
            document_type=doc.document_type,
            name=doc.name or "",
            folder_id=doc.folder_id,
            is_published=doc.is_published,
        )
        doc.container = container
        doc.save(update_fields=["container"])


def reverse(apps, schema_editor):
    ManagedDocument = apps.get_model("doc_management", "ManagedDocument")
    DocumentContainer = apps.get_model("doc_management", "DocumentContainer")
    db = schema_editor.connection.alias
    ManagedDocument.objects.using(db).update(container=None)
    DocumentContainer.objects.using(db).all().delete()


class Migration(migrations.Migration):
    dependencies = [
        (
            "doc_management",
            "0003_alter_manageddocument_policy_documentcontainer_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(backfill_containers, reverse),
    ]
