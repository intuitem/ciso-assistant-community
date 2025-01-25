from datetime import date, datetime, timezone
from huey import crontab
from huey.contrib.djhuey import periodic_task, task, db_periodic_task, db_task
from core.models import AppliedControl
from django.db.models import Q


# basic placeholders from the official doc
# https://huey.readthedocs.io/en/latest/django.html


@db_periodic_task(crontab(minute="*/1"))
def check_controls_with_expired_eta():
    expired_controls = (
        AppliedControl.objects.exclude(status="active")
        .filter(eta__lt=date.today(), eta__isnull=False)
        .prefetch_related("owner")
    )

    # Group by individual owner
    owner_controls = {}
    for control in expired_controls:
        for owner in control.owner.all():
            if owner.email not in owner_controls:
                owner_controls[owner.email] = []
            owner_controls[owner.email].append(control)

    # Send personalized email to each owner
    for owner_email, controls in owner_controls.items():
        send_notification_email(owner_email, controls)


@task()
def send_notification_email(owner_email, controls):
    subject = f"You have {len(controls)} expired controls"
    message = "The following controls have expired:\n\n"
    for control in controls:
        message += f"- {control.name} (ETA: {control.eta})\n"

    print(f"Sending email to {owner_email}")
    print(message)
