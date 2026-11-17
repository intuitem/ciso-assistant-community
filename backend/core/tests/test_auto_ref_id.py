"""Automatic ref_id: numbered within the parent, only when the setting is on."""

from itertools import count

import pytest

from core.models import AppliedControl, Finding, FindingsAssessment
from crq.models import QuantitativeRiskScenario, QuantitativeRiskStudy
from global_settings.models import GlobalSettings
from iam.models import Folder


@pytest.fixture
def domains(db):
    root = Folder.get_root_folder()
    return [
        Folder.objects.create(
            name=name, content_type=Folder.ContentType.DOMAIN, parent_folder=root
        )
        for name in ("A", "B")
    ]


def set_auto_ref_id(enabled):
    gs, _ = GlobalSettings.objects.get_or_create(name="general", defaults={"value": {}})
    gs.value = {**(gs.value or {}), "auto_ref_id": enabled}
    gs.save()


@pytest.mark.django_db
def test_off_by_default_leaves_ref_id_blank(domains):
    set_auto_ref_id(False)
    assert not AppliedControl.objects.create(name="c", folder=domains[0]).ref_id


@pytest.mark.django_db
def test_numbered_per_domain_and_never_overwritten(domains):
    set_auto_ref_id(True)
    a, b = domains
    names = count()
    make = lambda folder, **kw: (
        AppliedControl.objects.create(
            name=f"c{next(names)}", folder=folder, **kw
        ).ref_id
    )

    assert make(a) == "AC.01"
    assert make(a) == "AC.02"
    assert make(b) == "AC.01"
    assert make(a, ref_id="CUSTOM-1") == "CUSTOM-1"
    assert make(a, ref_id="AC.07") == "AC.07"
    assert make(a) == "AC.08"

    control = AppliedControl.objects.get(folder=a, ref_id="AC.01")
    control.ref_id = ""
    control.save()
    control.refresh_from_db()
    assert control.ref_id == ""  # only filled on creation


@pytest.mark.django_db
def test_numbered_per_parent_object(domains):
    set_auto_ref_id(True)
    fa1, fa2 = (
        FindingsAssessment.objects.create(name=n, folder=domains[0]) for n in "12"
    )
    assert fa1.ref_id == "FA.01" and fa2.ref_id == "FA.02"
    make = lambda fa, name: (
        Finding.objects.create(name=name, findings_assessment=fa).ref_id
    )
    assert [make(fa1, "f1"), make(fa1, "f2"), make(fa2, "f3")] == [
        "F.01",
        "F.02",
        "F.01",
    ]


@pytest.mark.django_db
def test_reuses_existing_generator(domains):
    set_auto_ref_id(True)
    study = QuantitativeRiskStudy.objects.create(name="s", folder=domains[0])
    names = count()
    make = lambda: (
        QuantitativeRiskScenario.objects.create(
            name=f"q{next(names)}", quantitative_risk_study=study
        ).ref_id
    )
    assert [make(), make()] == ["QR.01", "QR.02"]


def set_prefixes(prefixes):
    gs = GlobalSettings.objects.get(name="general")
    gs.value = {**gs.value, "auto_ref_id_prefixes": prefixes}
    gs.save()


@pytest.mark.django_db
def test_custom_prefix_starts_its_own_sequence(domains):
    set_auto_ref_id(True)
    a = domains[0]
    assert AppliedControl.objects.create(name="c1", folder=a).ref_id == "AC.01"
    set_prefixes({"appliedcontrol": "CTRL"})
    assert AppliedControl.objects.create(name="c2", folder=a).ref_id == "CTRL.01"
    assert AppliedControl.objects.get(name="c1").ref_id == "AC.01"


@pytest.mark.django_db
def test_custom_prefix_reaches_existing_generators(domains):
    set_auto_ref_id(True)
    set_prefixes({"quantitativeriskscenario": "SCN"})
    study = QuantitativeRiskStudy.objects.create(name="s", folder=domains[0])
    assert QuantitativeRiskScenario.get_default_ref_id(study) == "SCN.01"
    assert (
        QuantitativeRiskScenario.objects.create(
            name="q", quantitative_risk_study=study
        ).ref_id
        == "SCN.01"
    )


@pytest.mark.django_db
def test_custom_prefix_ignored_while_setting_off(domains):
    set_auto_ref_id(False)
    set_prefixes({"quantitativeriskscenario": "SCN"})
    study = QuantitativeRiskStudy.objects.create(name="s", folder=domains[0])
    assert QuantitativeRiskScenario.get_default_ref_id(study) == "QR.01"


