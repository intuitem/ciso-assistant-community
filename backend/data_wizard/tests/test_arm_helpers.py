"""
Regression tests for the ARM importer against the sheet naming used by ARM
exports without the "Base de" prefix.
"""

import io

import pytest
from openpyxl import Workbook

from data_wizard.arm_helpers import find_measure_sheets, find_sheet, process_arm_file
from data_wizard.tests.test_templates import ebios_4x4_matrix  # noqa: F401

FR_SHEETS = {
    "1 - Missions": [
        ["", "✓/❒", "Mission", "Valeurs métier", "Paramètres", "Description"],
        [],
        ["1", "✔", "Fabriquer des vaccins", "", "", ""],
    ],
    "1 - Valeurs métier": [
        ["", "✓/❒", "Nom", "Abrév.", "Nature", "Biens supports", "Description"],
        [],
        ["1", "✔", "R&D", "VM01", "Processus", "• Serveurs", "Recherche"],
    ],
    "1 - Biens supports": [
        ["", "✓/❒", "Nom", "Abrév.", "Bien support parent", "Description"],
        [],
        ["1", "✔", "Serveurs", "BS01", "", "Serveurs bureautiques"],
    ],
    "1 - Échelle de gravité": [
        ["", "✓/❒", "Niveau", "Nom", "Description"],
        [],
        ["1", "✔", "1", "Mineure", ""],
        ["2", "✔", "2", "Significative", ""],
        ["3", "✔", "3", "Grave", ""],
    ],
    "1 - Évènements redoutés": [
        [
            "",
            "✓/❒",
            "Valeurs métier",
            "Évènement redouté",
            "Abrév.",
            "Impacts",
            "Gravité retenue",
        ],
        [],
        [
            "1",
            "✔",
            "• R&D",
            "Perte des données",
            "ER01",
            "• Impacts juridiques",
            "Grave",
        ],
    ],
    "1 - Référentiel de sécurité X": [
        [
            "",
            "✓/❒",
            "Réf.",
            "Nom",
            "Type",
            "Réduction de la gravité",
            "Description",
            "Statut",
        ],
        [],
        ["1", "✔", "M1", "Sensibilisation", "Gouvernance", "0 %", "", "En cours"],
    ],
}

EN_SHEETS = {
    "1 - Missions": [
        ["", "✓/❒", "Mission", "Business assets", "Parameters", "Description"],
        [],
        ["1", "✔", "Manufacture vaccines", "", "", ""],
    ],
    "1 - Business assets": [
        ["", "✓/❒", "Name", "Short name", "Nature", "Supporting assets", "Description"],
        [],
        ["1", "✔", "R&D", "BA01", "Process", "• Servers", "Research"],
    ],
    "1 - Supporting assets": [
        ["", "✓/❒", "Name", "Short name", "Parent supporting asset", "Description"],
        [],
        ["1", "✔", "Servers", "SA01", "", "Desktop servers"],
    ],
    "1 - Severity scale": [
        ["", "✓/❒", "Level", "Name", "Description"],
        [],
        ["1", "✔", "1", "Minor", ""],
        ["2", "✔", "2", "Significant", ""],
        ["3", "✔", "3", "Serious", ""],
    ],
    "1 - Feared events": [
        [
            "",
            "✓/❒",
            "Business assets",
            "Feared event",
            "Short name",
            "Impacts",
            "Retained severity",
        ],
        [],
        ["1", "✔", "• R&D", "Loss of data", "FE01", "• Legal impacts", "Serious"],
    ],
    "1 - X reference standard": [
        [
            "",
            "✓/❒",
            "Ref.",
            "Name",
            "Type",
            "Severity reduction",
            "Description",
            "Status",
        ],
        [],
        ["1", "✔", "M1", "Awareness", "Governance", "0 %", "", "In progress"],
    ],
}


def build_workbook(sheets: dict) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row or [None])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


