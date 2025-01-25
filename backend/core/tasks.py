from datetime import date, datetime, timezone
from huey import crontab
from huey.contrib.djhuey import periodic_task, task, db_periodic_task, db_task
from core.models import AppliedControl
from django.db.models import Q


# basic placeholders from the official doc
# https://huey.readthedocs.io/en/latest/django.html
#
@task()
def count_beans(number):
    print("-- counted %s beans --" % number)
    return "Counted %s beans" % number


@task()
def send_email():
    print("sending an email")
    return "email sent"


@periodic_task(crontab(minute="*/1"))
def every_min():
    print("Every five minutes this will be printed by the consumer")


@db_task()
def do_some_queries():
    # This task executes queries. Once the task finishes, the connection
    # will be closed.
    pass


@db_periodic_task(crontab(minute="*/5"))
def every_five_mins_db():
    print("Every five minutes this will be printed by the consumer")


# unrralistic, just for testing
@db_periodic_task(crontab(minute="*/1"))
def check_controls_with_expired_eta():
    expired_eta_controls = AppliedControl.objects.exclude(status="active").filter(
        eta__lt=date.today(), eta__isnull=False
    )
    print(f"Found {expired_eta_controls.count()} expired controls")
    for ac in expired_eta_controls:
        print(":: ", ac.name)
    send_email()
