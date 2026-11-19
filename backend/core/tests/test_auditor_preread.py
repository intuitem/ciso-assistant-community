from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from core.auditor_preread import (
    EVIDENCE_TO_CONFIRM,
    EVIDENCE_TO_VALIDATE,
    EXPIRES_BEFORE_AUDIT,
    MISSING_FILE,
    NOTHING_LINKED,
    OPEN_FINDING,
    OPEN_MINOR_FINDING,
    REQUEST_NOT_ON_FILE,
    STALE_EVIDENCE,
    UNUSABLE_EVIDENCE,
    auditor_preread,
    guide_key,
    load_audit_guides,
    load_audit_sessions,
    pair_request,
    readiness,
    resolve_guide,
    update_preparation,
)
from core.models import (
    Actor,
    AppliedControl,
    AuditGuide,
    AuditPreparation,
    ComplianceAssessment,
    Evidence,
    EvidenceRequestLink,
    EvidenceRevision,
    Finding,
    FindingsAssessment,
    Framework,
    Perimeter,
    ReferenceControl,
    RequirementNode,
    TaskNode,
    TaskTemplate,
)
from iam.models import Folder, User

ISO = "urn:intuitem:risk:framework:iso27001-2022"
GUIDE_URN = "urn:intuitem:risk:audit_guide:iso27001-2022"
LIBRARY = Path(__file__).parents[2] / "library/libraries/iso27001-2022.yaml"
KINDS = {"document", "record", "technical", "observation"}
PEOPLE = {
    "top", "ciso", "risk", "auditor", "hr", "legal", "dpo", "proc",
    "facilities", "it_lead", "iam", "infra", "network", "endpoint",
    "service_desk", "sec_ops", "dev", "staff",
}  # fmt: skip
TODAY = date(2026, 11, 15)
WINDOWS = {40, 100, 200, 400}
STAGE2_ONLY = {"5.1", "10.1", "10.2"}
GUIDE = {"requests": [{"label": "a", "kind": "record", "fresh_days": 200}, {"label": "b", "kind": "document"}]}  # fmt: skip


def ev(days_old):
    return {
        "updated_at": datetime(2026, 11, 15, tzinfo=UTC) - timedelta(days=days_old),
        "has_file": True,
    }


@pytest.mark.django_db
def test_every_question_says_who_answers_it():
    for key, entry in load_audit_guides()[GUIDE_URN].items():
        for q in entry.get("questions") or []:
            who = q.get("who") or []
            assert 1 <= len(who) <= 3, (key, q["id"])
            assert set(who) <= set(entry["interviewees"]), (key, q["id"])


@pytest.mark.django_db
def test_iso27001_guidance_covers_every_assessable_node():
    framework = yaml.safe_load(LIBRARY.read_text())["objects"]["framework"]
    suffixes = {
        n["urn"].rsplit(":", 1)[-1]
        for n in framework["requirement_nodes"]
        if n.get("assessable")
    }
    guidance = load_audit_guides()[GUIDE_URN]
    key_library = yaml.safe_load(
        (LIBRARY.parent / "key-reference-controls.yaml").read_text()
    )
    key_controls = {c["urn"] for c in key_library["objects"]["reference_controls"]}
    assert set(guidance) == suffixes
    for key, g in guidance.items():
        assert g["questions"] and g["requests"], key
        assert all(q["stage"] in (1, 2) and q["text"] for q in g["questions"]), key
        assert all(r["kind"] in KINDS and r["label"] for r in g["requests"]), key
        assert set(g["interviewees"]) <= PEOPLE, key
        assert all(r.get("fresh_days", 400) in WINDOWS for r in g["requests"]), key
        if key not in STAGE2_ONLY:
            assert any(q["stage"] == 1 for q in g["questions"]), key
        for section, prefix in (
            ("questions", "q"),
            ("requests", "r"),
            ("pitfalls", "p"),
        ):
            ids = [x["id"] for x in g[section]]
            assert len(set(ids)) == len(ids), key
            assert all(i[0] == prefix and i[1:].isdigit() for i in ids), key
        linked = [
            r["reference_control"] for r in g["requests"] if "reference_control" in r
        ]
        # One request per document: two sharing it would be filed by the same evidence.
        assert len(set(linked)) == len(linked) and set(linked) <= key_controls, key
        assert all(0 < r["min"] <= r["max"] and r["unit"] for r in g["sampling"]), key


@pytest.mark.django_db
def test_iso27001_sessions_cover_every_entry_once():
    sessions = load_audit_sessions()[GUIDE_URN]
    members = [m for s in sessions for m in s["members"]]
    assert sorted(members) == sorted(load_audit_guides()[GUIDE_URN])
    assert len({s["id"] for s in sessions}) == len(sessions)
    for s in sessions:
        assert s["label"], s["id"]
        assert all(r["kind"] in KINDS and r["label"] for r in s.get("requests", [])), s[
            "id"
        ]


