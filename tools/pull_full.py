#!/usr/bin/env python3
"""Pull all objects of a CISO Assistant model from the API as full JSON.

The `list` endpoint returns a lightweight serializer that drops per-row fields.
Full fidelity comes either from the detail endpoint one object per call
(--mode detail, fetched concurrently) or from the bulk `/{resource}/full/`
endpoint in a single request (--mode bulk). --resource can be any model that
exposes a `/full/` action (e.g. applied-controls, assets).

Dev-only utility: --ca-bundle defaults to "false" (TLS verification off) for
localhost. Point it at a CA bundle before using against any real host.

Every flag also reads from an env var, so `export CISO_* ...; python pull_full.py`
still works; the flag wins when both are set. Run with --help for the full list.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Set by main() from parsed args, used by the worker functions below.
BASE = RESOURCE = OUTPUT = MODE = ""
WORKERS = 4
session = None


def build_parser():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--base",
        default=os.environ.get("CISO_API_BASE", "http://localhost:8000/api"),
        help="API base URL [env CISO_API_BASE]",
    )
    p.add_argument(
        "--pat",
        default=os.environ.get("CISO_PAT", ""),
        help="Personal Access Token; prefer the env var to keep it out of "
        "shell history [env CISO_PAT]",
    )
    p.add_argument(
        "--resource",
        default=os.environ.get("CISO_RESOURCE", "applied-controls"),
        help="url model exposing /full/, e.g. applied-controls, assets "
        "[env CISO_RESOURCE]",
    )
    p.add_argument(
        "--mode",
        choices=["detail", "bulk"],
        default=os.environ.get("CISO_MODE", "detail"),
        help="detail = N+1 per-id fetches (concurrent); bulk = single "
        "/full/ request [env CISO_MODE]",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("CISO_WORKERS", "4")),
        help="concurrent workers for detail mode [env CISO_WORKERS]",
    )
    p.add_argument(
        "--output",
        default=os.environ.get("CISO_OUTPUT", ""),
        help="output JSON path (default: <resource>_full.json) [env CISO_OUTPUT]",
    )
    p.add_argument(
        "--ca-bundle",
        default=os.environ.get("CISO_CA_BUNDLE", "false"),
        help='TLS: CA bundle path, "true", or "false" (dev, no verify) '
        "[env CISO_CA_BUNDLE]",
    )
    return p


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


def run():
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


def main():
    args = build_parser().parse_args()
    if not args.pat:
        sys.exit("PAT not set; pass --pat or export CISO_PAT.")

    global BASE, RESOURCE, OUTPUT, WORKERS, MODE, session
    BASE = args.base
    RESOURCE = args.resource
    OUTPUT = args.output or f"{RESOURCE.replace('-', '_')}_full.json"
    WORKERS = args.workers
    MODE = args.mode

    # Normalize: "false" -> False, "true" -> True, else treat as CA bundle path
    verify = args.ca_bundle
    if verify.lower() == "false":
        verify = False
    elif verify.lower() == "true":
        verify = True

    session = requests.Session()
    session.headers.update({"Authorization": f"Token {args.pat}"})
    session.verify = verify
    # reuse connections across threads (keep-alive + reused TLS handshake)
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=WORKERS, pool_maxsize=WORKERS
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    run()


if __name__ == "__main__":
    main()
