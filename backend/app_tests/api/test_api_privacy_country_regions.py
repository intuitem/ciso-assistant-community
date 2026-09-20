import unicodedata

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.constants import (
    COUNTRY_CHOICES,
    EEA_COUNTRIES_SET,
    EU_COUNTRIES_SET,
    NON_MAPPABLE_COUNTRY_CODES,
    PRIVACY_COUNTRY_CHOICES,
)
from data_wizard.views import ProcessingChildConsumerMixin
from iam.models import Folder, User
from privacy.models import DataTransfer, Processing
from privacy.views import agg_countries

IN_SCOPE_COLOR = "#A7CC74"
THIRD_COUNTRY_COLOR = "#F4B83D"


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    return Folder.get_root_folder()


def _admin_client():
    user = User.objects.create_superuser("region-admin@tests.com")
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _fold(name):
    return "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    ).lower()


class TestCountryChoices:
    def test_countries_are_sorted_by_name(self):
        # "Other Countries" is the deliberate catch-all and stays last.
        names = [name for _, name in COUNTRY_CHOICES[:-1]]
        assert names == sorted(names, key=_fold)
        assert COUNTRY_CHOICES[-1] == ("x28", "Other Countries")

    def test_regions_are_absent_from_the_dora_country_list(self):
        # eba_GA only accepts ISO 3166-1 alpha-2, so regions must never reach the
        # DORA register. See documentation/dora-roi-specification.md.
        codes = {code for code, _ in COUNTRY_CHOICES}
        assert "EU" not in codes
        assert "EEA" not in codes

    def test_privacy_choices_offer_regions_first(self):
        assert PRIVACY_COUNTRY_CHOICES[:2] == [
            ("EU", "European Union"),
            ("EEA", "European Economic Area"),
        ]
        assert PRIVACY_COUNTRY_CHOICES[2:] == COUNTRY_CHOICES

    def test_region_codes_fit_the_column(self):
        assert max(len(code) for code, _ in PRIVACY_COUNTRY_CHOICES) <= 3

    def test_eea_extends_eu_with_the_three_efta_members(self):
        assert EEA_COUNTRIES_SET - EU_COUNTRIES_SET == {"IS", "LI", "NO"}

    def test_every_region_is_flagged_non_mappable(self):
        assert {"EU", "EEA"} <= NON_MAPPABLE_COUNTRY_CODES


class TestCountryEndpoints:
    def test_data_transfer_country_endpoint_offers_regions(self, app_ready):
        response = _admin_client().get("/api/privacy/data-transfers/country/")
        assert response.status_code == 200
        assert response.json()["EU"] == "European Union"
        assert response.json()["EEA"] == "European Economic Area"

    def test_data_contractor_country_endpoint_offers_regions(self, app_ready):
        response = _admin_client().get("/api/privacy/data-contractors/country/")
        assert response.status_code == 200
        assert response.json()["EU"] == "European Union"


class TestImporterChoiceResolution:
    """The picker offers EU/EEA, so the spreadsheet importer must accept them too."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("EU", "EU"),
            ("eu", "EU"),
            ("European Union", "EU"),
            ("EEA", "EEA"),
            ("European Economic Area", "EEA"),
            ("France", "FR"),
        ],
    )
    def test_regions_and_countries_resolve(self, raw, expected):
        resolve = ProcessingChildConsumerMixin._choice_key
        assert resolve(raw, PRIVACY_COUNTRY_CHOICES) == expected

    def test_regions_stay_out_of_the_dora_list(self):
        assert ProcessingChildConsumerMixin._choice_key("EU", COUNTRY_CHOICES) is None


class TestRegionAggregation:
    @pytest.fixture
    def processing(self, app_ready):
        return Processing.objects.create(name="P1", folder=app_ready)

    @pytest.fixture
    def other_processing(self, app_ready):
        return Processing.objects.create(name="P2", folder=app_ready)

    def _transfer(self, processing, country):
        # (entity, country, processing) is unique in scope, so a repeated country
        # has to hang off a different processing.
        return DataTransfer.objects.create(processing=processing, country=country)

    def _aggregate(self):
        return agg_countries(DataTransfer.objects.values_list("id", flat=True), [])

    def test_region_transfer_is_accepted(self, processing):
        transfer = self._transfer(processing, "EU")
        transfer.full_clean()
        assert transfer.country == "EU"

    def test_regions_are_split_out_of_the_map_areas(self, processing, other_processing):
        for country in ("FR", "EU", "US", "x28"):
            self._transfer(processing, country)
        self._transfer(other_processing, "EU")

        countries, regions = self._aggregate()

        assert {c["id"] for c in countries} == {"FR", "US"}
        assert {r["id"]: r["count"] for r in regions} == {"EU": 2, "x28": 1}
        assert [r["label"] for r in regions if r["id"] == "EU"] == ["European Union"]

    def test_regions_are_omitted_when_unused(self, processing):
        self._transfer(processing, "FR")
        _, regions = self._aggregate()
        assert regions == []

    def test_eea_members_are_in_gdpr_scope(self, processing):
        for country in ("NO", "FR", "US"):
            self._transfer(processing, country)

        countries, _ = self._aggregate()
        colors = {c["id"]: c["color"] for c in countries}

        assert colors["NO"] == IN_SCOPE_COLOR
        assert colors["FR"] == IN_SCOPE_COLOR
        assert colors["US"] == THIRD_COUNTRY_COLOR