@pytest.mark.django_db
def test_iso27001_french_covers_every_item():
    """Version 1 ships in French: every question, request, pitfall, sample and session."""
    t = AuditGuide.objects.get(urn=GUIDE_URN).translations["fr"]
    english, french = load_audit_guides()[GUIDE_URN], load_audit_guides("fr")[GUIDE_URN]
    assert set(t["entries"]) == set(english)
    for key, entry in english.items():
        ids = {x["id"] for part in ("questions", "requests", "pitfalls", "sampling") for x in entry.get(part) or []}  # fmt: skip
        assert set(t["entries"][key]) == ids, key
        assert french[key]["requests"][0]["kind"] == entry["requests"][0]["kind"]
        assert french[key]["questions"][0]["text"] != entry["questions"][0]["text"], key
    for s in load_audit_sessions()[GUIDE_URN]:
        own = {x["id"] for part in ("requests", "pitfalls") for x in s.get(part) or []}
        assert set(t["sessions"][s["id"]]) == {"label", *own}, s["id"]
    assert (
        load_audit_sessions("fr")[GUIDE_URN][0]["label"]
        != load_audit_sessions()[GUIDE_URN][0]["label"]
    )


def test_readiness_states():
    assert readiness("not_applicable", GUIDE, [], [], TODAY) == ("excluded", [])
    assert readiness("compliant", GUIDE, [], [], TODAY)[0] == "gap"
    assert NOTHING_LINKED in readiness("compliant", GUIDE, [], [], TODAY)[1]
    # Every request set aside, or only observed on site: nothing is missing.
    assert readiness("compliant", {"requests": []}, [], [], TODAY) == ("ready", [])
    seen_only = {"requests": [{"id": "o", "label": "o", "kind": "observation"}]}
    assert readiness("compliant", seen_only, [], [], TODAY) == ("ready", [])
    # Evidence without a pairing may answer the requests: to confirm, never ready.
    assert readiness("compliant", GUIDE, [ev(10), ev(20)], [], TODAY) == (
        "to_confirm",
        [EVIDENCE_TO_CONFIRM],
    )
    state, reasons = readiness("compliant", GUIDE, [ev(300)], [], TODAY)
    assert state == "weak"
    assert {STALE_EVIDENCE, EVIDENCE_TO_CONFIRM} <= set(reasons)
    # One document may answer several requests: fewer evidences is still to confirm.
    assert readiness("compliant", GUIDE, [ev(10)], [], TODAY) == (
        "to_confirm",
        [EVIDENCE_TO_CONFIRM],
    )
    seen = {"label": "c", "kind": "observation"}
    on_site = {"requests": [*GUIDE["requests"], seen]}
    assert readiness("compliant", on_site, [ev(10), ev(20)], [], TODAY) == (
        "to_confirm",
        [EVIDENCE_TO_CONFIRM],
    )
    monthly = {"requests": [*GUIDE["requests"], {"label": "d", "kind": "technical", "fresh_days": 40}]}  # fmt: skip
    assert STALE_EVIDENCE in readiness("compliant", monthly, [ev(60)] * 3, [], TODAY)[1]
    ok = [ev(10), ev(20)]
    potential_nc = [{"severity": 2, "open": True}]
    assert readiness("compliant", GUIDE, ok, [], TODAY, potential_nc) == ("gap", [OPEN_FINDING, EVIDENCE_TO_CONFIRM])  # fmt: skip
    to_watch = [{"severity": 1, "open": True}]
    assert readiness("compliant", GUIDE, ok, [], TODAY, to_watch) == ("weak", [OPEN_MINOR_FINDING, EVIDENCE_TO_CONFIRM])  # fmt: skip
    closed = [{"severity": 3, "open": False}]
    assert readiness("compliant", GUIDE, ok, [], TODAY, closed) == (
        "to_confirm",
        [EVIDENCE_TO_CONFIRM],
    )
    paired = {"requests": [{"id": "r1", "label": "p", "kind": "document", "reference_control": "u", "fresh_days": 40}]}  # fmt: skip
    filed_old = {"r1": [{"id": 1, **ev(100)}]}
    assert readiness("compliant", paired, [], [], TODAY, (), filed_old) == ("weak", [STALE_EVIDENCE])  # fmt: skip
    assert readiness("compliant", paired, [], [], TODAY, (), {"r1": [{"id": 1, **ev(5)}]}) == ("ready", [])  # fmt: skip
    assert readiness("compliant", paired, [{"id": 2, **ev(5)}], [], TODAY, (), {"r1": []}) == ("to_confirm", [EVIDENCE_TO_CONFIRM])  # fmt: skip
    two = {"requests": [*paired["requests"], {"id": "r2", "label": "q", "kind": "document", "reference_control": "v"}]}  # fmt: skip
    only_r1 = {"r1": [{"id": 1, **ev(5)}], "r2": []}
    assert readiness("compliant", two, [{"id": 1, **ev(5)}], [], TODAY, (), only_r1) == ("weak", [REQUEST_NOT_ON_FILE])  # fmt: skip
    # A paired document without its file holds the request but provides nothing.
    empty = {"r1": [{"id": 1, **ev(5), "has_file": False}]}
    assert readiness("compliant", paired, [], [], TODAY, (), empty) == ("gap", [MISSING_FILE])  # fmt: skip
    one_empty = {
        "r1": [{"id": 1, **ev(5)}],
        "r2": [{"id": 2, **ev(5), "has_file": False}],
    }
    assert readiness("compliant", two, [], [], TODAY, (), one_empty) == ("weak", [MISSING_FILE])  # fmt: skip
    # Rejected, expired or missing: on file but not counted, like no file.
    for status in ("rejected", "expired", "missing"):
        dead = {"r1": [{"id": 1, **ev(5), "status": status}]}
        assert readiness("compliant", paired, [], [], TODAY, (), dead) == ("gap", [UNUSABLE_EVIDENCE])  # fmt: skip
    lapsed = {"r1": [{"id": 1, **ev(5), "expiry_date": TODAY - timedelta(days=1)}]}
    assert readiness("compliant", paired, [], [], TODAY, (), lapsed)[0] == "gap"
    # Draft or in review counts, capped at weak; so does expiring before the audit.
    draft = {"r1": [{"id": 1, **ev(5), "status": "in_review"}]}
    assert readiness("compliant", paired, [], [], TODAY, (), draft) == ("weak", [EVIDENCE_TO_VALIDATE])  # fmt: skip
    soon = {"r1": [{"id": 1, **ev(5), "expiry_date": TODAY + timedelta(days=10)}]}
    due = TODAY + timedelta(days=30)
    assert readiness("compliant", paired, [], [], TODAY, (), soon, due) == ("weak", [EXPIRES_BEFORE_AUDIT])  # fmt: skip
    assert readiness("compliant", paired, [], [], TODAY, (), soon) == ("ready", [])
    errors = [{"severity": "error", "msgid": "x", "msg": "x"}]
    assert readiness("compliant", GUIDE, [ev(1), ev(1)], errors, TODAY)[0] == "gap"


