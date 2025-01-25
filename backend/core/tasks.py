from datetime import date
from huey import crontab
from huey.contrib.djhuey import periodic_task, task, db_periodic_task, db_task
from core.models import AppliedControl
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings

# official doc
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
    # TODO: check that the mailer is properly set and log an error otherwise
    subject = f"CISO Assistant: You have {len(controls)} expired control(s)"
    message = "Hello,\n\nThe following controls have expired:\n\n"
    for control in controls:
        message += f"- {control.name} (ETA: {control.eta})\n"
    message += "\nThis reminder will stop once the control is marked as active or you update the ETA.\n"
    message += "Log in to your CISO Assistant portal and check 'my assignments' section to get to your controls directly.\n\n"
    message += "Thank you."
    # think templating and i18n
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[owner_email],
        fail_silently=False,
    )