@pytest.fixture(params=["fr", "en"])
def arm_data(request):
    sheets = FR_SHEETS if request.param == "fr" else EN_SHEETS
    return process_arm_file(build_workbook(sheets))


class TestSheetResolution:
    @pytest.mark.parametrize(
        "sheets,key,expected",
        [
            (FR_SHEETS, "business_values", "1 - Valeurs métier"),
            (FR_SHEETS, "feared_events", "1 - Évènements redoutés"),
            (FR_SHEETS, "impact_level_scale", "1 - Échelle de gravité"),
            (EN_SHEETS, "business_values", "1 - Business assets"),
            (EN_SHEETS, "feared_events", "1 - Feared events"),
            (EN_SHEETS, "impact_level_scale", "1 - Severity scale"),
        ],
    )
    def test_sheet_found(self, sheets, key, expected):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(build_workbook(sheets)))
        assert find_sheet(wb, key)[1] == expected

    def test_truncated_sheet_name_is_matched(self):
        sheets = dict(FR_SHEETS)
        sheets["1 - Échelle de niveau d'impac"] = sheets.pop("1 - Échelle de gravité")
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(build_workbook(sheets)))
        assert (
            find_sheet(wb, "impact_level_scale")[1] == "1 - Échelle de niveau d'impac"
        )

    @pytest.mark.parametrize(
        "sheets,expected",
        [
            (FR_SHEETS, ["1 - Référentiel de sécurité X"]),
            (EN_SHEETS, ["1 - X reference standard"]),
            (
                {
                    **FR_SHEETS,
                    "1 - Mesures de sécurité isolée": [
                        ["", "Réf.", "Nom"],
                        [],
                        ["1", "M1", "MFA"],
                    ],
                },
                ["1 - Mesures de sécurité isolée", "1 - Référentiel de sécurité X"],
            ),
        ],
    )
    def test_measure_sheets_detected_by_headers(self, sheets, expected):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(build_workbook(sheets)))
        assert find_measure_sheets(wb) == expected


class TestExtraction:
    def test_primary_assets(self, arm_data):
        assert len(arm_data["primary_assets"]) == 1
        assert arm_data["primary_assets"][0]["supporting_asset_names"] != []

    def test_feared_events_linked_and_graded(self, arm_data):
        assert len(arm_data["feared_events"]) == 1
        event = arm_data["feared_events"][0]
        assert event["gravity"] == 2
        assert event["asset_names"] == ["R&D"]

    def test_applied_controls(self, arm_data):
        assert [c["ref_id"] for c in arm_data["applied_controls"]] == ["M1"]

    def test_workshop_1_sheets_all_resolved(self, arm_data):
        workshop_1 = {
            "business_values",
            "missions",
            "feared_events",
            "supporting_assets",
            "impact_level_scale",
            "security_measures",
        }
        assert workshop_1.isdisjoint(arm_data["missing_sheets"])


class TestMissingSheetReporting:
    def test_absent_sheets_are_reported(self):
        sheets = {k: v for k, v in FR_SHEETS.items() if k == "1 - Missions"}
        result = process_arm_file(build_workbook(sheets))
        assert "feared_events" in result["missing_sheets"]
        assert "security_measures" in result["missing_sheets"]


