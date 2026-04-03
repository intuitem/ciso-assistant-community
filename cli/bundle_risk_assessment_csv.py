#!/usr/bin/env python3
import csv
import json
from pathlib import Path

bundle = json.loads(Path("risk_bundle_fixed.json").read_text(encoding="utf-8"))
out = Path("bundle_risk_assessment.csv")

control_name_by_ref = {c.get("ref_id", ""): c.get("name", "") for c in bundle.get("controls", [])}

with out.open("w", newline="", encoding="utf-8") as f:
    cols = [
        "ref_id",
        "name",
        "description",
        "inherent_impact",
        "inherent_proba",
        "current_impact",
        "current_proba",
        "residual_impact",
        "residual_proba",
        "treatment",
        "existing_applied_controls",
        "additional_controls",
        "filtering_labels",
    ]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for s in bundle.get("risk_scenarios", []):
        ctrl_names = []
        for c in bundle.get("controls", []):
            if s.get("ref_id", "") in (c.get("risk_scenario_ref_ids") or []):
                name = c.get("name", "")
                if name:
                    ctrl_names.append(name)

        # Keep values empty so Data Wizard doesn't fail matrix label mapping differences.
        # Scenario gets created and can be scored in UI.
        w.writerow(
            {
                "ref_id": str(s.get("ref_id", ""))[:100],
                "name": s.get("name", ""),
                "description": s.get("description", ""),
                "inherent_impact": "",
                "inherent_proba": "",
                "current_impact": "",
                "current_proba": "",
                "residual_impact": "",
                "residual_proba": "",
                "treatment": "mitigate",
                "existing_applied_controls": "",
                "additional_controls": "\n".join(ctrl_names),
                "filtering_labels": "",
            }
        )

print(out)