@pytest.mark.django_db
def test_evidence_through_applied_control_is_counted_and_attributed():
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="preread")
    framework = Framework.objects.create(name="ISO", urn=ISO, folder=root)
    RequirementNode.objects.create(
        framework=framework,
        urn="urn:intuitem:risk:req_node:iso27001-2022:a.5.18",
        ref_id="A.5.18",
        name="Access rights",
        assessable=True,
        folder=root,
    )
    audit = ComplianceAssessment.objects.create(
        name="preread",
        framework=framework,
        perimeter=Perimeter.objects.create(name="p", folder=folder),
        folder=folder,
    )
    audit.create_requirement_assessments()
    ra = audit.requirement_assessments.get()
    recert = ReferenceControl.objects.create(
        name="Recertification",
        urn="urn:intuitem:risk:function:doc-pol:proc.recertification",
        folder=root,
    )
    control = AppliedControl.objects.create(
        name="JML process", folder=folder, reference_control=recert
    )
    via_control = Evidence.objects.create(name="Access review Q3", folder=folder)
    direct = Evidence.objects.create(name="JML procedure", folder=folder)
    control.evidences.add(via_control)
    ra.applied_controls.add(control)
    ra.evidences.add(direct)
    stage1 = FindingsAssessment.objects.create(
        name="Stage 1", category="audit", perimeter=audit.perimeter, folder=folder
    )
    Finding.objects.create(
        name="No review record",
        findings_assessment=stage1,
        requirement_node=ra.requirement,
        severity=2,
        status="identified",
        folder=folder,
    )

    user = User.objects.create_superuser(email="preread@test.local", password="x")
    item = auditor_preread(audit, user)["items"][0]

    by_name = {e["name"]: e for e in item["evidences"]}
    assert by_name["Access review Q3"]["direct"] is False
    assert by_name["Access review Q3"]["via_controls"] == [control.id]
    assert by_name["JML procedure"]["direct"] is True
    assert by_name["JML procedure"]["via_controls"] == []
    assert NOTHING_LINKED not in item["reasons"]
    assert [e["name"] for e in item["filed"]["r2"]] == ["Access review Q3"]
    assert item["filed"]["r2"][0]["here"] is True
    assert [f["source"] for f in item["prior_findings"]] == ["Stage 1"]
    assert item["readiness"] == "gap" and OPEN_FINDING in item["reasons"]

    # Tasks are the third path: the evidence a task expects (filed as revisions
    # by its occurrences) and what an occurrence adds, through the requirement
    # or one of its controls; never filed, it is listed but has no file.
    review = TaskTemplate.objects.create(name="Quarterly review", folder=folder)
    review.applied_controls.add(control)
    expected = Evidence.objects.create(name="Review export", folder=folder)
    review.evidences.add(expected)
    EvidenceRevision.objects.create(
        evidence=expected, folder=folder, version=1, link="https://example.test/r"
    )
    drill = TaskTemplate.objects.create(name="Offboarding drill", folder=folder)
    drill.requirement_assessments.add(ra)
    occurrence = TaskNode.objects.create(
        task_template=drill, folder=folder, due_date=date.today()
    )
    ad_hoc = Evidence.objects.create(name="Drill notes", folder=folder)
    occurrence.evidences.add(ad_hoc)
    elsewhere = TaskTemplate.objects.create(name="Unrelated", folder=folder)
    elsewhere.evidences.add(Evidence.objects.create(name="Other", folder=folder))

    item = auditor_preread(audit, user)["items"][0]
    by_name = {e["name"]: e for e in item["evidences"]}
    assert "Other" not in by_name
    assert by_name["Review export"]["via_tasks"] == ["Quarterly review"]
    assert by_name["Review export"]["has_file"] is True
    assert by_name["Review export"]["via_controls"] == []
    assert by_name["Drill notes"]["via_tasks"] == ["Offboarding drill"]
    assert by_name["Drill notes"]["has_file"] is False
    # The backend judges each evidence; the page only shows the verdict.
    assert by_name["Review export"]["issue"] == "to_validate"  # new evidence is a draft
    assert by_name["Drill notes"]["issue"] == "no_file"
    assert all("stale" in e for e in item["evidences"])
    assert by_name["JML procedure"]["via_tasks"] == []
    # The control implements the request's reference control: its task's
    # evidence answers the request too.
    assert "Review export" in [e["name"] for e in item["filed"]["r2"]]