FULL_EXPORT_SHEETS = {
    "1 - Base de valeurs métier - p": [
        ["", "✓/❒", "Nom", "Abrév.", "Nature", "Biens supports", "Description"],
        [],
        ["1", "✔", "Paie", "VM1", "Processus", "• Serveur RH", ""],
    ],
    "1 - Base de biens supports": [
        ["", "Nom", "Abrév.", "Bien support parent", "Description"],
        [],
        ["1", "Catalogue A", "", "", ""],
        ["2", "Catalogue B", "", "", ""],
    ],
    "1 - Base de biens supports - p": [
        ["", "Nom", "Abrév.", "Bien support parent", "Description"],
        [],
        ["1", "Serveur RH", "", "", ""],
    ],
    "1 - Mesures de sécurité isolée": [
        ["", "Réf.", "Nom", "Type", "Description", "Statut"],
        ["", "", "", "", "", ""],
        ["1", "M1", "MFA", "", "", "Implémentée"],
        ["2", "", "Revue des accès", "", "", "A démarrer"],
    ],
    "1 - ISO 27002": [
        ["", "Réf.", "Nom", "Type", "Description", "Statut"],
        [],
        ["1", "5.1", "Politiques", "", "", ""],
    ],
    "2 - Base de couples SR OV": [
        [
            "",
            "Identification",
            None,
            "Évènements redoutés",
            "Cotation",
            None,
            "Justification",
        ],
        ["", "Source de risque", "Objectif visé", None, "Motivation", "Ressources"],
        ["1", "SR1", "OV1", "• ER1", "Assez motivé", ""],
        ["2", "SR1", "OV1", "• ER2", "Assez motivé", "++", 2026],
    ],
    "2 - Échelle de motivation": [
        ["", "✓/❒", "Niveau", "Nom"],
        [],
        ["1", "✔", "1", "Peu motivé"],
        ["2", "✔", "3", "Assez motivé"],
    ],
    "3 - Base des parties prenantes": [
        ["", "✓/❒", "Nom", "Abrév.", "Catégorie", "Sources de risque"],
        [],
        ["1", "✔", "Prestataire", "", "Fournisseurs", ""],
        ["2", "", "Inconnu", "", "Partenaires", ""],
    ],
    "3 - Menace des parties prenant": [
        ["", "Catégorie", "Partie prenante", "Niveau d'exposition", None, None],
        ["", "", "", "Dépendance", "Pénétration", "Maturité cyber"],
        ["1", "Fournisseurs", "Prestataire", "4", "3", "2"],
    ],
    "3 - Synthèse des scénarios str": [
        [
            "",
            "✓/❒",
            "Nom",
            "Abrév.",
            "Couple SR/OV",
            None,
            "Chemin d'attaque",
            None,
            None,
        ],
        ["", "", "", "", "Source de risque", "Objectif visé", "✓/❒", "Réf.", "Nom"],
        ["1", "✔", "S1", "", "SR1", "OV1", "✔", "R1", "Chemin 1"],
        ["2", None, None, None, None, None, "✔", "R2", "Chemin 2"],
    ],
    "4 - Base d'actions élémentaire": [
        ["", "✓/❒", "Nom", "Abrév.", "Description"],
        [],
        ["1", "✔", "Hameçonnage", "AE1", ""],
        ["2", "", "Catalogue", "AE2", ""],
        ["3", "✓", "Rebond", "AE3", ""],
    ],
}


class TestFullExportLayout:
    @pytest.fixture
    def data(self):
        return process_arm_file(build_workbook(FULL_EXPORT_SHEETS))

    def test_project_sheets_preferred(self, data):
        assert [a["name"] for a in data["primary_assets"]] == ["Paie"]
        assert [a["name"] for a in data["supporting_assets"]] == ["Serveur RH"]

    def test_isolated_measures_with_status(self, data):
        assert [(c["name"], c["status"]) for c in data["applied_controls"]] == [
            ("MFA", "active"),
            ("Revue des accès", "to_do"),
        ]

    def test_only_selected_stakeholders_with_scores(self, data):
        assert [s["name"] for s in data["stakeholders"]] == ["Prestataire"]
        assert data["stakeholders"][0]["current_dependency"] == 4

    def test_continuation_rows_add_attack_paths(self, data):
        assert [
            [p["ref_id"] for p in s["attack_paths"]]
            for s in data["strategic_scenarios"]
        ] == [["R1", "R2"]]

    def test_roto_repeated_per_feared_event_is_merged(self, data):
        [roto] = data["roto_couples"]
        assert roto["feared_event_names"] == ["ER1", "ER2"]

    def test_roto_cotation_from_scale_or_plus_signs(self, data):
        [roto] = data["roto_couples"]
        assert (roto["motivation"], roto["resources"]) == (3, 2)
        assert roto["justification"] == "2026"

    def test_elementary_actions(self, data):
        assert [a["ref_id"] for a in data["elementary_actions"]] == ["AE1", "AE3"]


