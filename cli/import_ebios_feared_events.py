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
        if isinstance(data, dict):
            results.extend(data.get("results", []))
            url = data.get("next")
        else:
            break
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

    matrices = get_all(api, headers, "risk-matrices")
    if not matrices:
        raise RuntimeError("No risk matrix found")
    matrix_id = matrices[0]["id"]

    assets = get_all(api, headers, "assets")
    asset_by_ref = {str(x.get("ref_id", "")).strip(): x["id"] for x in assets if x.get("ref_id")}

    study_ref = f"EBIOS-{bundle.get('meta', {}).get('risk_assessment_ref_id', '2026-001')}"
    study_name = f"EBIOS Study {bundle.get('meta', {}).get('risk_assessment_ref_id', '2026-001')}"

    studies = get_all(api, headers, "ebios-rm/studies")
    existing_study = next((s for s in studies if str(s.get("ref_id", "")).strip() == study_ref), None)

    study_asset_ids = []
    for fe in bundle.get("feared_events", []):
        for ref in fe.get("asset_ref_ids", []) or []:
            aid = asset_by_ref.get(ref)
            if aid and aid not in study_asset_ids:
                study_asset_ids.append(aid)

    study_payload = {
        "ref_id": study_ref,
        "name": study_name,
        "description": "Imported from JSON bundle",
        "folder": folder_id,
        "risk_matrix": matrix_id,
        "assets": study_asset_ids,
        "status": "in_progress",
        "version": "1.0",
        "observation": "Auto-created from uploaded JSON bundle",
        "quotation_method": "express",
    }

    if existing_study:
        r = requests.patch(f"{api}/ebios-rm/studies/{existing_study['id']}/", headers=headers, data=json.dumps(study_payload, ensure_ascii=False), verify=False, timeout=60)
        r.raise_for_status()
        study = r.json()
    else:
        r = requests.post(f"{api}/ebios-rm/studies/", headers=headers, data=json.dumps(study_payload, ensure_ascii=False), verify=False, timeout=60)
        r.raise_for_status()
        study = r.json()

    study_id = study["id"]

    feared_events = get_all(api, headers, "ebios-rm/feared-events")
    by_ref = {str(x.get("ref_id", "")).strip(): x for x in feared_events if x.get("ref_id")}

    created = 0
    updated = 0
    for fe in bundle.get("feared_events", []):
        ref_id = fe.get("ref_id", "").strip()
        if not ref_id:
            continue
        fe_asset_ids = [asset_by_ref[r] for r in (fe.get("asset_ref_ids") or []) if r in asset_by_ref]
        impact = int(fe.get("business_impact_level", 0) or 0)
        gravity = max(-1, min(3, impact - 1)) if impact else -1
        payload = {
            "ref_id": ref_id,
            "name": fe.get("name", ""),
            "description": fe.get("description", ""),
            "ebios_rm_study": study_id,
            "assets": fe_asset_ids,
            "gravity": gravity,
            "is_selected": True,
            "justification": ", ".join(fe.get("security_criteria", []) or []),
        }
        existing = by_ref.get(ref_id)
        if existing:
            r = requests.patch(f"{api}/ebios-rm/feared-events/{existing['id']}/", headers=headers, data=json.dumps(payload, ensure_ascii=False), verify=False, timeout=60)
            r.raise_for_status()
            updated += 1
        else:
            r = requests.post(f"{api}/ebios-rm/feared-events/", headers=headers, data=json.dumps(payload, ensure_ascii=False), verify=False, timeout=60)
            r.raise_for_status()
            created += 1

    print(f"EBIOS study ready: {study_name}")
    print(f"Feared events imported: created={created}, updated={updated}")


if __name__ == "__main__":
    main()
