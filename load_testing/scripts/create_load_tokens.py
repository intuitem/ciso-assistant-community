#!/usr/bin/env python
"""Create Knox tokens for load-test users and write a Locust CSV.

Run from the repository root with the same environment as the target DB, for example:

  DJANGO_SETTINGS_MODULE=ciso_assistant.settings \
  .venv/bin/python load_testing/scripts/create_load_tokens.py --users 50 --superusers

Or inside the backend container:

  docker compose -f load_testing/docker-compose.sqlite.yml exec backend \
    python /code/load_testing/scripts/create_load_tokens.py --users 50 --superusers \
    --out /code/load_testing/users.csv

The initial mode creates superusers because it is the simplest way to exercise broad API
coverage without designing RBAC fixtures first. For final production sizing, prefer
role-scoped users that match real auditor/respondent profiles.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Local checkout: repo/backend/manage.py. Container image: /code/manage.py.
DJANGO_ROOT = (
    REPO_ROOT / "backend"
    if (REPO_ROOT / "backend" / "manage.py").exists()
    else REPO_ROOT
)
sys.path.insert(0, str(DJANGO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from knox.models import AuthToken  # noqa: E402

from iam.models import PersonalAccessToken, User  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--users", type=int, default=50, help="Number of users/tokens to create"
    )
    parser.add_argument("--prefix", default="loadtest", help="Email prefix")
    parser.add_argument("--domain", default="example.test", help="Email domain")
    parser.add_argument(
        "--password",
        default="LoadTest123!",
        help="Password for local login smoke tests",
    )
    parser.add_argument(
        "--superusers",
        action="store_true",
        help="Create users as superusers for broad API access",
    )
    parser.add_argument(
        "--out", default="load_testing/users.csv", help="CSV output path"
    )
    parser.add_argument(
        "--fresh-tokens",
        action="store_true",
        help="Delete previous PAT rows/tokens for matching users first",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    with transaction.atomic():
        for i in range(1, args.users + 1):
            email = f"{args.prefix}-{i:04d}@{args.domain}"
            user = User.objects.filter(email=email).first()
            if user is None:
                if args.superusers:
                    user = User.objects.create_superuser(
                        email=email, password=args.password
                    )
                else:
                    user = User.objects.create_user(
                        email=email, password=args.password, keep_local_login=True
                    )
            elif args.superusers and not user.is_superuser:
                user.is_superuser = True
                user.save(update_fields=["is_superuser"])

            if args.fresh_tokens:
                for pat in PersonalAccessToken.objects.filter(auth_token__user=user):
                    pat.auth_token.delete()

            instance, token = AuthToken.objects.create(user=user)
            PersonalAccessToken.objects.create(name="load-testing", auth_token=instance)
            rows.append({"email": email, "token": token})

    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "token"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} tokens to {out}")


if __name__ == "__main__":
    main()