def test_guide_key_falls_back_to_the_parent_number():
    keys = {"4.2", "4.3", "9.3.2", "a.5.18", "a.5.1"}
    assert guide_key("4.2 a)", "urn:x:req_node:copy:4.2.a", keys) == "4.2"
    assert guide_key("A.5.18", "urn:x:req_node:copy:node-12", keys) == "a.5.18"
    assert guide_key("Clause 9.3.2 f)", "urn:x:req_node:copy:n7", keys) == "9.3.2"
    assert guide_key("5", "urn:x:req_node:copy:5", keys) is None
    assert guide_key("A5.1", "urn:x:req_node:copy:n3", keys) == "a.5.1"
    assert guide_key("A.05.01", "urn:x:req_node:copy:n3", keys) == "a.5.1"


@pytest.mark.django_db
def test_guide_projects_on_a_copy_and_pairs_by_hand():
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="copy")
    copy = Framework.objects.create(
        name="ISO copy", urn="urn:custom:risk:framework:iso-copy", folder=root
    )
    # Same numbers as the built-in standard, other URNs and ref_id spelling.
    for i, key in enumerate(load_audit_guides()[GUIDE_URN]):
        RequirementNode.objects.create(
            framework=copy,
            urn=f"urn:custom:risk:req_node:iso-copy:n{i}",
            ref_id=key.upper() if key.startswith("a.") else f"Clause {key}",
            name=key,
            assessable=True,
            folder=root,
        )
    fit = resolve_guide(copy)
    assert fit["applies"] and not fit["exact"] and fit["coverage"] == 1
    audit = ComplianceAssessment.objects.create(
        name="copy",
        framework=copy,
        perimeter=Perimeter.objects.create(name="p", folder=folder),
        folder=folder,
    )
    audit.create_requirement_assessments()
    ra = audit.requirement_assessments.get(requirement__ref_id="A.5.18")
    review = Evidence.objects.create(name="Access review Q3", folder=folder)
    ra.evidences.add(review)
    user = User.objects.create_superuser(email="copy@test.local", password="x")

    pair = {"requirement_assessment": ra.id, "request": "r1", "evidence": review.id}
    assert pair_request(audit, user, pair) is None
    assert pair_request(audit, user, {**pair, "request": "r99"}) == "unknownRequest"
    other = Evidence.objects.create(name="Unrelated", folder=folder)
    assert (
        pair_request(audit, user, {**pair, "evidence": other.id}) == "unknownEvidence"
    )
    # Picked from elsewhere: attached to the requirement, then paired.
    attach = {**pair, "request": "r2", "evidence": other.id, "attach": True}
    assert pair_request(audit, user, attach) is None
    assert ra.evidences.filter(id=other.id).exists()
    ra.evidences.remove(other)
    EvidenceRequestLink.objects.filter(evidence=other).delete()

    preread = auditor_preread(audit, user)
    item = next(i for i in preread["items"] if i["id"] == ra.id)
    assert preread["guide"]["exact"] is False and item["guide_key"] == "a.5.18"
    assert [(e["name"], e["manual"], e["has_file"]) for e in item["filed"]["r1"]] == [
        ("Access review Q3", True, False)
    ]
    assert pair_request(audit, user, {**pair, "remove": True}) is None
    items = auditor_preread(audit, user)["items"]
    assert "r1" not in next(i for i in items if i["id"] == ra.id)["filed"]

    # One document asked by several requirements is paired once for all of them.
    policy = "urn:intuitem:risk:function:doc-pol:pol.main"
    asking = {
        key: next(
            r["id"] for r in e["requests"] if r.get("reference_control") == policy
        )
        for key, e in load_audit_guides()[GUIDE_URN].items()
        if any(r.get("reference_control") == policy for r in e["requests"])
    }
    assert {"a.5.1", "5.2"} <= set(asking)
    doc = Evidence.objects.create(name="ISMS policy v3", folder=folder)
    a51 = audit.requirement_assessments.get(requirement__ref_id="A.5.1")
    c52 = audit.requirement_assessments.get(requirement__ref_id="Clause 5.2")
    a51.evidences.add(doc)
    c52.evidences.add(doc)
    paired = {"requirement_assessment": a51.id, "request": asking["a.5.1"], "evidence": doc.id}  # fmt: skip
    assert pair_request(audit, user, paired) is None
    by_id = {i["id"]: i for i in auditor_preread(audit, user)["items"]}
    assert [e["manual"] for e in by_id[c52.id]["filed"][asking["5.2"]]] == [True]
    # The pairing holds for the audits of this domain only, and says so.
    twin = ComplianceAssessment.objects.create(
        name="twin", framework=copy, perimeter=audit.perimeter, folder=folder
    )
    twin.create_requirement_assessments()
    elsewhere = Folder.objects.create(parent_folder=root, name="elsewhere")
    away = ComplianceAssessment.objects.create(
        name="away",
        framework=copy,
        perimeter=Perimeter.objects.create(name="q", folder=elsewhere),
        folder=elsewhere,
    )
    away.create_requirement_assessments()
    for a in (twin, away):
        a.requirement_assessments.get(requirement__ref_id="A.5.1").evidences.add(doc)
    reach = by_id[a51.id]["filed"][asking["a.5.1"]][0]["reach"]
    assert "Clause 5.2" in reach["requirements"]
    by_id = {i["id"]: i for i in auditor_preread(audit, user)["items"]}
    assert by_id[a51.id]["filed"][asking["a.5.1"]][0]["reach"]["audits"] == 1

    def manual_in(a):
        items = auditor_preread(a, user)["items"]
        a51_there = next(i for i in items if i["ref_id"] == "A.5.1")
        return [e["manual"] for e in a51_there["filed"][asking["a.5.1"]]]

    assert manual_in(twin) == [True]
    assert manual_in(away) == []
    # A set-aside, like a pairing, holds wherever the same document is asked,
    # and is restored from any of them.
    aside = {"requirement_assessment": a51.id, "request": asking["a.5.1"], "reason": "Group policy"}  # fmt: skip
    assert update_preparation(audit, user, {"set_aside": aside}) is None
    by_id = {i["id"]: i for i in auditor_preread(audit, user)["items"]}
    assert by_id[c52.id]["set_aside"][asking["5.2"]]["reason"] == "Group policy"
    back = {"requirement_assessment": c52.id, "request": asking["5.2"], "remove": True}
    assert update_preparation(audit, user, {"set_aside": back}) is None
    by_id = {i["id"]: i for i in auditor_preread(audit, user)["items"]}
    assert not by_id[a51.id]["set_aside"] and not by_id[c52.id]["set_aside"]
    # Unpaired where the pairing shows, though the document is not linked there.
    c52.evidences.remove(doc)
    unpair = {"requirement_assessment": c52.id, "request": asking["5.2"], "evidence": doc.id, "remove": True}  # fmt: skip
    assert pair_request(audit, user, unpair) is None
    by_id = {i["id"]: i for i in auditor_preread(audit, user)["items"]}
    assert not by_id[a51.id]["filed"][asking["a.5.1"]]


