"""Inheritance overlays must honour per-role field visibility.

The framework report and the combined tree redact a row's own ``score`` when
the audit hides it, but the ``inheritance`` block used to carry the same value
(and every ancestor's) unredacted.
"""

import pytest
from django.urls import reverse
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.audit_inheritance import redact_overlay
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    StoredLibrary,
)
from global_settings.models import GlobalSettings
from iam.models import Folder, User, UserGroup

SHOW_SCORE = {
    "score": {"auditor": "edit", "respondent": "edit"},
    "is_scored": {"auditor": "edit", "respondent": "edit"},
}

YAML = """
urn: urn:intuitem:test:library:inh-redaction
locale: en
ref_id: INHR
name: inh redaction
description: x
copyright: x
version: 1
publication_date: 2025-01-01
provider: t
packager: t
objects:
  framework:
    urn: urn:intuitem:test:framework:inh-redaction
    ref_id: INHR
    name: inh redaction fw
    description: x
    min_score: 1
    max_score: 5
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:inhr:cat
      assessable: false
      depth: 1
      ref_id: CAT
      name: cat
    - urn: urn:intuitem:test:req_node:inhr:req
      assessable: true
      depth: 2
      ref_id: REQ
      parent_urn: urn:intuitem:test:req_node:inhr:cat
      name: req
""".lstrip()


# ---------------------------------------------------------------------------
# Pure redaction
# ---------------------------------------------------------------------------


def _entry(ca_id, distance, result="compliant", score=4):
    return {
        "ca_id": ca_id,
        "ca_name": ca_id,
        "folder_id": None,
        "folder_name": None,
        "distance": distance,
        "result": result,
        "score": score,
        "raw_score": score,
        "is_scored": True,
        "scale": {"min": 1, "max": 5},
    }


def _overlay(source, path, own_score=2):
    return {
        "strategy": "best_case",
        "inherited": source["distance"] > 0,
        "effective_result": source["result"],
        "effective_score": source["score"],
        "scale": {"min": 1, "max": 5},
        "own": {
            "result": "partially_compliant",
            "score": own_score,
            "is_scored": True,
            "scale": {"min": 1, "max": 5},
        },
        "source": source,
        "path": path,
    }


class TestRedactOverlay:
    def test_none_passthrough(self):
        assert redact_overlay(None, "t", lambda _: frozenset()) is None

    def test_nothing_hidden_is_identity(self):
        ov = _overlay(_entry("p", 1), [_entry("p", 1)])
        assert redact_overlay(ov, "t", lambda _: frozenset()) == ov

    def test_source_hidden_score_redacts_effective_and_entry(self):
        ov = _overlay(_entry("p", 1), [_entry("p", 1)])
        hidden = {"p": frozenset({"score", "is_scored"})}
        out = redact_overlay(ov, "t", lambda c: hidden.get(c, frozenset()))
        assert out["effective_score"] is None
        assert out["effective_result"] == "compliant"
        assert out["source"]["score"] is None
        assert out["source"]["raw_score"] is None
        assert out["source"]["is_scored"] is None
        assert out["path"][0]["score"] is None
        # The target shows scores: its own value stays.
        assert out["own"]["score"] == 2
        # Input untouched.
        assert ov["effective_score"] == 4

    def test_target_hidden_score_redacts_everything_scored(self):
        ov = _overlay(_entry("p", 1), [_entry("p", 1), _entry("g", 2)])
        hidden = {"t": frozenset({"score", "is_scored"})}
        out = redact_overlay(ov, "t", lambda c: hidden.get(c, frozenset()))
        assert out["effective_score"] is None
        assert out["own"]["score"] is None
        assert out["own"]["is_scored"] is None
        assert all(e["score"] is None for e in out["path"])
        assert out["source"]["score"] is None
        assert out["effective_result"] == "compliant"

    def test_only_the_hidden_ancestor_is_redacted(self):
        ov = _overlay(_entry("p", 1), [_entry("p", 1), _entry("g", 2, score=5)])
        hidden = {"g": frozenset({"score"})}
        out = redact_overlay(ov, "t", lambda c: hidden.get(c, frozenset()))
        assert out["effective_score"] == 4
        assert out["path"][0]["score"] == 4
        assert out["path"][1]["score"] is None
        assert out["path"][1]["result"] == "compliant"

    def test_hidden_result_redacts_verdicts(self):
        ov = _overlay(_entry("p", 1), [_entry("p", 1)])
        hidden = {"p": frozenset({"result"})}
        out = redact_overlay(ov, "t", lambda c: hidden.get(c, frozenset()))
        assert out["effective_result"] is None
        assert out["source"]["result"] is None
        assert out["effective_score"] == 4

    def test_unknown_source_audit_is_fully_hidden_by_default_redactor(self):
        from core.audit_inheritance import make_overlay_redactor

        hidden_for_ca = make_overlay_redactor([], set())
        assert hidden_for_ca("nope") == frozenset({"result", "score", "is_scored"})


# ---------------------------------------------------------------------------
# End to end through the report and combined tree
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_client(db):
    startup(sender=None)
    admin = User.objects.create_superuser("admin@inh-redaction.com")
    g = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = g.folder
    admin.save()
    g.user_set.add(admin)
    c = APIClient()
    tok = AuthToken.objects.create(user=admin)
    c.credentials(HTTP_AUTHORIZATION=f"Token {tok[1]}")
    return c


