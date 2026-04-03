#!/usr/bin/env python3
import json
from pathlib import Path
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ROOT = Path(__file__).resolve().parent


def load_env(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_all(api: str, headers: dict, endpoint: str) -> list[dict]:
    url = f"{api}/{endpoint}/"
    results = []
    while url:
        r = requests.get(url, headers=headers, verify=False, timeout=60)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        url = data.get("next")
    return results


def main() -> None:
    env = load_env(ROOT / ".clica.env")
    api = env["API_URL"].rstrip("/")
    headers = {"Authorization": f"Token {env['TOKEN']}", "Content-Type": "application/json"}
    bundle = json.loads((ROOT / "risk_bundle_fixed.json").read_text(encoding="utf-8"))

    folder_name = bundle.get("meta", {}).get("folder", "Global")
    folders = get_all(api, headers, "folders")
    folder = next((x for x in folders if x.get("name") == folder_name), None)
    if not folder:
        raise RuntimeError(f"Folder not found: {folder_name}")
    folder_id = folder["id"]

    teams = get_all(api, headers, "teams")
    by_name = {t.get("name"): t for t in teams}

    created = 0
    updated = 0
    for rs in bundle.get("risk_sources", []):
        name = rs.get("name", "").strip()
        if not name:
            continue
        desc = rs.get("description", "")
        category = rs.get("category", "")
        payload = {
            "name": name,
            "description": f"[Risk Source] {category}\n{desc}".strip(),
            "folder": folder_id,
            "team_email": None,
            "leader": None,
            "deputies": [],
            "members": [],
        }
        existing = by_name.get(name)
        if existing:
            rid = existing["id"]
            r = requests.patch(f"{api}/teams/{rid}/", headers=headers, data=json.dumps(payload, ensure_ascii=False), verify=False, timeout=60)
            r.raise_for_status()
            updated += 1
        else:
            r = requests.post(f"{api}/teams/", headers=headers, data=json.dumps(payload, ensure_ascii=False), verify=False, timeout=60)
            r.raise_for_status()
            updated_team = r.json()
            by_name[name] = updated_team
            created += 1

    print(f"Risk sources imported as teams: created={created}, updated={updated}")


if __name__ == "__main__":
    main()