@pytest.mark.django_db
def test_preparation_is_lazy_and_drives_readiness():
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="prep")
    framework = Framework.objects.create(name="ISO", urn=ISO, folder=root)
    RequirementNode.objects.create(
        framework=framework,
        urn="urn:intuitem:risk:req_node:iso27001-2022:a.5.18",
        ref_id="A.5.18",
        name="Access rights",
        assessable=True,
        folder=root,
    )

    def new_audit(name):
        audit = ComplianceAssessment.objects.create(
            name=name,
            framework=framework,
            perimeter=Perimeter.objects.create(name=name, folder=folder),
            folder=folder,
        )
        audit.create_requirement_assessments()
        return audit, audit.requirement_assessments.get()

    audit, ra = new_audit("2026")
    user = User.objects.create_superuser(email="prep@test.local", password="x")
    payload = auditor_preread(audit, user)
    assert payload["preparation"] is None and payload["previous_set_asides"] == []
    # A rejected change creates nothing.
    assert (
        update_preparation(audit, user, {"fields": {"stage": "nope"}}) == "invalidField"
    )
    assert update_preparation(audit, user, {"set_aside": {"requirement_assessment": ra.id, "request": "r1"}}) == "reasonRequired"  # fmt: skip
    assert not AuditPreparation.objects.exists()

    fields = {"stage": "stage_2", "start_date": "2026-11-30", "end_date": "2026-12-02", "auditors": "A. Auditor"}  # fmt: skip
    assert update_preparation(audit, user, {"fields": fields}) is None
    prep = AuditPreparation.objects.get()
    assert prep.end_date == date(2026, 12, 2)

    # Set aside: the requests stop counting, and their reason is shown.
    review = Evidence.objects.create(name="Review", folder=folder)
    EvidenceRevision.objects.create(
        evidence=review, folder=folder, version=1, link="https://example.test/r"
    )
    ra.evidences.add(review)
    before = auditor_preread(audit, user)["items"][0]
    assert EVIDENCE_TO_CONFIRM in before["reasons"]
    for rid in ("r1", "r2", "r3", "r4"):
        aside = {"requirement_assessment": ra.id, "request": rid, "reason": "No access rights here"}  # fmt: skip
        assert update_preparation(audit, user, {"set_aside": aside}) is None
    item = auditor_preread(audit, user)["items"][0]
    assert set(item["set_aside"]) == {"r1", "r2", "r3", "r4"}
    assert EVIDENCE_TO_CONFIRM not in item["reasons"]

    # Roles and sessions name actors.
    actor = Actor.objects.get(user=user)
    assert update_preparation(audit, user, {"role": {"role": "ciso", "actors": [actor.id]}}) is None  # fmt: skip
    session = {"session": "access", "date": "2026-12-01", "start_time": "09:00", "location": "Room 2", "attendees": [actor.id]}  # fmt: skip
    assert update_preparation(audit, user, {"session": session}) is None
    assert update_preparation(audit, user, {"role": {"role": "ciso", "actors": ["00000000-0000-0000-0000-000000000000"]}}) == "unknownObject"  # fmt: skip
    assert update_preparation(audit, user, {"role": {"role": "nobody", "actors": []}}) == "unknownObject"  # fmt: skip
    backwards = {**session, "start_time": "10:00", "end_time": "09:00"}
    assert update_preparation(audit, user, {"session": backwards}) == "invalidField"
    prep_payload = auditor_preread(audit, user)["preparation"]
    assert [a["id"] for a in prep_payload["roles"]["ciso"]] == [actor.id]
    assert prep_payload["sessions"]["access"]["location"] == "Room 2"

    # The next audit of the domain is offered the set-asides, and takes them on request.
    nxt, _ = new_audit("2027")
    offered = auditor_preread(nxt, user)["previous_set_asides"]
    assert {a["request"] for a in offered} == {"r1", "r2", "r3", "r4"}
    assert update_preparation(nxt, user, {"carry_over": True}) is None
    assert set(auditor_preread(nxt, user)["items"][0]["set_aside"]) == {"r1", "r2", "r3", "r4"}  # fmt: skip


