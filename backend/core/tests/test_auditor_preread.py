from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from core.auditor_preread import (
    FEWER_EVIDENCES_THAN_REQUESTS,
    NOTHING_LINKED,
    STALE_EVIDENCE,
    auditor_preread,
    load_guidance,
    readiness,
)
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    RequirementNode,
)
from iam.models import Folder, User

ISO = "urn:intuitem:risk:framework:iso27001-2022"
LIBRARY = Path(__file__).parents[2] / "library/libraries/iso27001-2022.yaml"
KINDS = {"document", "record", "technical", "observation"}
PEOPLE = {
    "top", "ciso", "risk", "auditor", "hr", "legal", "dpo", "proc",
    "facilities", "it_lead", "iam", "infra", "network", "endpoint",
    "service_desk", "sec_ops", "dev", "staff",
}  # fmt: skip
TODAY = date(2026, 11, 15)
GUIDE = {"requests": [{"label": "a", "kind": "record", "fresh_days": 200}, {"label": "b", "kind": "document"}]}  # fmt: skip


def ev(days_old):
    return {"updated_at": datetime(2026, 11, 15, tzinfo=UTC) - timedelta(days=days_old)}


def test_iso27001_guidance_covers_every_assessable_node():
    framework = yaml.safe_load(LIBRARY.read_text())["objects"]["framework"]
    suffixes = {
        n["urn"].rsplit(":", 1)[-1]
        for n in framework["requirement_nodes"]
        if n.get("assessable")
    }
    guidance = load_guidance()[ISO]
    assert set(guidance) == suffixes
    for key, g in guidance.items():
        assert g["questions"] and g["requests"], key
        assert all(q["stage"] in (1, 2) and q["text"] for q in g["questions"]), key
        assert all(r["kind"] in KINDS and r["label"] for r in g["requests"]), key
        assert set(g["interviewees"]) <= PEOPLE, key


def test_readiness_states():
    assert readiness("not_applicable", GUIDE, [], [], TODAY) == ("excluded", [])
    assert readiness("compliant", GUIDE, [], [], TODAY)[0] == "gap"
    assert NOTHING_LINKED in readiness("compliant", GUIDE, [], [], TODAY)[1]
    assert readiness("compliant", GUIDE, [ev(10), ev(20)], [], TODAY) == ("ready", [])
    state, reasons = readiness("compliant", GUIDE, [ev(300)], [], TODAY)
    assert state == "weak"
    assert {STALE_EVIDENCE, FEWER_EVIDENCES_THAN_REQUESTS} <= set(reasons)
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
    control = AppliedControl.objects.create(name="JML process", folder=folder)
    via_control = Evidence.objects.create(name="Access review Q3", folder=folder)
    direct = Evidence.objects.create(name="JML procedure", folder=folder)
    control.evidences.add(via_control)
    ra.applied_controls.add(control)
    ra.evidences.add(direct)

    user = User.objects.create_superuser(email="preread@test.local", password="x")
    item = auditor_preread(audit, user)["items"][0]

    by_name = {e["name"]: e for e in item["evidences"]}
    assert by_name["Access review Q3"]["direct"] is False
    assert by_name["Access review Q3"]["via_controls"] == [control.id]
    assert by_name["JML procedure"]["direct"] is True
    assert by_name["JML procedure"]["via_controls"] == []
    assert NOTHING_LINKED not in item["reasons"]
