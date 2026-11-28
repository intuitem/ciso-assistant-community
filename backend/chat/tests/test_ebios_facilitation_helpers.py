from types import SimpleNamespace

from chat.workflows.ebios_facilitation import _find, _readable, _roto_label


def test_find_compound_name_by_its_first_part():
    by_name = {
        "rançongiciel via hôpisoft - accès via hôpisoft": 1,
        "fuite de données - accès direct": 2,
    }
    assert _find(by_name, "Rançongiciel via Hôpisoft") == 1
    assert _find(by_name, "inconnu") is None


def test_find_first_part_must_be_unique():
    by_name = {"risque a - chemin 1": 1, "risque a - chemin 2": 2}
    assert _find(by_name, "risque a") is None


def test_couple_shown_in_user_language():
    origin = SimpleNamespace(name="organized_crime", translations={})
    roto = SimpleNamespace(risk_origin=origin, target_objective="extorquer")
    assert _roto_label(roto, "fr") == "crime organisé - extorquer"
    assert (
        _readable(
            "risk_origin", "Organized_crime", {}, {"organized_crime": "crime organisé"}
        )
        == "crime organisé"
    )


def test_objects_of_the_current_proposal_match_by_exact_name_only():
    from datetime import datetime, timedelta, timezone

    from chat.workflows.ebios_facilitation import _BATCH_START

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fresh = SimpleNamespace(created_at=start + timedelta(seconds=1))
    old = SimpleNamespace(created_at=start - timedelta(days=1))
    token = _BATCH_START.set(start)
    try:
        assert (
            _find({"vengeur → fuite de données": fresh}, "activiste → fuite de données")
            is None
        )
        assert (
            _find({"vengeur → fuite de données": fresh}, "Vengeur → fuite de données")
            is fresh
        )
        assert (
            _find({"vengeur → fuite de donnée": old}, "vengeur → fuite de données")
            is old
        )
    finally:
        _BATCH_START.reset(token)
