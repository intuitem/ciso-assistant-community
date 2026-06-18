#!/usr/bin/env python3
"""
SCIM 2.0 end-to-end test driver for CISO Assistant.

Mimics the request patterns generic SCIM 2.0 clients send so you can
validate the full provisioning flow against your deployment.

Usage:
    python test_scim.py --base-url http://localhost:8000 --token <SCIM_TOKEN>

    # Or via env vars:
    SCIM_BASE_URL=http://localhost:8000 SCIM_TOKEN=xxx python test_scim.py

    # Filter to a single phase:
    python test_scim.py --only discovery
    python test_scim.py --only users
    python test_scim.py --only groups

    # Keep test data after run (for inspection):
    python test_scim.py --no-cleanup
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field

import requests


# ---------------------------------------------------------------------------
# Pretty output
# ---------------------------------------------------------------------------

class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


def section(title: str) -> None:
    print(f"\n{Style.BOLD}{Style.CYAN}━━━ {title} ━━━{Style.RESET}")


def step(idp: str, action: str) -> None:
    print(f"  {Style.MAGENTA}[{idp}]{Style.RESET} {action}")


def ok(msg: str) -> None:
    print(f"    {Style.GREEN}✓{Style.RESET} {msg}")


def fail(msg: str) -> None:
    print(f"    {Style.RED}✗{Style.RESET} {msg}")


def info(msg: str) -> None:
    print(f"    {Style.DIM}ℹ {msg}{Style.RESET}")


# ---------------------------------------------------------------------------
# SCIM client (with assertions)
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def record(self, name: str, condition: bool, detail: str = "") -> bool:
        if condition:
            self.passed += 1
            ok(f"{name}{(' — ' + detail) if detail else ''}")
        else:
            self.failed += 1
            self.errors.append(name)
            fail(f"{name}{(' — ' + detail) if detail else ''}")
        return condition


class SCIMClient:
    def __init__(self, base_url: str, token: str, verbose: bool = False):
        self.base_url = base_url.rstrip("/") + "/api/scim/v2"
        self.token = token
        self.verbose = verbose
        self.session = requests.Session()
        # Real IdPs set both the Bearer header and a SCIM content type.
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/scim+json",
            "Content-Type": "application/scim+json",
            "User-Agent": "SCIM-Test-Driver/1.0",
        })

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        if self.verbose:
            info(f"{method} {url} → {resp.status_code}")
            if resp.text and resp.status_code >= 400:
                info(f"  body: {resp.text[:300]}")
        return resp

    def get(self, path: str, params: dict | None = None) -> requests.Response:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict) -> requests.Response:
        return self._request("POST", path, data=json.dumps(body))

    def put(self, path: str, body: dict) -> requests.Response:
        return self._request("PUT", path, data=json.dumps(body))

    def patch(self, path: str, body: dict) -> requests.Response:
        return self._request("PATCH", path, data=json.dumps(body))

    def delete(self, path: str) -> requests.Response:
        return self._request("DELETE", path)


# ---------------------------------------------------------------------------
# Test phases
# ---------------------------------------------------------------------------

def phase_discovery(client: SCIMClient, result: TestResult) -> None:
    section("Phase 1 — Service Provider Discovery (all IdPs)")

    step("SCIM client", "GET /ServiceProviderConfig (no auth required)")
    # Real IdPs call this without auth to discover capabilities.
    resp = requests.get(f"{client.base_url}/ServiceProviderConfig", timeout=10)
    result.record("ServiceProviderConfig returns 200", resp.status_code == 200,
                  f"got {resp.status_code}")
    if resp.status_code == 200:
        cfg = resp.json()
        result.record("Has PATCH support", cfg.get("patch", {}).get("supported") is True)
        result.record("Has filter support", cfg.get("filter", {}).get("supported") is True)
        result.record(
            "Authentication scheme is oauthbearertoken",
            any(s.get("type") == "oauthbearertoken"
                for s in cfg.get("authenticationSchemes", [])),
        )
        result.record(
            "Content-Type is application/scim+json",
            "scim+json" in resp.headers.get("Content-Type", ""),
        )

    # /Schemas — SCIM clients probe this during initial connector setup.
    step("SCIM client", "GET /Schemas (no auth)")
    resp = requests.get(f"{client.base_url}/Schemas", timeout=10)
    result.record("/Schemas returns 200", resp.status_code == 200,
                  f"got {resp.status_code}")
    if resp.status_code == 200:
        body = resp.json()
        schema_ids = {r.get("id") for r in body.get("Resources", [])}
        result.record(
            "/Schemas advertises User",
            "urn:ietf:params:scim:schemas:core:2.0:User" in schema_ids,
        )
        result.record(
            "/Schemas advertises Group",
            "urn:ietf:params:scim:schemas:core:2.0:Group" in schema_ids,
        )

    # /Schemas/{urn} — single schema lookup
    step("SCIM client", "GET /Schemas/urn:ietf:params:scim:schemas:core:2.0:User")
    resp = requests.get(
        f"{client.base_url}/Schemas/urn:ietf:params:scim:schemas:core:2.0:User",
        timeout=10,
    )
    result.record("Single schema lookup returns 200", resp.status_code == 200,
                  f"got {resp.status_code}")
    if resp.status_code == 200:
        attrs = {a.get("name") for a in resp.json().get("attributes", [])}
        result.record("User schema declares userName", "userName" in attrs)
        result.record("User schema declares emails", "emails" in attrs)
        result.record("User schema declares active", "active" in attrs)

    # /ResourceTypes — discovery of supported resources
    step("SCIM client", "GET /ResourceTypes (no auth)")
    resp = requests.get(f"{client.base_url}/ResourceTypes", timeout=10)
    result.record("/ResourceTypes returns 200", resp.status_code == 200,
                  f"got {resp.status_code}")
    if resp.status_code == 200:
        type_ids = {r.get("id") for r in resp.json().get("Resources", [])}
        result.record("/ResourceTypes advertises User", "User" in type_ids)
        result.record("/ResourceTypes advertises Group", "Group" in type_ids)


def phase_users(client: SCIMClient, result: TestResult, cleanup: bool) -> list[str]:
    """
    Returns list of created user IDs (for the group phase to consume).
    """
    section("Phase 2 — User Provisioning Flow (generic SCIM pattern)")

    created_ids: list[str] = []
    run_id = uuid.uuid4().hex[:8]
    alice_email = f"alice-{run_id}@scim-test.local"
    bob_email = f"bob-{run_id}@scim-test.local"
    alice_external = f"scim-{run_id}-alice"
    bob_external = f"scim-{run_id}-bob"

    # ─────────────────────────────────────────────────────────────────────
    # 1. Pre-flight: SCIM-style "does this user already exist?" check
    # ─────────────────────────────────────────────────────────────────────
    step("SCIM client", f'GET /Users?filter=userName eq "{alice_email}"')
    resp = client.get("/Users", params={
        "filter": f'userName eq "{alice_email}"',
        "startIndex": 1,
        "count": 100,
    })
    result.record("Pre-flight filter returns 200", resp.status_code == 200,
                  f"got {resp.status_code}")
    if resp.status_code == 200:
        body = resp.json()
        result.record("ListResponse schema present",
                      "urn:ietf:params:scim:api:messages:2.0:ListResponse"
                      in body.get("schemas", []))
        result.record("totalResults is 0 (user does not exist yet)",
                      body.get("totalResults") == 0,
                      f"got {body.get('totalResults')}")

    # ─────────────────────────────────────────────────────────────────────
    # 2. Create user (SCIM-style payload)
    # ─────────────────────────────────────────────────────────────────────
    step("SCIM client", f"POST /Users (create {alice_email})")
    scim_payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "externalId": alice_external,
        "userName": alice_email,
        "name": {"givenName": "Alice", "familyName": "Anderson"},
        "emails": [{"value": alice_email, "primary": True, "type": "work"}],
        "active": True,
    }
    resp = client.post("/Users", scim_payload)
    result.record("Create user returns 201", resp.status_code == 201,
                  f"got {resp.status_code}")
    alice_id = None
    if resp.status_code == 201:
        body = resp.json()
        alice_id = body.get("id")
        created_ids.append(alice_id)
        result.record("Response has id", bool(alice_id))
        result.record("Response has externalId",
                      body.get("externalId") == alice_external)
        result.record("Response has userName", body.get("userName") == alice_email)
        result.record("Response active=true", body.get("active") is True)
        result.record("meta.resourceType is User",
                      body.get("meta", {}).get("resourceType") == "User")
        result.record("meta.location set",
                      bool(body.get("meta", {}).get("location")))

    # ─────────────────────────────────────────────────────────────────────
    # 3. Idempotency: same POST again (the client retries on transient failures)
    # ─────────────────────────────────────────────────────────────────────
    step("SCIM client", "POST /Users again (idempotent — should update, not duplicate)")
    resp = client.post("/Users", scim_payload)
    # The implementation returns 200 on idempotent update.
    result.record("Duplicate POST returns 200 (idempotent)", resp.status_code == 200,
                  f"got {resp.status_code}")
    if resp.status_code == 200 and alice_id:
        result.record("Same id returned", resp.json().get("id") == alice_id)

    # ─────────────────────────────────────────────────────────────────────
    # 4. Lookup by externalId (SCIM-spec capability)
    # ─────────────────────────────────────────────────────────────────────
    step("SCIM client", f'GET /Users?filter=externalId eq "{alice_external}"')
    resp = client.get("/Users", params={
        "filter": f'externalId eq "{alice_external}"',
    })
    result.record("Filter by externalId returns 200", resp.status_code == 200)
    if resp.status_code == 200:
        result.record("Filter by externalId finds user",
                      resp.json().get("totalResults") == 1)

    # ─────────────────────────────────────────────────────────────────────
    # 5. Retrieve by id
    # ─────────────────────────────────────────────────────────────────────
    if alice_id:
        step("SCIM client", f"GET /Users/{alice_id}")
        resp = client.get(f"/Users/{alice_id}")
        result.record("GET by id returns 200", resp.status_code == 200)

    # ─────────────────────────────────────────────────────────────────────
    # 6. PATCH — update name (replace with value dict)
    # ─────────────────────────────────────────────────────────────────────
    if alice_id:
        step("SCIM client", "PATCH /Users (replace with value dict)")
        value_patch = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "Replace", "value": {
                    "name": {"givenName": "Alice", "familyName": "Anderson-Updated"},
                }},
            ],
        }
        resp = client.patch(f"/Users/{alice_id}", value_patch)
        result.record("value-dict PATCH returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            result.record("Family name updated",
                          resp.json().get("name", {}).get("familyName")
                          == "Anderson-Updated")

    # ─────────────────────────────────────────────────────────────────────
    # 7. PATCH — SCIM-style: deactivate user (path-based)
    # ─────────────────────────────────────────────────────────────────────
    if alice_id:
        step("SCIM client", "PATCH /Users (SCIM-style: deactivate with path)")
        scim_deactivate = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace", "path": "active", "value": False},
            ],
        }
        resp = client.patch(f"/Users/{alice_id}", scim_deactivate)
        result.record("SCIM-style PATCH deactivate returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            result.record("active is now false",
                          resp.json().get("active") is False)

    # ─────────────────────────────────────────────────────────────────────
    # 8. Reactivate via PATCH with value dict
    # ─────────────────────────────────────────────────────────────────────
    if alice_id:
        step("Generic", "PATCH /Users (reactivate)")
        resp = client.patch(f"/Users/{alice_id}", {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "value": {"active": True}}],
        })
        result.record("Reactivate returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            result.record("active is true again", resp.json().get("active") is True)

    # ─────────────────────────────────────────────────────────────────────
    # 8b. PATCH — SCIM-style email change via filter path
    # ─────────────────────────────────────────────────────────────────────
    if alice_id:
        new_alice_email = f"alice-renamed-{run_id}@scim-test.local"
        step("SCIM client", 'PATCH /Users (emails[type eq "work"].value)')
        resp = client.patch(f"/Users/{alice_id}", {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace",
                 "path": 'emails[type eq "work"].value',
                 "value": new_alice_email},
            ],
        })
        result.record("PATCH email by filter path returns 200",
                      resp.status_code == 200)
        if resp.status_code == 200:
            primary = next(
                (e for e in resp.json().get("emails", []) if e.get("primary")),
                {},
            )
            result.record("Email was updated by filter path",
                          primary.get("value") == new_alice_email)
            alice_email = new_alice_email

    # ─────────────────────────────────────────────────────────────────────
    # 9. Create a second user (for group membership tests later)
    # ─────────────────────────────────────────────────────────────────────
    step("SCIM client", f"POST /Users (create {bob_email})")
    bob_payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "externalId": bob_external,
        "userName": bob_email,
        "name": {"givenName": "Bob", "familyName": "Brown"},
        "emails": [{"value": bob_email, "primary": True}],
        "active": True,
    }
    resp = client.post("/Users", bob_payload)
    result.record("Second user created", resp.status_code == 201)
    bob_id = None
    if resp.status_code == 201:
        bob_id = resp.json().get("id")
        created_ids.append(bob_id)

    # ─────────────────────────────────────────────────────────────────────
    # 10. PUT — full replace (per RFC 7644)
    # ─────────────────────────────────────────────────────────────────────
    if bob_id:
        step("SCIM client", f"PUT /Users/{bob_id} (full replace)")
        resp = client.put(f"/Users/{bob_id}", {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "externalId": bob_external,
            "userName": bob_email,
            "name": {"givenName": "Robert", "familyName": "Brown"},
            "active": True,
        })
        result.record("PUT returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            result.record("Given name updated to Robert",
                          resp.json().get("name", {}).get("givenName") == "Robert")

    # ─────────────────────────────────────────────────────────────────────
    # 11. DELETE — DELETE for deprovision
    # ─────────────────────────────────────────────────────────────────────
    if cleanup and alice_id:
        step("SCIM client", f"DELETE /Users/{alice_id} (deprovision)")
        resp = client.delete(f"/Users/{alice_id}")
        result.record("DELETE returns 204", resp.status_code == 204,
                      f"got {resp.status_code}")
        # Verify the user is now inactive (soft-delete in our implementation)
        resp = client.get(f"/Users/{alice_id}")
        if resp.status_code == 200:
            result.record("User soft-deleted (active=false)",
                          resp.json().get("active") is False)

    return [uid for uid in created_ids if uid]


def phase_groups(client: SCIMClient, result: TestResult,
                 user_ids: list[str], cleanup: bool) -> None:
    section("Phase 3 — Group Provisioning Flow (generic SCIM pattern)")

    if not user_ids:
        info("No user IDs from previous phase — skipping membership tests")

    run_id = uuid.uuid4().hex[:8]
    group_name = f"Engineering-{run_id}"
    group_external = f"scim-grp-{run_id}"

    # ─────────────────────────────────────────────────────────────────────
    # 1. Pre-flight: lookup by displayName
    # ─────────────────────────────────────────────────────────────────────
    step("SCIM client", f'GET /Groups?filter=displayName eq "{group_name}"')
    resp = client.get("/Groups", params={
        "filter": f'displayName eq "{group_name}"',
    })
    result.record("Group pre-flight returns 200", resp.status_code == 200)
    if resp.status_code == 200:
        result.record("Group does not exist yet",
                      resp.json().get("totalResults") == 0)

    # ─────────────────────────────────────────────────────────────────────
    # 2. Create group with initial members
    # ─────────────────────────────────────────────────────────────────────
    step("SCIM client", f"POST /Groups (create {group_name} with members)")
    members_payload = [
        {"value": uid, "display": "member"} for uid in user_ids[:1]
    ]
    resp = client.post("/Groups", {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "externalId": group_external,
        "displayName": group_name,
        "members": members_payload,
    })
    result.record("Create group returns 201", resp.status_code == 201,
                  f"got {resp.status_code}")
    group_id = None
    if resp.status_code == 201:
        body = resp.json()
        group_id = body.get("id")
        result.record("Group has id", bool(group_id))
        result.record("Group has externalId",
                      body.get("externalId") == group_external)
        result.record("Group displayName matches",
                      body.get("displayName") == group_name)
        if user_ids:
            result.record("Initial member present",
                          len(body.get("members", [])) == 1)

    # ─────────────────────────────────────────────────────────────────────
    # 3. PATCH — add member (the IdP pattern)
    # ─────────────────────────────────────────────────────────────────────
    if group_id and len(user_ids) >= 2:
        step("SCIM client", f"PATCH /Groups/{group_id} (add second member)")
        resp = client.patch(f"/Groups/{group_id}", {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "add", "path": "members",
                 "value": [{"value": user_ids[1]}]},
            ],
        })
        result.record("PATCH add member returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            result.record("Group now has 2 members",
                          len(resp.json().get("members", [])) == 2)

    # ─────────────────────────────────────────────────────────────────────
    # 4. PATCH — remove member with filter path (filter selector path)
    # ─────────────────────────────────────────────────────────────────────
    if group_id and user_ids:
        step("SCIM client", f"PATCH /Groups/{group_id} (remove member by filter)")
        target_uid = user_ids[0]
        resp = client.patch(f"/Groups/{group_id}", {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "remove",
                 "path": f'members[value eq "{target_uid}"]'},
            ],
        })
        result.record("PATCH remove member returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            members = resp.json().get("members", [])
            result.record("Removed member is gone",
                          not any(m.get("value") == target_uid for m in members))

    # ─────────────────────────────────────────────────────────────────────
    # 5. PATCH — rename group (replace displayName, per RFC 7644)
    # ─────────────────────────────────────────────────────────────────────
    if group_id:
        new_name = f"{group_name}-Renamed"
        step("SCIM client", f"PATCH /Groups/{group_id} (rename displayName)")
        resp = client.patch(f"/Groups/{group_id}", {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace",
                 "value": {"displayName": new_name}},
            ],
        })
        result.record("PATCH rename returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            result.record("displayName updated",
                          resp.json().get("displayName") == new_name)

    # ─────────────────────────────────────────────────────────────────────
    # 6. PATCH — full replace members list (per RFC 7644)
    # ─────────────────────────────────────────────────────────────────────
    if group_id and user_ids:
        step("SCIM client", f"PATCH /Groups/{group_id} (replace all members)")
        resp = client.patch(f"/Groups/{group_id}", {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace", "path": "members",
                 "value": [{"value": uid} for uid in user_ids]},
            ],
        })
        result.record("PATCH replace members returns 200", resp.status_code == 200)
        if resp.status_code == 200:
            result.record("Member count matches",
                          len(resp.json().get("members", [])) == len(user_ids))

    # ─────────────────────────────────────────────────────────────────────
    # 7. DELETE group
    # ─────────────────────────────────────────────────────────────────────
    if cleanup and group_id:
        step("SCIM client", f"DELETE /Groups/{group_id}")
        resp = client.delete(f"/Groups/{group_id}")
        result.record("DELETE group returns 204", resp.status_code == 204)
        # Verify it's gone
        resp = client.get(f"/Groups/{group_id}")
        result.record("Group really deleted (404)", resp.status_code == 404)


def phase_bulk(client: SCIMClient, result: TestResult, n: int,
               style: str, group_name: str, cleanup: bool) -> None:
    """
    Load generator: mimic an IdP syncing a group that has `n` members.

    Provisions `n` users, then pushes them into a group in a single PATCH —
    the way a real IdP sends a large group sync. `style` controls the PATCH
    shape:
      - per-member  : one {"op":"add","path":"members","value":[{...}]} per
                      user (e.g. authentik) -> `n` Operations in one request.
      - single-op   : one {"op":"add","path":"members","value":[ ...n... ]}
                      (e.g. Azure AD) -> 1 Operation with `n` values.

    The target group must already exist as an IdP group *and be mapped* in
    CISO (POST /Groups never auto-creates one). Use --group-name to point at
    a group you mapped beforehand.
    """
    section(f"Bulk load — group of {n} members ({style})")

    run_id = uuid.uuid4().hex[:8]

    # ── 1. Provision n users ────────────────────────────────────────────────
    step("SCIM client", f"POST /Users ×{n} (provision members)")
    user_ids: list[str] = []
    t0 = time.time()
    for i in range(n):
        email = f"bulk-{run_id}-{i}@scim-test.local"
        resp = client.post("/Users", {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "externalId": f"scim-bulk-{run_id}-{i}",
            "userName": email,
            "name": {"givenName": "Bulk", "familyName": f"User{i}"},
            "emails": [{"value": email, "primary": True, "type": "work"}],
            "active": True,
        })
        if resp.status_code in (200, 201):
            user_ids.append(resp.json().get("id"))
        elif client.verbose:
            info(f"user {i} POST → {resp.status_code}: {resp.text[:120]}")
        if n >= 50 and (i + 1) % max(1, n // 10) == 0:
            info(f"provisioned {i + 1}/{n} users…")
    prov_dt = time.time() - t0
    result.record(f"Provisioned {n} users", len(user_ids) == n,
                  f"created {len(user_ids)}/{n} in {prov_dt:.1f}s")
    if not user_ids:
        fail("No users provisioned — aborting bulk phase")
        return

    # ── 2. Resolve the (pre-mapped) target group ────────────────────────────
    step("SCIM client", f'POST /Groups (resolve "{group_name}")')
    resp = client.post("/Groups", {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "externalId": f"scim-bulk-grp-{group_name}",
        "displayName": group_name,
        "members": [],
    })
    if resp.status_code == 400:
        fail(f'Group "{group_name}" is not configured/mapped in CISO. '
             f"Create an IdP group with that external ID and a route, then retry.")
        if cleanup:
            _bulk_cleanup_users(client, user_ids)
        return
    if not result.record("Group resolved (201)", resp.status_code == 201,
                         f"got {resp.status_code}"):
        if cleanup:
            _bulk_cleanup_users(client, user_ids)
        return
    group_id = resp.json().get("id")

    # ── 3. The big membership PATCH (what the IdP actually sends) ────────────
    if style == "per-member":
        operations = [
            {"op": "add", "path": "members", "value": [{"value": uid}]}
            for uid in user_ids
        ]
    else:  # single-op
        operations = [
            {"op": "add", "path": "members",
             "value": [{"value": uid} for uid in user_ids]},
        ]

    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": operations,
    }
    body_bytes = len(json.dumps(payload))
    step("SCIM client",
         f"PATCH /Groups/{group_id} ({len(operations)} ops, {body_bytes/1024:.0f} KB)")
    t0 = time.time()
    resp = client.patch(f"/Groups/{group_id}", payload)
    patch_dt = time.time() - t0
    result.record("Bulk membership PATCH returns 200", resp.status_code == 200,
                  f"got {resp.status_code} in {patch_dt:.2f}s "
                  f"({n / patch_dt:.0f} members/s)")
    if resp.status_code == 200:
        members = resp.json().get("members", [])
        result.record("All members present after PATCH",
                      len(members) == n, f"got {len(members)}/{n}")

    # ── 4. Read-back timing (serializing n members) ─────────────────────────
    step("SCIM client", f"GET /Groups/{group_id} (read back {n} members)")
    t0 = time.time()
    get_resp = client.get(f"/Groups/{group_id}")
    get_dt = time.time() - t0
    result.record("Read-back returns 200", get_resp.status_code == 200,
                  f"in {get_dt:.2f}s")

    # ── Perf summary ─────────────────────────────────────────────────────────
    section(f"Perf — group of {n} members ({style})")
    print(f"    {Style.BOLD}provision {n} users : "
          f"{prov_dt:8.2f}s  ({n / prov_dt:7.0f} users/s){Style.RESET}")
    print(f"    {Style.BOLD}membership PATCH    : "
          f"{patch_dt:8.2f}s  ({n / patch_dt:7.0f} members/s){Style.RESET}")
    print(f"    {Style.BOLD}read-back GET       : "
          f"{get_dt:8.2f}s{Style.RESET}")
    print(f"    {Style.DIM}PATCH body size     : {body_bytes/1024:8.0f} KB "
          f"in {len(operations)} op(s){Style.RESET}")

    # ── 5. Cleanup ───────────────────────────────────────────────────────────
    if cleanup:
        t0 = time.time()
        step("SCIM client", f"DELETE /Groups/{group_id} + {len(user_ids)} users")
        client.delete(f"/Groups/{group_id}")
        _bulk_cleanup_users(client, user_ids)
        info(f"bulk test data removed in {time.time() - t0:.2f}s")


def _bulk_cleanup_users(client: SCIMClient, user_ids: list[str]) -> None:
    for uid in user_ids:
        if uid:
            client.delete(f"/Users/{uid}")


def phase_auth(client: SCIMClient, result: TestResult) -> None:
    section("Phase 4 — Authentication & Authorization edge cases")

    step("Generic", "GET /Users without auth → expect 401")
    resp = requests.get(f"{client.base_url}/Users", timeout=10)
    result.record("Unauthenticated GET returns 401", resp.status_code == 401,
                  f"got {resp.status_code}")

    step("Generic", "GET /Users with wrong token → expect 401")
    resp = requests.get(
        f"{client.base_url}/Users",
        headers={"Authorization": "Bearer not-a-real-token-xxx"},
        timeout=10,
    )
    result.record("Bad token returns 401", resp.status_code == 401,
                  f"got {resp.status_code}")


def phase_errors(client: SCIMClient, result: TestResult) -> None:
    section("Phase 5 — Error handling")

    step("Generic", "GET /Users/nonexistent-uuid → expect 404")
    resp = client.get(f"/Users/{uuid.uuid4()}")
    result.record("Nonexistent user returns 404", resp.status_code == 404,
                  f"got {resp.status_code}")
    if resp.status_code == 404:
        body = resp.json()
        result.record("Error body has SCIM error schema",
                      "urn:ietf:params:scim:api:messages:2.0:Error"
                      in body.get("schemas", []))

    step("Generic", "POST /Users with no userName → expect 400")
    resp = client.post("/Users", {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "name": {"givenName": "NoUserName"},
    })
    result.record("Missing userName returns 400", resp.status_code == 400)

    step("Generic", "POST /Users with malformed JSON → expect 400")
    resp = client.session.post(
        f"{client.base_url}/Users",
        data="this-is-not-json",
        timeout=10,
    )
    result.record("Malformed JSON returns 400", resp.status_code == 400)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="SCIM 2.0 E2E test driver")
    parser.add_argument("--base-url", default=os.environ.get("SCIM_BASE_URL",
                                                              "http://localhost:8000"),
                        help="Base URL of the CISO Assistant backend "
                             "(no /api/scim/v2 suffix). Default: http://localhost:8000")
    parser.add_argument("--token", default=os.environ.get("SCIM_TOKEN"),
                        help="SCIM Bearer token (or set SCIM_TOKEN env var)")
    parser.add_argument("--only",
                        choices=["discovery", "users", "groups", "auth", "errors"],
                        help="Run only one phase")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Don't delete test users/groups after the run")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print every HTTP request/response")
    parser.add_argument("--bulk", type=int, metavar="N",
                        help="Load test: provision N users and sync them into "
                             "a group in one PATCH (mimics an IdP group of size "
                             "N). Runs only the bulk phase.")
    parser.add_argument("--bulk-style", choices=["per-member", "single-op"],
                        default="per-member",
                        help="Shape of the membership PATCH: 'per-member' = one "
                             "add op per user (authentik), 'single-op' = one op "
                             "with N values (Azure AD). Default: per-member")
    parser.add_argument("--group-name", default="BulkLoad",
                        help="External ID / displayName of the pre-mapped IdP "
                             "group to target for --bulk. Default: BulkLoad")
    args = parser.parse_args()

    if not args.token:
        print(f"{Style.RED}error{Style.RESET}: --token or SCIM_TOKEN required")
        print("\nGenerate a token in CISO Assistant: Settings → SCIM Provisioning → Generate token")
        return 2

    client = SCIMClient(args.base_url, args.token, verbose=args.verbose)
    result = TestResult()

    print(f"{Style.BOLD}SCIM 2.0 Test Driver{Style.RESET}")
    print(f"  Endpoint: {client.base_url}")
    print(f"  Token: {args.token[:12]}…")
    print(f"  Cleanup: {'no' if args.no_cleanup else 'yes'}")

    t_start = time.time()

    try:
        if args.bulk is not None:
            # Load-test mode: only the bulk phase runs.
            phase_bulk(client, result, args.bulk, args.bulk_style,
                       args.group_name, cleanup=not args.no_cleanup)
        else:
            if args.only in (None, "discovery"):
                phase_discovery(client, result)
            if args.only in (None, "auth"):
                phase_auth(client, result)
            if args.only in (None, "errors"):
                phase_errors(client, result)

            user_ids: list[str] = []
            if args.only in (None, "users"):
                user_ids = phase_users(client, result, cleanup=not args.no_cleanup)
            if args.only in (None, "groups"):
                # If we skipped the users phase but still want to test groups,
                # we won't have user_ids — group ops will still run for the
                # parts that don't need members.
                phase_groups(client, result, user_ids, cleanup=not args.no_cleanup)
    except requests.exceptions.ConnectionError as e:
        print(f"\n{Style.RED}Connection failed:{Style.RESET} {e}")
        print(f"Is the backend running at {args.base_url}?")
        return 2
    except KeyboardInterrupt:
        print(f"\n{Style.YELLOW}Interrupted by user{Style.RESET}")
        return 130

    elapsed = time.time() - t_start

    # Summary
    print(f"\n{Style.BOLD}━━━ Summary ━━━{Style.RESET}")
    total = result.passed + result.failed
    pass_color = Style.GREEN if result.failed == 0 else Style.YELLOW
    print(f"  {pass_color}{result.passed}/{total} checks passed{Style.RESET} "
          f"in {elapsed:.1f}s")
    if result.failed:
        print(f"  {Style.RED}{result.failed} failures:{Style.RESET}")
        for err in result.errors:
            print(f"    - {err}")
        return 1
    print(f"  {Style.GREEN}All good. Your SCIM endpoint is ready.{Style.RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