@pytest.mark.django_db
def test_findings_count_for_every_viewer():
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="seen")
    framework = Framework.objects.create(name="ISO", urn=ISO, folder=root)
    node = RequirementNode.objects.create(
        framework=framework,
        urn="urn:intuitem:risk:req_node:iso27001-2022:a.5.18",
        ref_id="A.5.18",
        name="Access rights",
        assessable=True,
        folder=root,
    )
    audit = ComplianceAssessment.objects.create(
        name="a",
        framework=framework,
        perimeter=Perimeter.objects.create(name="p", folder=folder),
        folder=folder,
    )
    audit.create_requirement_assessments()
    stage1 = FindingsAssessment.objects.create(
        name="Stage 1", category="audit", perimeter=audit.perimeter, folder=folder
    )
    Finding.objects.create(
        name="Secret",
        findings_assessment=stage1,
        requirement_node=node,
        severity=2,
        status="identified",
        folder=folder,
    )
    # A finding of another domain on the same requirement is not this audit's.
    other = Folder.objects.create(parent_folder=root, name="other")
    Finding.objects.create(
        name="Elsewhere",
        findings_assessment=FindingsAssessment.objects.create(
            name="Other", category="audit", folder=other
        ),
        requirement_node=node,
        severity=3,
        status="identified",
        folder=other,
    )
    nobody = User.objects.create_user(email="nobody@test.local")
    item = auditor_preread(audit, nobody)["items"][0]
    assert OPEN_FINDING in item["reasons"]
    assert item["prior_findings"][0]["name"] is None
    assert item["prior_findings"][0]["source"] is False
    assert len(item["prior_findings"]) == 1


@pytest.mark.django_db
def test_own_guide_wins_only_on_its_own_framework():
    root = Folder.get_root_folder()
    ours = AuditGuide.objects.get(urn=GUIDE_URN)
    iso = Framework.objects.create(name="ISO", urn=ISO, folder=root)
    copy = Framework.objects.create(
        name="ISO copy", urn="urn:custom:risk:framework:copy", folder=root
    )
    other = Framework.objects.create(
        name="Other", urn="urn:custom:risk:framework:other", folder=root
    )
    for fw in (iso, copy):
        for i, key in enumerate(ours.entries):
            RequirementNode.objects.create(
                framework=fw,
                urn=f"{fw.urn.replace('framework', 'req_node')}:{key}",
                ref_id=key.upper(),
                assessable=True,
                folder=root,
            )

    def own(urn, framework):
        return AuditGuide.objects.create(
            urn=urn,
            ref_id=urn.rsplit(":", 1)[-1],
            provider="ACME",
            framework_urn=framework,
            entries=ours.entries,
            sessions=ours.sessions,
            folder=root,
        )

    # A guide written for another framework does not take over by numbering.
    own("urn:acme:risk:audit_guide:other", other.urn)
    assert resolve_guide(iso)["guide"] == GUIDE_URN
    assert resolve_guide(copy)["guide"] == GUIDE_URN
    # The organisation's own guide for the same framework wins over ours.
    own("urn:acme:risk:audit_guide:iso", ISO)
    assert resolve_guide(iso)["guide"] == "urn:acme:risk:audit_guide:iso"


@pytest.mark.django_db
def test_list_shows_only_audits_whose_preread_can_be_opened():
    from rest_framework.test import APIClient

    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="listed")
    framework = Framework.objects.create(name="ISO", urn=ISO, folder=root)
    ComplianceAssessment.objects.create(
        name="listed",
        framework=framework,
        perimeter=Perimeter.objects.create(name="p", folder=folder),
        folder=folder,
    )
    url = "/api/compliance-assessments/auditor_preread_audits/"
    for user, count in (
        (User.objects.create_superuser(email="lister@test.local", password="x"), 1),
        (User.objects.create_user(email="nobody-list@test.local"), 0),
    ):
        client = APIClient()
        client.force_authenticate(user)
        assert len(client.get(url).json()) == count


