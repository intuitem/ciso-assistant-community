from core.helpers import soa_rows


def test_soa_rows_flattens_assessable_nodes_in_order_and_localizes():
    tree = {
        "a5": {
            "ref_id": "A.5",
            "name": "Organizational controls",
            "assessable": False,
            "children": {
                "a51": {
                    "ref_id": "A.5.1",
                    "name": "Policies for information security",
                    "assessable": True,
                    "selected": True,
                    "observation": "Required by the ISMS scope",
                    "result": "partially_compliant",
                    "applied_controls": [
                        {"ref_id": "POL-1", "name": "ISP", "status": "active"}
                    ],
                    "risk_scenarios": [{"name": "Ransomware"}],
                    "children": {},
                },
                "a52": {
                    "ref_id": "A.5.2",
                    "name": "Roles",
                    "assessable": True,
                    "selected": True,  # N/A result wins, as on the SoA page
                    "observation": "",
                    "result": "not_applicable",
                    "applied_controls": [],
                    "risk_scenarios": [],
                    "children": {},
                },
            },
        }
    }
    rows = soa_rows(tree, "fr")
    assert [r["Réf."] for r in rows] == ["A.5.1", "A.5.2"]
    assert rows[0]["Applicable"] == "Oui"
    assert rows[0]["Résultat de conformité"] == "Partiellement conforme"
    assert rows[0]["Mesures appliquées (statut)"] == "POL-1 ISP (Actif)"
    assert rows[0]["Scénarios de risque liés"] == "Ransomware"
    assert rows[1]["Applicable"] == "Non"
    assert soa_rows(tree, "xx")[0]["Ref"] == "A.5.1"  # unknown locale -> English
    de = soa_rows(tree, "de")[0]
    assert de["Konformitätsergebnis"] == "Teilweise konform"
    assert de["Umgesetzte Maßnahmen (Status)"] == "POL-1 ISP (Aktiv)"
