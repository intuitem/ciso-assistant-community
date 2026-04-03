#!/usr/bin/env python3
"""Import a multi-file JSON package into CISO Assistant.

This script:
1) Loads JSON parts from an input directory.
2) Builds risk_bundle_fixed.json for the existing core import workflow.
3) Runs import_complete_json_bundle.py (assets, threats, controls, risk scenarios, feared events, risk sources).
4) Imports EBIOS advanced objects (RO/TO, stakeholders, strategic scenarios, attack paths, operational scenarios).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = Path("E:/")


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def load_json_list(path: Path, required: bool = False) -> list[dict[str, Any]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required file: {path}")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return data


def build_controls_from_mitigation(
    mitigations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    controls_by_ref: dict[str, dict[str, Any]] = {}
    for ms in mitigations:
        name = str(ms.get("name", "")).strip()
        desc = str(ms.get("description", "")).strip()
        labels = [str(x).strip() for x in ms.get("labels", []) if str(x).strip()]
        for ref in ms.get("control_ref_ids", []) or []:
            ref_id = str(ref).strip()
            if not ref_id:
                continue
            if ref_id not in controls_by_ref:
                controls_by_ref[ref_id] = {
                    "ref_id": ref_id,
                    "name": f"{ref_id} - generated from mitigation strategy",
                    "description": f"Generated from mitigation strategy: {name}",
                    "category": "Technique",
                    "status": "Planifie",
                    "owner": "RSSI",
                    "asset_ref_ids": [],
                    "threat_ref_ids": [],
                    "risk_scenario_ref_ids": [],
                    "effectiveness": 3,
                    "labels": labels[:],
                }

            current = controls_by_ref[ref_id]
            current["description"] = desc or current["description"]

            for key in ("threat_ref_ids", "risk_scenario_ref_ids"):
                known = set(current[key])
                for item in ms.get(key, []) or []:
                    item_s = str(item).strip()
                    if item_s and item_s not in known:
                        current[key].append(item_s)
                        known.add(item_s)

            known_labels = set(current["labels"])
            for label in labels:
                if label not in known_labels:
                    current["labels"].append(label)
                    known_labels.add(label)

    return sorted(controls_by_ref.values(), key=lambda x: x["ref_id"])


def choose_risk_origin_name(risk_source: dict[str, Any]) -> str:
    text = " ".join(
        [
            str(risk_source.get("name", "")).lower(),
            str(risk_source.get("description", "")).lower(),
            str(risk_source.get("category", "")).lower(),
            " ".join(str(x).lower() for x in (risk_source.get("labels") or [])),
        ]
    )
    if "apt" in text or "etat" in text or "state" in text:
        return "state"
    if "crime" in text:
        return "organized_crime"
    if "activ" in text or "hacktiv" in text:
        return "activist"
    if "terror" in text:
        return "terrorist"
    if "fourn" in text or "supplier" in text or "supply" in text:
        return "competitor"
    return "other"


class ApiClient:
    def __init__(self, api_url: str, token: str) -> None:
        self.api = api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        }

    def get_all(self, endpoint: str) -> list[dict[str, Any]]:
        url = f"{self.api}/{endpoint.strip('/')}/"
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        while url:
            if url in seen:
                break
            seen.add(url)
            r = requests.get(url, headers=self.headers, verify=False, timeout=90)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                out.extend(data.get("results", []))
                url = data.get("next")
            elif isinstance(data, list):
                out.extend(data)
                url = None
            else:
                url = None
        return out

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        r = requests.get(
            f"{self.api}/{endpoint.strip('/')}/",
            headers=self.headers,
            params=params or {},
            verify=False,
            timeout=90,
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"GET {endpoint} failed ({r.status_code}): {r.text}"
            )
        return r.json()

    def find_first_by_ref(self, endpoint: str, ref_id: str) -> dict[str, Any] | None:
        data = self.get(endpoint, params={"ref_id": ref_id})
        if isinstance(data, dict):
            items = data.get("results", [])
            return items[0] if items else None
        if isinstance(data, list) and data:
            return data[0]
        return None

    def create(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        r = requests.post(
            f"{self.api}/{endpoint.strip('/')}/",
            headers=self.headers,
            data=json.dumps(payload, ensure_ascii=False),
            verify=False,
            timeout=90,
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"POST {endpoint} failed ({r.status_code}): {r.text}"
            )
        return r.json()

    def update(
        self, endpoint: str, object_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        r = requests.patch(
            f"{self.api}/{endpoint.strip('/')}/{object_id}/",
            headers=self.headers,
            data=json.dumps(payload, ensure_ascii=False),
            verify=False,
            timeout=90,
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"PATCH {endpoint}/{object_id} failed ({r.status_code}): {r.text}"
            )
        return r.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import EBIOS package from multiple JSON files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing JSON files (assets.json, threats.json, etc.).",
    )
    parser.add_argument("--folder", default="Global")
    parser.add_argument("--perimeter", default="Global Perimeter")
    parser.add_argument("--matrix", default="4x4 risk matrix from EBIOS-RM")
    parser.add_argument(
        "--extras-only",
        action="store_true",
        help="Skip core Data Wizard imports and only import EBIOS extras (RO/TO, stakeholders, strategic, operational).",
    )
    parser.add_argument(
        "--skip-extras",
        action="store_true",
        help="Run only core imports and skip EBIOS extras.",
    )
    parser.add_argument(
        "--skip-feared-events",
        action="store_true",
        help="Skip feared-events import step (useful for reruns when they already exist).",
    )
    return parser.parse_args()


def build_bundle_from_parts(input_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    assets = load_json_list(input_dir / "assets.json", required=True)
    risk_sources = load_json_list(input_dir / "risk_sources.json", required=True)
    threats = load_json_list(input_dir / "threats.json", required=True)
    feared_events = load_json_list(input_dir / "risk_events.json", required=True)
    risk_scenarios = load_json_list(input_dir / "risk_scenarios.json", required=True)

    controls = load_json_list(input_dir / "controls.json", required=False)
    if not controls:
        mitigations = load_json_list(input_dir / "mitigation_strategies.json")
        if not mitigations:
            mitigations = load_json_list(input_dir / "mitigation_strateghies.json")
        controls = build_controls_from_mitigation(mitigations)

    ra_ref = "RA-2026-001"
    for item in risk_scenarios:
        found = str(item.get("risk_assessment_ref_id", "")).strip()
        if found:
            ra_ref = found
            break

    bundle = {
        "meta": {
            "folder": "Global",
            "threat_library": "urn:intuitem:risk:library:intuitem-common-catalog",
            "risk_assessment_ref_id": ra_ref,
            "generated_at": "2026-04-03",
        },
        "assets": assets,
        "risk_sources": risk_sources,
        "threats": threats,
        "feared_events": feared_events,
        "risk_scenarios": risk_scenarios,
        "controls": controls,
    }

    extras = {
        "stakeholders": load_json_list(input_dir / "stakeholders.json"),
        "target_objectives": load_json_list(input_dir / "target_objectives.json"),
        "ro_to_pairs": load_json_list(input_dir / "ro_to_pairs.json"),
        "strategic_scenarios": load_json_list(input_dir / "strategic_scenarios.json"),
        "operational_scenarios": load_json_list(input_dir / "operational_scenarios.json"),
        "risk_register": load_json_list(input_dir / "risk_register.json"),
        "mitigation_strategies": load_json_list(input_dir / "mitigation_strategies.json")
        or load_json_list(input_dir / "mitigation_strateghies.json"),
        "compliance_controls": load_json_list(input_dir / "compliance_controls.json"),
        "audits": load_json_list(input_dir / "audits.json"),
    }
    return bundle, extras


def run_core_import(folder: str, perimeter: str, matrix: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "bundle_to_csv.py")], cwd=ROOT, check=True)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "clica.py"),
            "import-assets",
            "--file",
            ".\\bundle_assets.csv",
            "--folder",
            folder,
            "--on-conflict",
            "update",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "clica.py"),
            "import-threats",
            "--file",
            ".\\bundle_threats.csv",
            "--folder",
            folder,
            "--on-conflict",
            "update",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "clica.py"),
            "import-applied-controls",
            "--file",
            ".\\bundle_controls.csv",
            "--folder",
            folder,
            "--on-conflict",
            "update",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "bundle_risk_assessment_csv.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "clica.py"),
            "import-risk-assessment",
            "--file",
            ".\\bundle_risk_assessment.csv",
            "--perimeter",
            perimeter,
            "--matrix",
            matrix,
            "--on-conflict",
            "update",
        ],
        cwd=ROOT,
        check=True,
    )


def pick_matrix_id(api: ApiClient, matrix_name: str) -> str:
    matrices = api.get_all("risk-matrices")
    if not matrices:
        raise RuntimeError("No risk matrix found")
    selected = next((m for m in matrices if str(m.get("name", "")) == matrix_name), None)
    if selected:
        return selected["id"]
    return matrices[0]["id"]


def import_risk_sources_as_teams(
    api: ApiClient, folder_id: str, risk_sources: list[dict[str, Any]]
) -> None:
    teams = [x for x in api.get_all("teams") if x.get("folder") == folder_id]
    by_name = {str(x.get("name", "")).strip(): x for x in teams}

    for source in risk_sources:
        name = str(source.get("name", "")).strip()
        if not name:
            continue
        payload = {
            "name": name,
            "description": f"[Risk Source] {source.get('category', '')}\n{source.get('description', '')}".strip(),
            "folder": folder_id,
            "team_email": None,
            "leader": None,
            "deputies": [],
            "members": [],
        }
        existing = by_name.get(name)
        if existing:
            api.update("teams", existing["id"], payload)
        else:
            created = api.create("teams", payload)
            by_name[name] = created


def import_feared_events(
    api: ApiClient,
    bundle: dict[str, Any],
    folder_id: str,
    study_id: str,
) -> None:
    print("  - importing feared events (asset linking optional)")
    existing_feared = [
        x for x in api.get_all("ebios-rm/feared-events") if x.get("ebios_rm_study") == study_id
    ]
    feared_by_ref = {
        str(x.get("ref_id", "")).strip(): x for x in existing_feared if x.get("ref_id")
    }
    feared_by_name = {
        str(x.get("name", "")).strip(): x for x in existing_feared if x.get("name")
    }

    for fe in bundle.get("feared_events", []):
        ref_id = str(fe.get("ref_id", "")).strip()
        if not ref_id:
            continue
        asset_ids: list[str] = []
        impact = int(fe.get("business_impact_level", 0) or 0)
        gravity = max(-1, min(3, impact - 1)) if impact else -1
        payload = {
            "ref_id": ref_id,
            "name": str(fe.get("name", "")).strip() or ref_id,
            "description": str(fe.get("description", "")),
            "ebios_rm_study": study_id,
            "assets": asset_ids,
            "gravity": gravity,
            "is_selected": True,
            "justification": ", ".join(str(x) for x in (fe.get("security_criteria") or [])),
        }
        existing = feared_by_ref.get(ref_id)
        if not existing:
            existing = feared_by_name.get(payload["name"])
        if existing:
            api.update("ebios-rm/feared-events", existing["id"], payload)
        else:
            created = api.create("ebios-rm/feared-events", payload)
            feared_by_ref[ref_id] = created
            feared_by_name[payload["name"]] = created
    print(f"  - feared events processed: {len(bundle.get('feared_events', []))}")


def import_ebios_extras(
    api: ApiClient, bundle: dict[str, Any], extras: dict[str, Any]
) -> dict[str, int]:
    counts = {
        "ro_to": 0,
        "stakeholders": 0,
        "strategic": 0,
        "attack_paths": 0,
        "operational": 0,
    }

    print("  - resolving folder and study")
    folder_name = bundle["meta"].get("folder", "Global")
    study_ref = f"EBIOS-{bundle['meta'].get('risk_assessment_ref_id', '2026-001')}"

    folders = api.get_all("folders")
    folder = next((x for x in folders if x.get("name") == folder_name), None)
    if not folder:
        raise RuntimeError(f"Folder not found: {folder_name}")
    folder_id = folder["id"]

    studies = api.get_all("ebios-rm/studies")
    study = next((x for x in studies if str(x.get("ref_id", "")) == study_ref), None)
    if not study:
        raise RuntimeError(f"EBIOS study not found: {study_ref}")
    study_id = study["id"]

    feared_events = [
        x for x in api.get_all("ebios-rm/feared-events") if x.get("ebios_rm_study") == study_id
    ]
    feared_by_ref = {str(x.get("ref_id", "")).strip(): x for x in feared_events}

    print("  - loading terminology and reference objects")
    terminology = api.get_all("terminologies")
    roto_terms = {
        str(x.get("name", "")): x
        for x in terminology
        if x.get("field_path") == "ro_to.risk_origin"
    }
    stakeholder_terms = {
        str(x.get("name", "")): x
        for x in terminology
        if x.get("field_path") == "entity.relationship"
    }

    def _create_visible_term(field_path: str, base_name: str) -> dict[str, Any]:
        # Some instances hide built-in terms; create an importer-scoped visible fallback.
        for idx in range(0, 40):
            suffix = "" if idx == 0 else f"_{idx}"
            candidate = f"import_{base_name}{suffix}"
            payload = {
                "field_path": field_path,
                "name": candidate,
                "locale": "en",
                "is_visible": True,
            }
            try:
                return api.create("terminologies", payload)
            except RuntimeError as exc:
                if "already used in this scope" in str(exc):
                    continue
                raise
        raise RuntimeError(f"Unable to create visible terminology for {field_path}")

    default_roto = roto_terms.get("other")
    if not default_roto and roto_terms:
        default_roto = next(iter(roto_terms.values()))
    if not default_roto:
        default_roto = _create_visible_term("ro_to.risk_origin", "other")
        roto_terms[str(default_roto.get("name", ""))] = default_roto

    default_stakeholder = stakeholder_terms.get("other")
    if not default_stakeholder and stakeholder_terms:
        default_stakeholder = next(iter(stakeholder_terms.values()))
    if not default_stakeholder:
        default_stakeholder = _create_visible_term("entity.relationship", "other")
        stakeholder_terms[str(default_stakeholder.get("name", ""))] = default_stakeholder

    risk_sources = {
        str(x.get("ref_id", "")).strip(): x for x in bundle.get("risk_sources", [])
    }
    target_objectives = {
        str(x.get("ref_id", "")).strip(): x for x in extras.get("target_objectives", [])
    }

    risk_scenarios = bundle.get("risk_scenarios", [])
    feared_refs_by_to_ref: dict[str, set[str]] = {}
    for to_ref, target in target_objectives.items():
        to_assets = set(str(a).strip() for a in target.get("asset_ref_ids", []) if str(a).strip())
        feared_refs_by_to_ref[to_ref] = set()
        for scenario in risk_scenarios:
            scenario_assets = set(str(a).strip() for a in scenario.get("asset_ref_ids", []) if str(a).strip())
            if to_assets & scenario_assets:
                for fe_ref in scenario.get("feared_event_ref_ids", []) or []:
                    fe_ref_s = str(fe_ref).strip()
                    if fe_ref_s:
                        feared_refs_by_to_ref[to_ref].add(fe_ref_s)

    existing_ro_to = [x for x in api.get_all("ebios-rm/ro-to") if x.get("ebios_rm_study") == study_id]
    ro_to_by_key = {
        (str(x.get("risk_origin")), str(x.get("target_objective", ""))): x
        for x in existing_ro_to
    }
    ro_to_by_ref: dict[str, dict[str, Any]] = {}

    print("  - importing RO/TO pairs")
    for pair in extras.get("ro_to_pairs", []):
        pair_ref = str(pair.get("ref_id", "")).strip()
        rs_ref = str(pair.get("risk_origin_ref_id", "")).strip()
        to_ref = str(pair.get("target_objective_ref_id", "")).strip()
        risk_source = risk_sources.get(rs_ref, {})
        target_objective = target_objectives.get(to_ref, {})

        chosen_name = choose_risk_origin_name(risk_source)
        risk_origin = roto_terms.get(chosen_name)
        if not risk_origin:
            risk_origin = _create_visible_term("ro_to.risk_origin", chosen_name)
            roto_terms[str(risk_origin.get("name", ""))] = risk_origin
        target_objective_text = str(target_objective.get("name", to_ref)).strip() or to_ref

        plausibility = clamp(int(pair.get("plausibility", 2) or 2), 1, 4)
        linked_feared_ids: list[str] = []
        for fe_ref in feared_refs_by_to_ref.get(to_ref, set()):
            fe = feared_by_ref.get(fe_ref)
            if fe:
                linked_feared_ids.append(fe["id"])

        payload = {
            "ebios_rm_study": study_id,
            "risk_origin": risk_origin["id"],
            "target_objective": target_objective_text,
            "motivation": plausibility,
            "resources": plausibility,
            "activity": plausibility,
            "is_selected": True,
            "justification": str(pair.get("justification", "")),
            "feared_events": linked_feared_ids,
        }

        key = (str(risk_origin["id"]), target_objective_text)
        existing = ro_to_by_key.get(key)
        if existing:
            current = api.update("ebios-rm/ro-to", existing["id"], payload)
        else:
            current = api.create("ebios-rm/ro-to", payload)
            ro_to_by_key[key] = current

        ro_to_by_ref[pair_ref] = current
        counts["ro_to"] += 1

    entities = [x for x in api.get_all("entities") if x.get("folder") == folder_id]
    entity_by_name = {str(x.get("name", "")).strip(): x for x in entities}

    existing_stakeholders = [
        x for x in api.get_all("ebios-rm/stakeholders") if x.get("ebios_rm_study") == study_id
    ]
    stakeholder_by_entity: dict[str, dict[str, Any]] = {
        str(x.get("entity")): x for x in existing_stakeholders
    }
    stakeholder_by_ref: dict[str, dict[str, Any]] = {}

    print("  - importing stakeholders")
    for item in extras.get("stakeholders", []):
        ref_id = str(item.get("ref_id", "")).strip()
        entity_name = str(item.get("name", "")).strip()
        if not entity_name:
            continue

        entity = entity_by_name.get(entity_name)
        if not entity:
            entity_payload = {
                "name": entity_name,
                "folder": folder_id,
                "description": str(item.get("role", "")),
                "default_dependency": clamp(int(item.get("criticality", 2) or 2), 0, 4),
                "default_penetration": clamp(int(item.get("criticality", 2) or 2), 0, 4),
                "default_maturity": 1,
                "default_trust": 1,
                "is_active": True,
            }
            entity = api.create("entities", entity_payload)
            entity_by_name[entity_name] = entity

        stakeholder_type = str(item.get("type", "")).lower()
        if "externe" in stakeholder_type or "external" in stakeholder_type:
            rel_key = "supplier"
        else:
            rel_key = "contractor"
        rel = stakeholder_terms.get(rel_key)
        if not rel:
            rel = _create_visible_term("entity.relationship", rel_key)
            stakeholder_terms[str(rel.get("name", ""))] = rel

        crit = clamp(int(item.get("criticality", 2) or 2), 1, 4)
        payload = {
            "ebios_rm_study": study_id,
            "entity": entity["id"],
            "category": rel["id"],
            "current_dependency": crit,
            "current_penetration": max(0, crit - 1),
            "current_maturity": 1,
            "current_trust": 1,
            "is_selected": True,
            "justification": str(item.get("role", "")),
        }

        existing = stakeholder_by_entity.get(str(entity["id"]))
        if existing:
            current = api.update("ebios-rm/stakeholders", existing["id"], payload)
        else:
            current = api.create("ebios-rm/stakeholders", payload)

        if ref_id:
            stakeholder_by_ref[ref_id] = current
        counts["stakeholders"] += 1

    existing_strategic = [
        x
        for x in api.get_all("ebios-rm/strategic-scenarios")
        if x.get("ebios_rm_study") == study_id
    ]
    strategic_by_ref = {
        str(x.get("ref_id", "")).strip(): x for x in existing_strategic if x.get("ref_id")
    }

    print("  - importing strategic scenarios")
    for item in extras.get("strategic_scenarios", []):
        ref_id = str(item.get("ref_id", "")).strip()
        ro_ref = ""
        for candidate in item.get("ro_to_pair_ref_ids", []) or []:
            c = str(candidate).strip()
            if c in ro_to_by_ref:
                ro_ref = c
                break
        if not ro_ref:
            continue

        ro_obj = ro_to_by_ref[ro_ref]
        focused = None
        for fe in feared_events:
            if fe.get("ebios_rm_study") == study_id and fe.get("is_selected"):
                focused = fe
                break

        payload = {
            "ref_id": ref_id,
            "name": str(item.get("name", "")).strip() or ref_id,
            "description": str(item.get("description", "")),
            "ebios_rm_study": study_id,
            "ro_to_couple": ro_obj["id"],
            "focused_feared_event": focused["id"] if focused else None,
        }

        existing = strategic_by_ref.get(ref_id)
        if existing:
            current = api.update("ebios-rm/strategic-scenarios", existing["id"], payload)
        else:
            current = api.create("ebios-rm/strategic-scenarios", payload)
        strategic_by_ref[ref_id] = current
        counts["strategic"] += 1

    needed_threat_refs: set[str] = set()
    for scenario in bundle.get("risk_scenarios", []):
        for ref in scenario.get("threat_ref_ids", []) or []:
            ref_s = str(ref).strip()
            if ref_s:
                needed_threat_refs.add(ref_s)

    threat_by_ref: dict[str, dict[str, Any]] = {}
    for ref in sorted(needed_threat_refs):
        obj = api.find_first_by_ref("threats", ref)
        if obj:
            threat_by_ref[ref] = obj

    attack_paths = [
        x for x in api.get_all("ebios-rm/attack-paths") if x.get("ebios_rm_study") == study_id
    ]
    attack_by_ref = {str(x.get("ref_id", "")).strip(): x for x in attack_paths if x.get("ref_id")}

    operational = [
        x
        for x in api.get_all("ebios-rm/operational-scenarios")
        if x.get("ebios_rm_study") == study_id
    ]
    operational_by_attack = {str(x.get("attack_path")): x for x in operational}

    print("  - importing attack paths and operational scenarios")
    for item in extras.get("operational_scenarios", []):
        ref_id = str(item.get("ref_id", "")).strip()
        ss_ref = str(item.get("strategic_scenario_ref_id", "")).strip()
        strategic = strategic_by_ref.get(ss_ref)
        if not strategic:
            continue

        stakeholder_ids: list[str] = []
        source_ss = next(
            (
                s
                for s in extras.get("strategic_scenarios", [])
                if str(s.get("ref_id", "")).strip() == ss_ref
            ),
            {},
        )
        for sid in source_ss.get("stakeholder_ref_ids", []) or []:
            sid_s = str(sid).strip()
            if sid_s in stakeholder_by_ref:
                stakeholder_ids.append(stakeholder_by_ref[sid_s]["id"])

        path_ref = f"AP-{ref_id}" if ref_id else ""
        path_payload = {
            "ref_id": path_ref,
            "name": str(item.get("name", "")).strip() or path_ref,
            "description": str(item.get("description", "")),
            "ebios_rm_study": study_id,
            "strategic_scenario": strategic["id"],
            "stakeholders": stakeholder_ids,
            "is_selected": True,
            "justification": " | ".join(
                str(x).strip() for x in (item.get("attack_path_steps") or []) if str(x).strip()
            ),
        }

        existing_path = attack_by_ref.get(path_ref)
        if existing_path:
            path_obj = api.update("ebios-rm/attack-paths", existing_path["id"], path_payload)
        else:
            path_obj = api.create("ebios-rm/attack-paths", path_payload)
        attack_by_ref[path_ref] = path_obj
        counts["attack_paths"] += 1

        threat_ids: list[str] = []
        source_rs_ref = None
        for rs in bundle.get("risk_scenarios", []):
            if str(rs.get("ref_id", "")).strip() == str(ref_id).replace("OS", "SC"):
                source_rs_ref = rs
                break
        if source_rs_ref:
            for tref in source_rs_ref.get("threat_ref_ids", []) or []:
                t = threat_by_ref.get(str(tref).strip())
                if t:
                    threat_ids.append(t["id"])

        op_payload = {
            "ebios_rm_study": study_id,
            "attack_path": path_obj["id"],
            "threats": threat_ids,
            "operating_modes_description": " | ".join(
                str(x).strip() for x in (item.get("attack_path_steps") or []) if str(x).strip()
            ),
            "likelihood": clamp(int(item.get("likelihood", 2) or 2) - 1, 0, 3),
            "is_selected": True,
            "justification": str(item.get("description", "")),
        }

        existing_op = operational_by_attack.get(str(path_obj["id"]))
        if existing_op:
            api.update("ebios-rm/operational-scenarios", existing_op["id"], op_payload)
        else:
            api.create("ebios-rm/operational-scenarios", op_payload)
        counts["operational"] += 1

    return counts


def main() -> None:
    args = parse_args()

    bundle, extras = build_bundle_from_parts(args.input_dir)
    (ROOT / "risk_bundle_fixed.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "ebios_extras_fixed.json").write_text(
        json.dumps(extras, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not args.extras_only:
        print("== Core import: assets/threats/controls/risk scenarios ==")
        run_core_import(args.folder, args.perimeter, args.matrix)

    env = load_env(ROOT / ".clica.env")
    api = ApiClient(env["API_URL"], env["TOKEN"])

    folders = api.get_all("folders")
    folder = next((x for x in folders if x.get("name") == args.folder), None)
    if not folder:
        raise RuntimeError(f"Folder not found: {args.folder}")
    folder_id = folder["id"]

    print("== Import risk sources as teams ==")
    import_risk_sources_as_teams(api, folder_id, bundle.get("risk_sources", []))

    matrix_id = pick_matrix_id(api, args.matrix)
    study_ref = f"EBIOS-{bundle['meta'].get('risk_assessment_ref_id', '2026-001')}"
    study_payload = {
        "ref_id": study_ref,
        "name": f"EBIOS Study {bundle['meta'].get('risk_assessment_ref_id', '2026-001')}",
        "description": "Imported from JSON package",
        "folder": folder_id,
        "risk_matrix": matrix_id,
        "status": "in_progress",
        "version": "1.0",
        "observation": "Automated import from multi-file JSON package",
        "quotation_method": "express",
    }
    studies = api.get_all("ebios-rm/studies")
    study = next((x for x in studies if str(x.get("ref_id", "")) == study_ref), None)
    if study:
        study = api.update("ebios-rm/studies", study["id"], study_payload)
    else:
        study = api.create("ebios-rm/studies", study_payload)

    if args.skip_feared_events:
        print("== Skipping feared events import ==")
    else:
        print("== Import feared events into EBIOS study ==")
        import_feared_events(api, bundle, folder_id, study["id"])

    counts = {
        "ro_to": 0,
        "stakeholders": 0,
        "strategic": 0,
        "attack_paths": 0,
        "operational": 0,
    }
    if not args.skip_extras:
        print("== Import EBIOS extras: RO/TO, stakeholders, strategic, operational ==")
        counts = import_ebios_extras(api, bundle, extras)

    print("== EBIOS JSON package import completed ==")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