PER_TABLE_EXPORTS = {
    "Atelier 1/Base de valeurs métier - projet.xlsx": [
        ["", "✓/❒", "Nom", "Abrév.", "Nature", "Description", "Critères de sécurité"],
        [],
        ["1", "✔", "Paie", "", "Processus", "", ""],
        ["2", "✔", "Long" * 60, "", "Processus", "", ""],
    ],
    "Atelier 1/Base d'évènements redoutés - projet.xlsx": [
        [
            "",
            "✓/❒",
            "Valeurs métier",
            "Évènement redouté",
            "Gravité retenue",
            "Impacts",
        ],
        [],
        ["1", "✔", "• Paie", "Fuite de données", "G3 - Grave", "Légal\nFinancier"],
        ["2", "", "• Paie", "NA", ""],
        [
            "3",
            "",
            "• " + "Long" * 60,
            "Fuite de données",
            "G2 - Significative",
            "Légal",
        ],
    ],
    "Atelier 1/Base de biens supports.xlsx": [
        ["", "Nom", "Abrév.", "Bien support parent"],
        [],
        ["1", "Catalogue", "", ""],
    ],
    "Atelier 1/Base de biens supports - projet.xlsx": [
        ["", "Nom", "Abrév.", "Bien support parent"],
        [],
        ["1", "Serveur RH", "", ""],
    ],
    "Atelier 2/Base de couples SR OV.xlsx": [
        ["", "Identification", None, "Évènements redoutés", "Cotation", None],
        ["", "Source de risque", "Objectif visé", None, "Motivation", "Ressources"],
        ["1", "SR1", "OV1", "• Fuite de données", "Assez motivé", "Significatives"],
    ],
    "Atelier 3/Menace des parties prenantes.xlsx": [
        ["", "Catégorie", "Partie prenante", "Niveau d'exposition", None],
        ["", "", "", "Dépendance", "Pénétration"],
        ["1", "Partenaires", "Prestataire", "4", "2"],
    ],
    "Atelier 3/Synthèse des scénarios stratégiques.xlsx": [
        ["", "✓/❒", "Nom", "Abrév.", "Couple SR/OV", None, "Chemin d'attaque"],
        ["", "", "", "", "Source de risque", "Objectif visé", "✓/❒", "Réf.", "Nom"],
        ["1", "✔", "S1", "", "SR1", "OV1", "✔", "R1", "Chemin 1"],
    ],
    "Atelier 5/Mesures de sécurité isolées - projet.xlsx": [
        ["", "Réf.", "Nom", "Mesures de sécurité associées", "Description"],
        ["", "", "", "Nom", ""],
        ["1", "M1", "MFA", "", ""],
    ],
    "notes.xlsx": [["Commentaire"], [], ["rien"]],
}


def build_archive(files: dict) -> bytes:
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, rows in files.items():
            wb = Workbook()
            for row in rows:
                wb.active.append(row or [None])
            content = io.BytesIO()
            wb.save(content)
            archive.writestr(name, content.getvalue())
    return buffer.getvalue()