def test_iso_requirements_suggest_every_control_the_guide_asks_for():
    """A request answered through a reference control only fills itself when the
    ISO requirement suggests that control: keep the library and the guide in step."""
    framework = yaml.safe_load(LIBRARY.read_text())["objects"]["framework"]
    suggested = {
        n["urn"].rsplit(":", 1)[-1]: set(n.get("reference_controls") or [])
        for n in framework["requirement_nodes"]
    }
    guide = yaml.safe_load(
        (LIBRARY.parent / "audit-guide-iso27001-2022.yaml").read_text()
    )["objects"]["audit_guides"][0]
    for key, entry in guide["entries"].items():
        for r in entry["requests"]:
            if r.get("reference_control"):
                assert r["reference_control"] in suggested[key], (key, r["id"])


def _guide(**over):
    entry = {
        "questions": [{"id": "q1", "stage": 2, "who": ["ciso"], "text": "Show me."}],
        "requests": [{"id": "r1", "label": "Records", "kind": "record"}],
        "interviewees": ["ciso"],
    }
    return {
        "urn": "urn:acme:risk:audit_guide:t",
        "ref_id": "t",
        "framework": ISO,
        "entries": {"A.05.18": entry},
        **over,
    }


def test_guide_validation_catches_what_would_break_the_preread():
    from library.utils import AuditGuideImporter

    assert AuditGuideImporter(_guide()).is_valid() is None
    entry = _guide()["entries"]["A.05.18"]
    broken = [
        {"entries": {"a.5.18": entry, "A.5.18": entry}},  # same number twice
        {"entries": {"a.5.18": {**entry, "pitfalls": [{"id": "q1", "text": "x"}]}}},
        {
            "entries": {
                "a.5.18": {
                    **entry,
                    "requests": [
                        {
                            "id": "r1",
                            "label": "x",
                            "kind": "record",
                            "fresh_days": "monthly",
                        }
                    ],
                }
            }
        },
        {
            "entries": {
                "a.5.18": {
                    **entry,
                    "requests": [
                        {
                            "id": "r1",
                            "label": "x",
                            "kind": "record",
                            "reference_control": ["a"],
                        }
                    ],
                }
            }
        },
        {"entries": {"a.5.18": ["not", "a", "mapping"]}},
        {"translations": {"fr": {"entries": {"a.5.18": "texte"}}}},
    ]
    for over in broken:
        assert AuditGuideImporter(_guide(**over)).is_valid(), over


def test_guide_keys_are_normalized_like_requirements():
    fields = AuditGuide.fields_from(
        _guide(
            sessions=[{"id": "s", "members": ["A.05.18"]}],
            translations={"fr": {"entries": {"A.05.18": {"q1": "Montrez."}}}},
        )
    )
    assert list(fields["entries"]) == ["a.5.18"]
    assert fields["sessions"][0]["members"] == ["a.5.18"]
    assert list(fields["translations"]["fr"]["entries"]) == ["a.5.18"]


@pytest.mark.django_db
def test_forced_guide_that_is_gone_falls_back():
    framework = Framework.objects.create(
        name="ISO", urn=ISO, folder=Folder.get_root_folder()
    )
    fit = resolve_guide(framework, "urn:acme:risk:audit_guide:unloaded")
    assert fit["guide"] == GUIDE_URN and fit["applies"]


@pytest.mark.django_db
def test_library_update_refuses_bad_guides_and_drops_removed_ones():
    from core.models import LoadedLibrary, StoredLibrary

    def library(version, guides):
        return yaml.safe_dump(
            {
                "urn": "urn:acme:risk:library:guides",
                "locale": "en",
                "ref_id": "acme-guides",
                "name": "ACME guides",
                "version": version,
                "provider": "ACME",
                "packager": "ACME",
                "objects": {"audit_guides": guides},
            }
        ).encode()

    two = [_guide(), _guide(urn="urn:acme:risk:audit_guide:u", ref_id="u")]
    stored, error = StoredLibrary.store_library_content(library(1, two))
    assert error is None and stored.load() is None
    loaded = LoadedLibrary.objects.get(urn="urn:acme:risk:library:guides")
    assert loaded.audit_guides.count() == 2

    bad = [_guide(entries={"a.5.18": {"requests": [{"id": "r1", "label": "x"}]}})]
    StoredLibrary.store_library_content(library(2, bad))
    assert loaded.update() == "invalidLibraryUpdate"
    assert loaded.audit_guides.count() == 2

    # Another library's guide URN cannot be taken over.
    StoredLibrary.store_library_content(
        library(3, [_guide(urn="urn:intuitem:risk:audit_guide:iso27001-2022")])
    )
    assert loaded.update() == "invalidLibraryUpdate"

    StoredLibrary.store_library_content(library(4, [_guide()]))
    assert loaded.update() is None
    assert list(loaded.audit_guides.values_list("urn", flat=True)) == [
        "urn:acme:risk:audit_guide:t"
    ]


