"""Locust scenarios for CISO Assistant API load tests.

Default target is the Django API behind Caddy. Authentication uses Knox/PAT tokens:
Authorization: Token <token>

Environment variables:
  LOAD_USERS_CSV=/mnt/locust/users.csv       CSV with columns: email,token
  LOAD_WORKLOAD_JSON=/mnt/locust/workload.json  Seeded assessment/RA ids
  LOAD_TOKEN=...                             fallback single token
  API_PREFIX=/api                            API path prefix
  WARMUP_LIMIT=25                            ids cached per collection
  ENABLE_WRITES=false                        enable RA update flow
"""

from __future__ import annotations

import csv
import itertools
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gevent.lock import Semaphore
from locust import HttpUser, between, task


API_PREFIX = os.getenv("API_PREFIX", "/api").rstrip("/")
USERS_CSV = os.getenv("LOAD_USERS_CSV", "/mnt/locust/users.csv")
WORKLOAD_JSON = os.getenv("LOAD_WORKLOAD_JSON", "/mnt/locust/workload.json")
WARMUP_LIMIT = int(os.getenv("WARMUP_LIMIT", "25"))
ENABLE_WRITES = os.getenv("ENABLE_WRITES", "false").lower() in {"1", "true", "yes"}

RESULT_VALUES = ["compliant", "partially_compliant", "non_compliant", "not_applicable"]
STATUS_VALUES = ["to_do", "in_progress", "in_review", "done"]


@dataclass(frozen=True)
class LoadIdentity:
    email: str
    token: str


def _load_identities() -> list[LoadIdentity]:
    rows: list[LoadIdentity] = []
    path = Path(USERS_CSV)
    if path.exists():
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                token = (row.get("token") or "").strip()
                if token and not token.startswith("paste-"):
                    rows.append(
                        LoadIdentity(
                            email=(row.get("email") or "").strip(), token=token
                        )
                    )
    fallback = os.getenv("LOAD_TOKEN", "").strip()
    if fallback:
        rows.append(LoadIdentity(email="LOAD_TOKEN", token=fallback))
    if not rows:
        raise RuntimeError(
            f"No load-test tokens found. Provide {USERS_CSV} or LOAD_TOKEN. "
            "See load_testing/README.md."
        )
    return rows


def _load_workload() -> dict[str, list[str]]:
    path = Path(WORKLOAD_JSON)
    if not path.exists():
        return {"assessment_ids": [], "requirement_assessment_ids": []}
    import json

    payload = json.loads(path.read_text())
    return {
        "assessment_ids": [str(x) for x in payload.get("assessment_ids", [])],
        "requirement_assessment_ids": [
            str(x) for x in payload.get("requirement_assessment_ids", [])
        ],
    }


_identities = _load_identities()
_workload = _load_workload()
_identity_cycle = itertools.cycle(_identities)
_identity_lock = Semaphore()


def _json_items(payload: Any) -> list[dict[str, Any]]:
    """Support DRF pagination and plain lists."""
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return [x for x in payload["results"] if isinstance(x, dict)]
        if isinstance(payload.get("items"), list):
            return [x for x in payload["items"] if isinstance(x, dict)]
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


