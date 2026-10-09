"""Domain tree feed: one framework's audits summed up per domain."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.apps import startup
from core.domain_tree import build_domain_tree, framework_structure
from core.models import (
    Actor,
    Campaign,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    StoredLibrary,
)
from core.utils import EVERYONE_EDIT
from iam.models import Folder, User, UserGroup

YAML = """
urn: urn:intuitem:test:library:domain-tree
locale: en
ref_id: DT
name: domain tree
description: x
copyright: x
version: 1
publication_date: 2025-01-01
provider: t
packager: t
objects:
  framework:
    urn: urn:intuitem:test:framework:domain-tree
    ref_id: DT
    name: domain tree fw
    description: x
    min_score: 0
    max_score: 4
    implementation_groups_definition:
    - ref_id: IG1
      name: Basic
    - ref_id: IG2
      name: Advanced
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:dt:s1
      assessable: false
      depth: 1
      ref_id: S1
      name: section one
    - urn: urn:intuitem:test:req_node:dt:s1.a
      assessable: true
      depth: 2
      ref_id: S1.A
      parent_urn: urn:intuitem:test:req_node:dt:s1
      name: s1 a
      implementation_groups: [IG1, IG2]
    - urn: urn:intuitem:test:req_node:dt:s1.b
      assessable: true
      depth: 2
      ref_id: S1.B
      parent_urn: urn:intuitem:test:req_node:dt:s1
      name: s1 b
      implementation_groups: [IG2]
    - urn: urn:intuitem:test:req_node:dt:s2
      assessable: false
      depth: 1
      ref_id: S2
      name: section two
    - urn: urn:intuitem:test:req_node:dt:s2.grp
      assessable: false
      depth: 2
      ref_id: S2.G
      parent_urn: urn:intuitem:test:req_node:dt:s2
      name: s2 group
    - urn: urn:intuitem:test:req_node:dt:s2.a
      assessable: true
      depth: 3
      ref_id: S2.A
      parent_urn: urn:intuitem:test:req_node:dt:s2.grp
      name: s2 a
      implementation_groups: [IG2, IG1]