class TestPerTableArchive:
    @pytest.fixture
    def data(self):
        return process_arm_file(build_archive(PER_TABLE_EXPORTS))

    def test_tables_identified_by_headers(self, data):
        assert data["unrecognized_files"] == ["notes.xlsx"]
        assert data["primary_assets"][0]["name"] == "Paie"
        assert [c["ref_id"] for c in data["applied_controls"]] == ["M1"]
        assert [s["name"] for s in data["strategic_scenarios"]] == ["S1"]

    def test_repeated_feared_event_is_merged(self, data):
        [event] = data["feared_events"]
        assert event["gravity"] == 2
        assert event["is_selected"]
        assert event["asset_names"] == ["Paie", ("Long" * 60)[:200]]
        assert event["justification"] == "Légal\nFinancier\nLégal"

    def test_long_asset_name_is_truncated_and_kept_in_description(self, data):
        long_asset = data["primary_assets"][1]
        assert long_asset["name"] == ("Long" * 60)[:200]
        assert long_asset["description"] == "Long" * 60

    def test_roto_cotation_falls_back_to_anssi_scale(self, data):
        [roto] = data["roto_couples"]
        assert (roto["motivation"], roto["resources"]) == (3, 2)
        assert roto["feared_event_names"] == ["Fuite de données"]

    def test_stakeholders_from_threat_table(self, data):
        [stakeholder] = data["stakeholders"]
        assert stakeholder["name"] == "Prestataire"
        assert stakeholder["category_raw"] == "Partenaires"
        assert stakeholder["current_dependency"] == 4
        assert "stakeholders" not in data["missing_sheets"]

    def test_project_table_preferred_over_catalogue(self, data):
        assert [a["name"] for a in data["supporting_assets"]] == ["Serveur RH"]
        exports = dict(reversed(PER_TABLE_EXPORTS.items()))
        reversed_data = process_arm_file(build_archive(exports))
        assert [a["name"] for a in reversed_data["supporting_assets"]] == ["Serveur RH"]

    @pytest.mark.parametrize(
        "content,code",
        [
            (b"not a zip", "not_zip"),
            (
                build_archive({"notes.xlsx": PER_TABLE_EXPORTS["notes.xlsx"]}),
                "no_table",
            ),
            (
                build_archive(
                    {
                        f"{study}/Base de couples SR OV.xlsx": PER_TABLE_EXPORTS[
                            "Atelier 2/Base de couples SR OV.xlsx"
                        ]
                        for study in ("Etude 1", "Etude 2")
                    }
                ),
                "duplicate_table",
            ),
            (
                build_archive(
                    {
                        name: PER_TABLE_EXPORTS[
                            "Atelier 1/Base de biens supports" + suffix + ".xlsx"
                        ]
                        for name, suffix in [
                            ("a/Base de biens supports.xlsx", ""),
                            ("b/Base de biens supports - projet.xlsx", " - projet"),
                            ("c/Base de biens supports.xlsx", ""),
                        ]
                    }
                ),
                "duplicate_table",
            ),
            (
                build_archive(
                    {
                        f"notes{i}.xlsx": PER_TABLE_EXPORTS["notes.xlsx"]
                        for i in range(101)
                    }
                ),
                "too_large",
            ),
        ],
        ids=[
            "not_zip",
            "no_arm_table",
            "same_table_twice",
            "same_catalogue_twice",
            "too_many_files",
        ],
    )
    def test_invalid_archive_is_rejected(self, content, code):
        from data_wizard.arm_helpers import ARMArchiveError

        with pytest.raises(ARMArchiveError) as error:
            process_arm_file(content)
        assert error.value.code == code


@pytest.mark.django_db
def test_gravity_outside_matrix_is_not_rated(
    api_client,
    domain_folder,
    all_accessible,
    ebios_4x4_matrix,  # noqa: F811
):
    from data_wizard.tests.test_load_file_view import _post
    from ebios_rm.models import FearedEvent

    exports = {
        "Base d'évènements redoutés - projet.xlsx": [
            ["", "✓/❒", "Valeurs métier", "Évènement redouté", "Gravité retenue"],
            [],
            ["1", "✔", "", "Fuite", "G3 - Grave"],
            ["2", "✔", "", "Arrêt", "G5 - Critique"],
        ]
    }
    response = _post(
        api_client,
        build_archive(exports),
        "etude.zip",
        "EbiosRMStudyARM",
        domain_folder.id,
        HTTP_X_MATRIX_ID=str(ebios_4x4_matrix.id),
    )
    assert response.json()["results"]["errors"] == []
    assert dict(FearedEvent.objects.values_list("name", "gravity")) == {
        "Fuite": 2,
        "Arrêt": -1,
    }