@pytest.mark.django_db
def test_preread_permissions_with_builtin_roles():
    """Reader: no pre-read. Analyst: reads and prepares in their domain only,
    and cannot pair an evidence they cannot see."""
    from rest_framework.test import APIClient

    from core.startup import startup
    from iam.models import Role, RoleAssignment, UserGroup

    startup(sender=None)
    root = Folder.get_root_folder()
    framework = Framework.objects.create(name="ISO", urn=ISO, folder=root)
    RequirementNode.objects.create(
        framework=framework,
        urn="urn:intuitem:risk:req_node:iso27001-2022:a.6.3",
        ref_id="A.6.3",
        assessable=True,
        folder=root,
    )

    def domain(name):
        folder = Folder.objects.create(
            name=name, content_type=Folder.ContentType.DOMAIN, parent_folder=root
        )
        audit = ComplianceAssessment.objects.create(
            name=name,
            framework=framework,
            perimeter=Perimeter.objects.create(name=name, folder=folder),
            folder=folder,
        )
        audit.create_requirement_assessments()
        return folder, audit

    mine, audit = domain("mine")
    theirs, other_audit = domain("theirs")
    secret = Evidence.objects.create(name="Their secret", folder=theirs)

    def member(email, role):
        user = User.objects.create_user(email=email)
        group = UserGroup.objects.create(name=email, folder=mine)
        group.user_set.add(user)
        ra = RoleAssignment.objects.create(
            user_group=group, role=Role.objects.get(name=role), folder=mine
        )
        ra.perimeter_folders.add(mine)
        client = APIClient()
        client.force_authenticate(user)
        return client

    reader, analyst = member("r@t.local", "BI-RL-AUD"), member("a@t.local", "BI-RL-ANA")

    def url(a, tail=""):
        return f"/api/compliance-assessments/{a.id}/auditor_preread/{tail}"

    assert reader.get(url(audit)).status_code == 403
    assert reader.post(url(audit, "preparation/"), {"fields": {"stage": "stage_2"}}, format="json").status_code == 403  # fmt: skip
    assert analyst.get(url(audit)).status_code == 200
    assert analyst.post(url(audit, "preparation/"), {"fields": {"stage": "stage_2"}}, format="json").status_code == 204  # fmt: skip
    # Another domain's audit does not exist for them.
    assert analyst.get(url(other_audit)).status_code == 404
    assert analyst.post(url(other_audit, "preparation/"), {"fields": {"stage": "stage_2"}}, format="json").status_code == 404  # fmt: skip
    # An evidence of another domain cannot be paired, even with attach.
    ra = audit.requirement_assessments.get()
    request = load_audit_guides()[GUIDE_URN]["a.6.3"]["requests"][0]["id"]
    pair = {"requirement_assessment": str(ra.id), "request": request, "evidence": str(secret.id), "attach": True}  # fmt: skip
    response = analyst.post(url(audit, "pair/"), pair, format="json")
    assert response.status_code == 400 and response.json() == {
        "error": "unknownEvidence"
    }
    assert not ra.evidences.filter(id=secret.id).exists()
    # Malformed ids are a 400 with a fixed code, never a stack trace.
    bad = analyst.post(
        url(audit, "pair/"), {**pair, "evidence": "not-a-uuid"}, format="json"
    )
    assert bad.status_code == 400 and bad.json() == {"error": "invalidField"}
    # A locked audit's requirements cannot gain an evidence through the pre-read.
    ComplianceAssessment.objects.filter(id=audit.id).update(is_locked=True)
    locked = analyst.post(url(audit, "pair/"), pair, format="json")
    assert locked.status_code == 403


def test_paired_evidence_keeps_its_request_verdict():
    old = {**ev(300), "id": "e1"}
    monthly = {"requests": [{"id": "r1", "label": "x", "kind": "record", "fresh_days": 40}]}  # fmt: skip
    listed = dict(old)
    readiness("compliant", monthly, [listed], [], TODAY, filed={"r1": [dict(old)]})
    assert listed["stale"] is True


@pytest.mark.django_db
def test_guide_urns_must_be_strings_and_unique():
    from core.models import LoadedLibrary, StoredLibrary
    from library.utils import AuditGuideImporter

    assert AuditGuideImporter(_guide(urn=None)).is_valid()
    assert AuditGuideImporter(_guide(framework=None)).is_valid()
    content = yaml.safe_dump(
        {
            "urn": "urn:acme:risk:library:twins",
            "locale": "en",
            "ref_id": "twins",
            "name": "Twins",
            "version": 1,
            "provider": "ACME",
            "packager": "ACME",
            "objects": {"audit_guides": [_guide(), _guide(ref_id="u")]},
        }
    ).encode()
    stored, error = StoredLibrary.store_library_content(content)
    assert error is None
    assert stored.load() is not None
    assert not LoadedLibrary.objects.filter(urn="urn:acme:risk:library:twins").exists()


def test_a_guide_that_can_apply_ranks_first():
    from core.auditor_preread import _rank

    def fit(coverage, matched):
        return {"exact": False, "own": False, "builtin": False, "coverage": coverage, "matched": matched, "total": 100}  # fmt: skip

    assert _rank(fit(0.95, 95)) > _rank(fit(1.0, 1))


def test_non_text_translation_falls_back_to_english():
    from core.auditor_preread import _localized

    item = {"questions": [{"id": "q1", "text": "Show me."}]}
    assert _localized(item, {"q1": {"text": "x"}})["questions"][0]["text"] == "Show me."
