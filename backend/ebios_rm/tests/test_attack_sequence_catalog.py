from pathlib import Path

import pytest
from django.conf import settings

from core.models import StoredLibrary
from ebios_rm.models import ElementaryAction
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from ebios_rm.serializers import ElementaryActionReadSerializer
from sec_intel.models import Tactic, Technique, TTPCatalog
from sec_intel.views import build_catalog_matrix

LIBRARY_URN = "urn:intuitem:risk:library:ebios-rm-attack-sequence"
TECHNIQUE = "urn:intuitem:risk:technique:ebios-rm-attack-sequence:"


@pytest.fixture
def catalog():
    library = StoredLibrary.objects.filter(urn=LIBRARY_URN).first()
    if library is None:
        library, error = StoredLibrary.store_library_file(
            Path(settings.BASE_DIR) / "library/libraries/ebios-rm-attack-sequence.yaml",
            builtin=True,
        )
        assert error is None, error
    if not library.is_loaded:
        assert library.load() is None
    return library


@pytest.mark.django_db
class TestAttackSequenceCatalog:
    def test_library_asks_to_be_autoloaded(self, catalog):
        assert catalog.autoload is True

    def test_four_phases_in_guide_order(self, catalog):
        phases = list(
            Tactic.objects.filter(catalog__urn__endswith="ebios-rm-attack-sequence")
            .order_by("order_id")
            .values_list("order_id", flat=True)
        )
        assert phases == [0, 1, 2, 3]

    def test_categories_follow_fiche_7(self, catalog):
        recruitment = Technique.objects.get(urn=TECHNIQUE + "recrutement")
        assert sorted(t.order_id for t in recruitment.tactics.all()) == [0, 1, 2, 3]
        assert recruitment.ref_id is None
        malware = Technique.objects.get(urn=TECHNIQUE + "outils-malveillants")
        assert sorted(t.order_id for t in malware.tactics.all()) == [0, 1, 2, 3]
        phishing = Technique.objects.get(
            urn=TECHNIQUE + "intrusion-internet.hameconnage"
        )
        assert phishing.parent.urn == TECHNIQUE + "intrusion-internet"
        assert recruitment.annotation.startswith("- Number of potential targets")

    def test_sub_technique_label_without_ref_id(self, catalog):
        phishing = Technique.objects.get(
            urn=TECHNIQUE + "intrusion-internet.hameconnage"
        )
        assert phishing.ref_id is None
        assert str(phishing) == (
            f"{phishing.parent.get_name_translated}: {phishing.get_name_translated}"
        )

    @pytest.mark.parametrize(
        "flags, status", [({"ttps": False, "ebiosrm": True}, 200), ({}, 403)]
    )
    def test_techniques_follow_either_flag(self, admin_client, catalog, flags, status):
        settings_row, _ = GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.FEATURE_FLAGS
        )
        settings_row.value = {"ttps": False, "ebiosrm": False, **flags}
        settings_row.save(update_fields=["value"])
        clear_feature_flags_cache()

        lateral = Technique.objects.get(urn=TECHNIQUE + "lateralisation")
        response = admin_client.get(f"/api/techniques/{lateral.id}/")
        assert response.status_code == status, response.content

    def test_matrix_orders_techniques_without_ref_id(self, catalog):
        ebios = TTPCatalog.objects.get(
            urn__endswith="ttp_catalog:ebios-rm-attack-sequence"
        )
        cells = build_catalog_matrix(ebios)["cells"]
        intrusion = next(
            cell for cell in cells if cell["children"] and cell["ref_id"] is None
        )
        orders = [child["order_id"] for child in intrusion["children"]]
        assert orders == sorted(orders)

    def test_rating_help_comes_from_the_category(self, catalog):
        sub_technique = Technique.objects.get(
            urn=TECHNIQUE + "intrusion-internet.hameconnage"
        )
        action = ElementaryAction.objects.create(
            name="Spear-phishing the HR team",
            attack_stage=ElementaryAction.AttackStage.ENTER,
            technique=sub_technique,
        )
        data = ElementaryActionReadSerializer(action).data
        assert data["technique"]["id"] == str(sub_technique.id)
        assert data["rating_help"] == sub_technique.parent.annotation

    def test_action_without_technique_has_no_help(self):
        action = ElementaryAction.objects.create(
            name="Custom", attack_stage=ElementaryAction.AttackStage.KNOW
        )
        data = ElementaryActionReadSerializer(action).data
        assert data["technique"] is None
        assert data["rating_help"] is None