def _mk(name, folder, fw, result, score, field_visibility):
    per = Perimeter.objects.create(name=f"p-{name}", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name=name,
        framework=fw,
        folder=folder,
        perimeter=per,
        status="in_progress",
        field_visibility=field_visibility,
    )
    ca.create_requirement_assessments()
    ra = RequirementAssessment.objects.get(
        compliance_assessment=ca, requirement__assessable=True
    )
    ra.result, ra.score, ra.is_scored = result, score, True
    ra.save()
    return ca


@pytest.fixture
def tree(admin_client):
    """Global (hides score) > Eurostar (shows) > {Teams+ (shows), Opalys (hides)}."""
    stored, err = StoredLibrary.store_library_content(YAML.encode())
    assert err is None, err
    assert stored.load() is None
    fw = Framework.objects.get(urn="urn:intuitem:test:framework:inh-redaction")

    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    eurostar = Folder.objects.create(name="Eurostar", parent_folder=root)
    ops = Folder.objects.create(name="Operations", parent_folder=eurostar)
    teams = Folder.objects.create(name="Teams+", parent_folder=ops)
    opalys = Folder.objects.create(name="Opalys", parent_folder=ops)

    cas = {
        "Group": _mk("Group", root, fw, "compliant", 5, {}),
        "Eurostar": _mk("Eurostar", eurostar, fw, "partially_compliant", 1, SHOW_SCORE),
        "Teams+": _mk("Teams+", teams, fw, "partially_compliant", 3, SHOW_SCORE),
        "Opalys": _mk("Opalys", opalys, fw, "partially_compliant", 2, {}),
    }

    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS,
        defaults={"value": {"audit_tree_inheritance": True}},
    )
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.GENERAL, defaults={"value": {}}
    )
    gs.value = {**(gs.value or {}), "audit_tree_aggregation_strategy": "best_case"}
    gs.save()
    return fw, cas


def _scores_by_ca(path):
    return {e["ca_name"]: (e["score"], e["raw_score"], e["is_scored"]) for e in path}


@pytest.mark.django_db
def test_report_and_combined_tree_redact_overlay(admin_client, tree):
    fw, cas = tree
    r = admin_client.get(reverse("frameworks-report", kwargs={"pk": str(fw.pk)}))
    assert r.status_code == 200, r.content
    data = r.json()
    assert data["aggregation_strategy"] == "best_case"
    rows = {row["compliance_assessment_name"]: row for row in data["rows"]}
    assert set(rows) == set(cas)

    # Top audit: nothing to inherit, own score hidden by its default visibility.
    assert rows["Group"]["inheritance"] is None
    assert rows["Group"]["score"] is None

    # Eurostar shows scores, but its source (Group) hides them: the verdict is
    # inherited, the score is not.
    inh = rows["Eurostar"]["inheritance"]
    assert rows["Eurostar"]["score"] == 1
    assert inh["inherited"] is True
    assert inh["source"]["ca_name"] == "Group"
    assert inh["effective_result"] == "compliant"
    assert inh["effective_score"] is None
    assert inh["own"]["score"] == 1
    assert _scores_by_ca(inh["path"]) == {"Group": (None, None, None)}

    # Teams+ shows scores: Eurostar's stays visible, Group's does not.
    inh = rows["Teams+"]["inheritance"]
    assert rows["Teams+"]["score"] == 3
    assert inh["source"]["ca_name"] == "Group"
    assert inh["effective_result"] == "compliant"
    assert inh["effective_score"] is None
    assert inh["own"]["score"] == 3
    assert _scores_by_ca(inh["path"]) == {
        "Eurostar": (1, 1, True),
        "Group": (None, None, None),
    }

    # Opalys hides scores: every score in the block goes, even Eurostar's,
    # which is visible elsewhere.
    inh = rows["Opalys"]["inheritance"]
    assert rows["Opalys"]["score"] is None
    assert inh["effective_result"] == "compliant"
    assert inh["effective_score"] is None
    assert inh["own"]["score"] is None
    assert inh["own"]["is_scored"] is None
    assert inh["own"]["result"] == "partially_compliant"
    assert _scores_by_ca(inh["path"]) == {
        "Eurostar": (None, None, None),
        "Group": (None, None, None),
    }
    assert [e["result"] for e in inh["path"]] == ["partially_compliant", "compliant"]

    # Combined tree of Teams+ applies the same rules.
    r = admin_client.get(
        reverse(
            "compliance-assessments-combined-tree", kwargs={"pk": str(cas["Teams+"].pk)}
        )
    )
    assert r.status_code == 200, r.content
    found = []

    def walk(nodes):
        for node in nodes.values():
            # Non-assessable section nodes carry a not_assessed overlay too.
            if node.get("inheritance", {}).get("inherited"):
                found.append(node["inheritance"])
            walk(node.get("children") or {})

    walk(r.json()["tree"])
    assert len(found) == 1
    inh = found[0]
    assert inh["effective_score"] is None
    assert inh["own"]["score"] == 3
    assert _scores_by_ca(inh["path"]) == {
        "Eurostar": (1, 1, True),
        "Group": (None, None, None),
    }
