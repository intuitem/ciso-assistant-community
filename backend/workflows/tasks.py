from huey.contrib.djhuey import db_task


@db_task()
def run_instance_task(instance_id):
    from .engine import run_instance
    from .models import WorkflowInstance

    instance = WorkflowInstance.objects.filter(id=instance_id).first()
    if instance is not None:
        run_instance(instance)


@db_task()
def retry_token_task(token_id):
    from .engine import run_instance
    from .models import WorkflowToken

    token = WorkflowToken.objects.filter(
        id=token_id, status=WorkflowToken.Status.RETRYING
    ).first()
    if token is None:
        return
    token.status = WorkflowToken.Status.ACTIVE
    token.save(update_fields=["status", "updated_at"])
    run_instance(token.instance)