@pytest.mark.django_db
def test_prefix_validation():
    from rest_framework.exceptions import ValidationError

    from global_settings.serializers import _validate_auto_ref_id_prefixes as check

    assert check({"appliedcontrol": " CTRL ", "asset": ""}) == {
        "appliedcontrol": "CTRL"
    }
    for bad in ({"user": "U"}, {"asset": "TOO-LONG-1"}, {"asset": "A.B"}, ["x"]):
        with pytest.raises(ValidationError):
            check(bad)


@pytest.mark.django_db
def test_backfill_fills_blanks_only_in_creation_order(domains):
    from core.base_models import backfill_auto_ref_ids

    a, b = domains
    set_auto_ref_id(False)
    for name, folder, ref_id in [
        ("old", a, ""),
        ("kept", a, "AC.03"),
        ("custom", a, "MY-1"),
        ("new", a, None),
        ("other", b, ""),
    ]:
        AppliedControl.objects.create(name=name, folder=folder, ref_id=ref_id)
    set_auto_ref_id(True)

    backfill_auto_ref_ids()  # also numbers the builtin Main entity
    refs = dict(AppliedControl.objects.values_list("name", "ref_id"))
    assert refs == {
        "old": "AC.04",
        "kept": "AC.03",
        "custom": "MY-1",
        "new": "AC.05",
        "other": "AC.01",
    }
    assert backfill_auto_ref_ids() == 0


@pytest.mark.django_db
def test_backfill_endpoint_admin_only_and_requires_setting(domains):
    from rest_framework.test import APIClient

    from core.apps import startup
    from iam.models import User, UserGroup

    startup(sender=None, **{})
    url = "/api/settings/general/backfill_ref_ids/"
    client = APIClient()

    client.force_authenticate(User.objects.create_user(email="reader@test.local"))
    assert client.post(url).status_code == 403

    admin = User.objects.create_user(email="admin@test.local")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    client.force_authenticate(admin)
    set_auto_ref_id(False)
    assert client.post(url).status_code == 400

    AppliedControl.objects.create(name="c", folder=domains[0])
    set_auto_ref_id(True)
    response = client.post(url)
    assert response.status_code == 200 and response.json()["updated"] >= 1
    assert AppliedControl.objects.get(name="c").ref_id == "AC.01"


@pytest.mark.django_db
def test_models_that_gained_a_ref_id(domains):
    from core.models import Evidence, RiskAcceptance

    set_auto_ref_id(True)
    assert Evidence.objects.create(name="e", folder=domains[0]).ref_id == "EVD.01"
    assert RiskAcceptance.objects.create(name="r", folder=domains[0]).ref_id == "RAC.01"


@pytest.mark.django_db
def test_assessment_numbered_in_its_perimeter_domain(domains):
    from core.models import Perimeter

    set_auto_ref_id(True)
    a = domains[0]
    FindingsAssessment.objects.create(name="existing", folder=a)  # FA.01 in A
    perimeter = Perimeter.objects.create(name="p", folder=a)
    fa = FindingsAssessment.objects.create(
        name="via perimeter", folder=Folder.get_root_folder(), perimeter=perimeter
    )
    assert (fa.folder_id, fa.ref_id) == (a.id, "FA.02")


@pytest.mark.django_db
def test_policies_share_the_applied_control_sequence(domains):
    from core.base_models import auto_ref_id_models
    from core.models import Policy

    set_auto_ref_id(True)
    set_prefixes({"appliedcontrol": "CTRL"})
    AppliedControl.objects.create(name="c", folder=domains[0])
    assert Policy.objects.create(name="p", folder=domains[0]).ref_id == "CTRL.02"
    assert "policy" not in auto_ref_id_models()


@pytest.mark.django_db
def test_numbering_ignores_case_and_non_ascii_digits(domains):
    set_auto_ref_id(True)
    a = domains[0]
    AppliedControl.objects.create(name="lower", folder=a, ref_id="ac.03")
    AppliedControl.objects.create(name="sup", folder=a, ref_id="AC.²")
    assert AppliedControl.objects.create(name="c", folder=a).ref_id == "AC.04"


@pytest.mark.django_db
def test_findings_without_assessment_share_one_sequence(domains):
    from core.base_models import backfill_auto_ref_ids

    set_auto_ref_id(False)
    Finding.objects.create(name="old", folder=domains[0])
    set_auto_ref_id(True)
    assert Finding.objects.create(name="new", folder=domains[0]).ref_id == "F.01"
    backfill_auto_ref_ids()
    assert Finding.objects.get(name="old").ref_id == "F.02"
