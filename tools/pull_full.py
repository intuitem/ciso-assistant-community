#!/usr/bin/env python3
"""Pull all objects of a CISO Assistant model from the API as full JSON.

The `list` endpoint returns a lightweight serializer that drops per-row fields.
Full fidelity comes either from the detail endpoint one object per call
(MODE=detail, fetched concurrently) or from the bulk `/{resource}/full/`
endpoint in a single request (MODE=bulk). Set CISO_RESOURCE to any model that
exposes a `/full/` action (e.g. applied-controls, assets).

Usage:
    export CISO_API_BASE="https://localhost:8443/api"
    export CISO_PAT="your-personal-access-token"
    export CISO_RESOURCE="applied-controls"   # or "assets"
    export CISO_MODE="bulk"                    # or "detail"
    python pull_full.py
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE = os.environ.get("CISO_API_BASE", "http://localhost:8000/api")
PAT = os.environ.get("CISO_PAT", "")
VERIFY = os.environ.get("CISO_CA_BUNDLE", "false")  # path to CA bundle, or "false"
# url model to pull, e.g. "applied-controls" or "assets" (both expose /full/)
RESOURCE = os.environ.get("CISO_RESOURCE", "applied-controls")
OUTPUT = os.environ.get("CISO_OUTPUT", f"{RESOURCE.replace('-', '_')}_full.json")
WORKERS = int(os.environ.get("CISO_WORKERS", "4"))
# "detail" = N+1 per-id fetches; "bulk" = single /{resource}/full/ endpoint
MODE = os.environ.get("CISO_MODE", "detail")

if not PAT:
    sys.exit("CISO_PAT is not set; export your Personal Access Token first.")

# Normalize VERIFY: "false" -> False, "true" -> True, else treat as CA bundle path
if VERIFY.lower() == "false":
    VERIFY = False
elif VERIFY.lower() == "true":
    VERIFY = True

session = requests.Session()
session.headers.update({"Authorization": f"Token {PAT}"})
session.verify = VERIFY
# reuse connections across threads (keep-alive + reused TLS handshake)
adapter = requests.adapters.HTTPAdapter(pool_connections=WORKERS, pool_maxsize=WORKERS)
session.mount("https://", adapter)
session.mount("http://", adapter)


def get_all_ids(limit=5000):
    ids, offset = [], 0
    while True:
        r = session.get(
            f"{BASE}/{RESOURCE}/",
            params={"limit": limit, "offset": offset},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        ids.extend(item["id"] for item in data["results"])
        if not data.get("next"):
            return ids
        offset += limit


def fetch_detail(obj_id):
    r = session.get(f"{BASE}/{RESOURCE}/{obj_id}/", timeout=120)
    r.raise_for_status()
    return r.json()


def fetch_full_bulk(limit=5000):
    """Pull full-detail records via the single bulk endpoint, paginated."""
    results, offset = [], 0
    while True:
        r = session.get(
            f"{BASE}/{RESOURCE}/full/",
            params={"limit": limit, "offset": offset},
            timeout=300,
        )
        r.raise_for_status()
        data = r.json()
        results.extend(data["results"])
        if not data.get("next"):
            return results
        offset += limit


def run_bulk():
    t0 = time.perf_counter()
    results = fetch_full_bulk()
    elapsed = time.perf_counter() - t0
    return results, elapsed


def run_detail():
    t0 = time.perf_counter()
    ids = get_all_ids()
    t_ids = time.perf_counter() - t0
    print(
        f"Fetching {len(ids)} {RESOURCE} with {WORKERS} workers...",
        file=sys.stderr,
    )
    t0 = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_detail, i): i for i in ids}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                print(f"  failed {futures[fut]}: {e}", file=sys.stderr)
    elapsed = time.perf_counter() - t0
    return results, elapsed, t_ids


def main():
    t_start = time.perf_counter()
    t_ids = None

    if MODE == "bulk":
        print(f"Fetching {RESOURCE} via bulk endpoint...", file=sys.stderr)
        results, t_fetch = run_bulk()
    else:
        results, t_fetch, t_ids = run_detail()

    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    t_total = time.perf_counter() - t_start
    n = len(results)
    throughput = (n / t_fetch) if t_fetch else 0.0
    print(f"Wrote {n} records to {OUTPUT}", file=sys.stderr)
    print(f"--- timing (mode={MODE}) ---", file=sys.stderr)
    if t_ids is not None:
        print(f"  id list fetch : {t_ids:.3f}s", file=sys.stderr)
        # effective per-request server latency, only meaningful at WORKERS=1
        per_req_ms = (t_fetch / n * WORKERS * 1000) if n else 0.0
        print(f"  detail fetch  : {t_fetch:.3f}s for {n} records", file=sys.stderr)
        print(
            f"                  {throughput:.1f} req/s, "
            f"~{per_req_ms:.0f} ms/request server-side ({WORKERS} workers)",
            file=sys.stderr,
        )
    else:
        print(f"  bulk fetch    : {t_fetch:.3f}s for {n} records", file=sys.stderr)
        print(f"                  {throughput:.0f} records/s", file=sys.stderr)
    print(f"  total         : {t_total:.3f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