class CisoApiUser(HttpUser):
    """Authenticated API user approximating SvelteKit SSR/API activity.

    This intentionally starts with API endpoints instead of browser rendering so the
    DB/backend comparison is not hidden by browser/asset noise. Run through Caddy to
    keep the proxy layer in the path.
    """

    wait_time = between(1, 4)

    # Collection endpoints hit by common list/detail pages.
    collections = (
        "folders",
        "compliance-assessments",
        "requirement-assessments",
        "applied-controls",
        "evidences",
        "risk-assessments",
        "risk-scenarios",
        "assets",
        "findings",
        "task-nodes",
    )

    def on_start(self) -> None:
        with _identity_lock:
            self.identity = next(_identity_cycle)
        self.client.headers.update(
            {
                "Authorization": f"Token {self.identity.token}",
                "Accept": "application/json",
            }
        )
        self.ids: dict[str, list[str]] = {name: [] for name in self.collections}
        if _workload["assessment_ids"]:
            self.ids["compliance-assessments"] = _workload["assessment_ids"]
        if _workload["requirement_assessment_ids"]:
            self.ids["requirement-assessments"] = _workload[
                "requirement_assessment_ids"
            ]
        self._prime_ids()

    def api_get(self, path: str, *, name: str | None = None, **kwargs):
        return self.client.get(f"{API_PREFIX}{path}", name=name or path, **kwargs)

    def api_patch(
        self, path: str, json: dict[str, Any], *, name: str | None = None, **kwargs
    ):
        return self.client.patch(
            f"{API_PREFIX}{path}", json=json, name=name or path, **kwargs
        )

    def _prime_ids(self) -> None:
        for collection in self.collections:
            with self.api_get(
                f"/{collection}/?limit={WARMUP_LIMIT}",
                name=f"/{collection}/ [prime]",
                catch_response=True,
            ) as res:
                if res.status_code == 200:
                    discovered = [
                        str(x["id"]) for x in _json_items(res.json()) if x.get("id")
                    ]
                    # Preserve seeded workload ids; add discovered ids for non-seeded models.
                    self.ids[collection] = list(
                        dict.fromkeys([*self.ids.get(collection, []), *discovered])
                    )
                elif res.status_code in {403, 404}:
                    res.success()  # not every role/module can access every model

    @task(8)
    def list_model(self) -> None:
        collection = random.choice(self.collections)
        limit = random.choice([10, 20, 50])
        offset = random.choice([0, 0, 0, 20, 50])
        with self.api_get(
            f"/{collection}/?limit={limit}&offset={offset}",
            name=f"/{collection}/ [list]",
            catch_response=True,
        ) as res:
            if res.status_code in {403, 404}:
                res.success()

    @task(5)
    def detail_model(self) -> None:
        populated = [c for c, ids in self.ids.items() if ids]
        if not populated:
            self._prime_ids()
            return
        collection = random.choice(populated)
        obj_id = random.choice(self.ids[collection])
        with self.api_get(
            f"/{collection}/{obj_id}/",
            name=f"/{collection}/:id [detail]",
            catch_response=True,
        ) as res:
            if res.status_code in {403, 404}:
                res.success()

    @task(4)
    def dashboard_api(self) -> None:
        endpoint = random.choice(
            [
                "/get_counters/",
                "/get_metrics/",
                "/agg_data/",
                "/user-preferences/",
            ]
        )
        with self.api_get(
            endpoint, name=f"{endpoint} [dashboard]", catch_response=True
        ) as res:
            if res.status_code in {403, 404}:
                res.success()

    @task(2)
    def search_and_filter_like_tables(self) -> None:
        collection = random.choice(
            [
                "compliance-assessments",
                "requirement-assessments",
                "applied-controls",
                "evidences",
            ]
        )
        query = random.choice(["a", "security", "risk", "policy", "control"])
        with self.api_get(
            f"/{collection}/?limit=20&search={query}",
            name=f"/{collection}/ [search]",
            catch_response=True,
        ) as res:
            if res.status_code in {403, 404}:
                res.success()

    @task(6)
    def update_requirement_assessment(self) -> None:
        """Realistic mixed workload: users update requirement assessments.

        This approximates auditors/respondents flipping results/statuses and writing
        observations across the 50 seeded compliance assessments. The target RA ids come
        from `seed_compliance_workload.py` when available, with API discovery as fallback.
        """
        if not ENABLE_WRITES:
            return
        ids = self.ids.get("requirement-assessments") or []
        if not ids:
            self._prime_ids()
            ids = self.ids.get("requirement-assessments") or []
        if not ids:
            return

        ra_id = random.choice(ids)
        result = random.choice(RESULT_VALUES)
        payload: dict[str, Any] = {
            "result": result,
            "status": random.choice(STATUS_VALUES),
            "observation": (
                f"Load test update by {self.identity.email}; "
                f"result={result}; marker={random.randint(1, 1_000_000)}"
            ),
        }
        # Keep extended_result empty to avoid result-dependent validation constraints.
        payload["extended_result"] = None
        with self.api_patch(
            f"/requirement-assessments/{ra_id}/",
            json=payload,
            name="/requirement-assessments/:id [update]",
            catch_response=True,
        ) as res:
            if res.status_code in {403, 404}:
                res.success()
