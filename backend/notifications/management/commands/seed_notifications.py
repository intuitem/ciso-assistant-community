"""Fill an inbox with a realistic spread, for judging the UI before the nightly
sweeps have produced anything. Development only."""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from iam.models import User
from notifications.models import Notification
from notifications.registry import NOTIFICATION_REGISTRY
from notifications.service import notify

# Which model a type points at, keyed by the context variable the registry declares.
# Seeding a "control assigned to you" row against an Evidence produces a page that
# looks broken, so the target has to match what the producer would really pass.
TARGET_FOR_CONTEXT_VAR = {
    "control_name": "AppliedControl",
    "evidence_name": "Evidence",
    "assessment_name": "ComplianceAssessment",
    "scenario_name": "RiskScenario",
    "exception_name": "SecurityException",
    "task_name": "TaskNode",
    "validation_ref_id": "ValidationFlow",
    "response_name": "QuickFormResponse",
}


class Command(BaseCommand):
    help = "Seed the notification inbox of a user with a spread of types and ages."

    def add_arguments(self, parser):
        parser.add_argument("email", help="recipient")
        parser.add_argument("--per-type", type=int, default=3)
        parser.add_argument(
            "--clear", action="store_true", help="delete this user's rows first"
        )

    def handle(self, *args, **options):
        user = User.objects.filter(email__iexact=options["email"]).first()
        if not user:
            self.stderr.write(f"No user {options['email']}")
            return

        if options["clear"]:
            deleted, _ = Notification.objects.filter(recipient=user).delete()
            self.stdout.write(f"cleared {deleted}")

        pools = self._pools()
        written, skipped = 0, []

        for key, entry in NOTIFICATION_REGISTRY.items():
            if "in_app" not in entry["channels"]:
                continue

            model_name = next(
                (
                    TARGET_FOR_CONTEXT_VAR[var]
                    for var in entry["context"]
                    if var in TARGET_FOR_CONTEXT_VAR
                ),
                None,
            )
            pool = pools.get(model_name) or []
            if not pool:
                skipped.append(f"{key} (no {model_name or 'target'} with a folder)")
                continue

            for target in random.sample(pool, min(options["per_type"], len(pool))):
                context = {var: self._value(var, target) for var in entry["context"]}
                for row in notify(key, [user], target, context):
                    # Spread created_at so the list is not one flat timestamp, and mark
                    # roughly a third read so both states are visible.
                    Notification.objects.filter(pk=row.pk).update(
                        created_at=timezone.now()
                        - timedelta(days=random.randint(0, 45)),
                        is_read=random.random() < 0.33,
                    )
                    written += 1

        unread = Notification.objects.filter(recipient=user, is_read=False).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"{written} notifications for {user.email} ({unread} unread)"
            )
        )
        for note in skipped:
            self.stdout.write(self.style.WARNING(f"  skipped {note}"))

    def _pools(self) -> dict:
        from core import models as core_models

        pools = {}
        for name in set(TARGET_FOR_CONTEXT_VAR.values()):
            model = getattr(core_models, name, None)
            if model is None:
                continue
            try:
                pools[name] = list(model.objects.exclude(folder=None)[:8])
            except Exception:
                # Models whose folder is derived rather than a column.
                pools[name] = list(model.objects.all()[:8])
        return pools

    def _value(self, var, target):
        if var in ("days_remaining", "days"):
            return random.choice([1, 3, 7, 14, 30])
        if var == "decision":
            return random.choice(["approved", "rejected"])
        if var == "new_status":
            return random.choice(["approved", "rejected", "expired"])
        return str(target)
