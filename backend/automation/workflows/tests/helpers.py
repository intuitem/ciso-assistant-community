"""Shared helpers for workflow engine tests.

Run authorization gives every run an identity. Engine-level tests
that exercise privileged actions need one: ``publisher_user()`` returns a
process-wide admin (BI-UG-ADM member, so kernel verdicts pass — there is no
superuser bypass in the runtime path) usable both as ``publish(user)``
argument and as a draft ``run_as``/``initiated_by``.
"""

from iam.models import User


def publisher_user():
    user = User.objects.filter(email="publisher@tests.local").first()
    return user or User.objects.create_superuser(
        email="publisher@tests.local", password="x"
    )
