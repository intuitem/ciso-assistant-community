import secrets

from django.db import migrations


def backfill_secrets(apps, schema_editor):
    Workflow = apps.get_model("workflows", "Workflow")
    for workflow in Workflow.objects.all():
        workflow.webhook_secret = secrets.token_urlsafe(32)
        workflow.save(update_fields=["webhook_secret"])


class Migration(migrations.Migration):
    dependencies = [
        ("workflows", "0002_workflow_webhook_secret_workflowinstance_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_secrets, migrations.RunPython.noop),
    ]