""".lstrip()

SHOW_SCORE = {"score": EVERYONE_EDIT, "is_scored": EVERYONE_EDIT}


@pytest.fixture
def framework(db):
    startup(sender=None)
    stored, err = StoredLibrary.store_library_content(YAML.encode())
    assert err is None, err
    assert stored.load() is None
    return Framework.objects.get(urn="urn:intuitem:test:framework:domain-tree")


def domain(name, parent=None):
    folder = Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=parent or Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(folder)
    return folder


def audit(fw, folder, name, results, status="in_progress", **kwargs):
    """`results` maps a requirement ref_id to (result, score)."""
    ca = ComplianceAssessment.objects.create(
        name=name,
        framework=fw,
        folder=folder,
        perimeter=Perimeter.objects.create(name=f"p-{name}", folder=folder),
        status=status,
        **kwargs,
    )
    ca.create_requirement_assessments()
    for ref_id, (result, score) in results.items():
        RequirementAssessment.objects.filter(
            compliance_assessment=ca, requirement__ref_id=ref_id
        ).update(result=result, score=score, is_scored=score is not None)
    return ca


def admin():
    user = User.objects.create_superuser("admin@domain-tree-tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(user)
    return user


def member(email, folder, group):
    user = User.objects.create_user(email)
    UserGroup.objects.get(name=group, folder=folder).user_set.add(user)
    return user


def counts_by_audit(feed):
    """{audit name: summed tuple columns 3..9} across sections and signatures."""
    out = {}
    for t in feed["counts"]:
        name = feed["audits"][t[0]]["name"]
        acc = out.setdefault(name, [0] * 7)
        for i, v in enumerate(t[3:]):
            acc[i] += v
    return out


@pytest.mark.django_db
class TestFrameworkStructure:
    def test_sections_signatures_and_scope(self, framework):
        s = framework_structure(framework)
        assert [sec["ref_id"] for sec in s["sections"]] == ["S1", "S2"]
        # IG order follows the framework definition, whatever the node says
        assert s["signatures"] == [["IG1", "IG2"], ["IG2"]]
        # S2.A sits two levels down and still lands in section S2
        assert sorted(map(tuple, s["scope"])) == [(0, 0, 1), (0, 1, 1), (1, 0, 1)]


@pytest.mark.django_db
class TestDomainTreeFeed:
    def test_counts_scores_and_one_audit_per_domain(self, framework):
        d = domain("D")
        old = audit(framework, d, "old", {"S1.A": ("compliant", 4)}, status="done")
        new = audit(
            framework,
            d,
            "new",
            {
                "S1.A": ("compliant", 4),
                "S1.B": ("non_compliant", 1),
                "S2.A": ("not_applicable", 3),
            },
            field_visibility=SHOW_SCORE,
        )
        audit(framework, d, "planned", {}, status="planned")
        ComplianceAssessment.objects.filter(id=old.id).update(
            updated_at=timezone.now() - timedelta(days=1)
        )
        ComplianceAssessment.objects.filter(id=new.id).update(updated_at=timezone.now())

        feed = build_domain_tree(admin(), framework)

        assert [a["name"] for a in feed["audits"]] == ["new"]
        # same figure as the audit page's gauge: AVG of 4 and 1 on 0..4
        assert feed["audits"][0]["score"] == 62.5
        # compliant, partial, non, n/a, not assessed, then scores rebased to
        # 0..1 and their weights (n/a never counts unless anchored)
        assert counts_by_audit(feed) == {"new": [1, 0, 1, 1, 0, 1.25, 2]}

    def test_progress_is_the_audit_pages(self, framework):
        d = domain("D")
        ca = audit(
            framework,
            d,
            "status driven",
            {"S1.A": ("compliant", None), "S1.B": ("non_compliant", None)},
        )
        RequirementAssessment.objects.filter(
            compliance_assessment=ca, requirement__ref_id="S1.A"
        ).update(status="done")
        feed = build_domain_tree(admin(), framework)
        # two answers recorded, but progress follows the status: only S1.A is done
        assert feed["audits"][0]["progress"] == ca.progress == 33

    def test_na_anchored_to_target_scores_like_the_gauge(self, framework):
        d = domain("D")
        audit(
            framework,
            d,
            "anchored",
            {"S1.A": ("compliant", 2), "S2.A": ("not_applicable", None)},
            field_visibility=SHOW_SCORE,
            anchor_na_to_target=True,
            target_score=3,
            min_score=0,
            max_score=4,
        )
        feed = build_domain_tree(admin(), framework)
        # S1.A at 2/4 = 0.5, S2.A anchored at the target 3/4 = 0.75
        assert counts_by_audit(feed)["anchored"][5:] == [1.25, 2]
        assert feed["audits"][0]["score"] == 62.5

    def test_audit_selection_without_done_audits(self, framework):
        d1, d2, d3 = domain("D1"), domain("D2"), domain("D3")
        no_status = audit(framework, d1, "no status", {}, status=None)
        audit(framework, d1, "planned later", {}, status="planned")
        ComplianceAssessment.objects.filter(id=no_status.id).update(
            updated_at=timezone.now() - timedelta(days=3)
        )
        audit(framework, d2, "only planned", {}, status="planned")
        audit(framework, d3, "deprecated", {}, status="deprecated")

        feed = build_domain_tree(admin(), framework)

        # started beats planned even when older; planned alone still shows
        assert sorted(a["name"] for a in feed["audits"]) == [
            "no status",
            "only planned",
        ]

    def test_hidden_scores_are_not_summed(self, framework):
        d = domain("D")
        audit(framework, d, "a", {"S1.A": ("compliant", 4)})
        feed = build_domain_tree(admin(), framework)
        assert counts_by_audit(feed)["a"][5:] == [0, 0]
        assert feed["audits"][0]["score"] is None

    def test_selected_implementation_groups_are_honoured(self, framework):
        d = domain("D")
        audit(
            framework,
            d,
            "ig1",
            {"S1.A": ("compliant", None), "S1.B": ("compliant", None)},
            selected_implementation_groups=["IG1"],
        )
        feed = build_domain_tree(admin(), framework)
        # S1.B is IG2-only: left out; S2.A stays not assessed
        assert counts_by_audit(feed)["ig1"][:5] == [1, 0, 0, 0, 1]

    def test_tree_keeps_unaudited_domains(self, framework):
        audit(framework, domain("Audited"), "a", {})
        domain("Unaudited")
        feed = build_domain_tree(admin(), framework)
        names = {f["name"] for f in feed["folders"]}
        assert {"Audited", "Unaudited"} <= names
        root = [f for f in feed["folders"] if f["parent_id"] is None]
        assert len(root) == 1

    def test_hidden_ancestor_is_sent_without_a_name(self, framework):
        parent = domain("Secret parent")
        child = domain("Child", parent)
        domain("Sibling")
        audit(framework, child, "child audit", {"S1.A": ("compliant", None)})
        reader = member("reader@domain-tree-tests.com", child, "BI-UG-AUD")

        feed = build_domain_tree(reader, framework)

        by_id = {f["id"]: f for f in feed["folders"]}
        child_row = by_id[str(child.id)]
        assert child_row["viewable"] and child_row["name"] == "Child"
        parent_row = by_id[str(parent.id)]
        assert parent_row == {
            "id": str(parent.id),
            "name": "",
            "parent_id": parent_row["parent_id"],
            "viewable": False,
        }
        assert "Sibling" not in {f["name"] for f in feed["folders"]}
        assert [a["name"] for a in feed["audits"]] == ["child audit"]

    def test_respondent_only_sees_assigned_audits_without_results(self, framework):
        d = domain("D")
        assigned = audit(framework, d, "assigned", {"S1.A": ("compliant", None)})
        other = domain("Other")
        audit(framework, other, "not assigned", {"S1.A": ("compliant", None)})
        respondent = member("auditee@domain-tree-tests.com", d, "BI-UG-ADE")
        UserGroup.objects.get(name="BI-UG-ADE", folder=other).user_set.add(respondent)
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=assigned, folder=d, status="in_progress"
        )
        assignment.actor.add(Actor.objects.get_or_create(user=respondent)[0])

        feed = build_domain_tree(respondent, framework)

        assert [
            (a["name"], a["results_hidden"], a["score"], a["progress"])
            for a in feed["audits"]
        ] == [("assigned", True, None, None)]
        assert feed["counts"] == []
        auditor_feed = build_domain_tree(admin(), framework)
        assert {a["name"] for a in auditor_feed["audits"]} == {
            "assigned",
            "not assigned",
        }
        assert all(not a["results_hidden"] for a in auditor_feed["audits"])
        assert auditor_feed["counts"]

    def test_unassigned_respondent_sees_no_audit(self, framework):
        d = domain("D")
        audit(framework, d, "not assigned", {"S1.A": ("compliant", None)})
        respondent = member("auditee@domain-tree-tests.com", d, "BI-UG-ADE")

        assert build_domain_tree(respondent, framework)["audits"] == []

    def test_hidden_result_field_hides_results_for_auditors(self, framework):
        audit(
            framework,
            domain("D"),
            "hidden",
            {"S1.A": ("compliant", None)},
            field_visibility={"result": {"auditor": "hidden", "respondent": "hidden"}},
        )
        feed = build_domain_tree(admin(), framework)
        assert feed["audits"][0]["results_hidden"] is True
        assert feed["counts"] == []

    def test_campaign_filter(self, framework):
        d1, d2 = domain("D1"), domain("D2")
        campaign = Campaign.objects.create(name="c", folder=Folder.get_root_folder())
        audit(framework, d1, "in campaign", {}, campaign=campaign)
        audit(framework, d2, "outside", {})
        feed = build_domain_tree(admin(), framework, campaign_id=str(campaign.id))
        assert [a["name"] for a in feed["audits"]] == ["in campaign"]


@pytest.mark.django_db
class TestDomainTreeEndpoint:
    def test_endpoint(self, framework):
        audit(framework, domain("D"), "a", {"S1.A": ("compliant", None)})
        client = APIClient()
        client.force_authenticate(user=admin())
        url = reverse("frameworks-domain-tree", kwargs={"pk": str(framework.pk)})

        r = client.get(url)
        assert r.status_code == 200, r.content
        assert set(r.json()) == {
            "framework",
            "sections",
            "signatures",
            "scope",
            "folders",
            "audits",
            "counts",
        }
        assert client.get(url, {"campaign": "nope"}).status_code == 400

    def test_frameworks_filter_lists_only_frameworks_in_the_tree(self, framework):
        client = APIClient()
        client.force_authenticate(user=admin())
        url = reverse("frameworks-list")

        def listed():
            r = client.get(url, {"in_domain_tree": "true"})
            assert r.status_code == 200, r.content
            return {f["id"] for f in r.json()["results"]}

        assert str(framework.id) not in listed()
        audit(framework, domain("D"), "gone", {}, status="deprecated")
        assert str(framework.id) not in listed()
        audit(framework, domain("E"), "live", {}, status=None)
        assert str(framework.id) in listed()
