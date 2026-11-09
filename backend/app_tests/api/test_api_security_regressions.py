import importlib
import inspect
import io
import json
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from docxtpl import DocxTemplate
from knox.models import AuthToken
from lxml import etree
from rest_framework.exceptions import PermissionDenied
from rest_framework.relations import ManyRelatedField, RelatedField
from rest_framework.test import APIClient

from core.generators import render_docx_report
from core.models import (
    Actor,
    Asset,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Finding,
    Framework,
    Incident,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    StoredLibrary,
    TaskNode,
    TaskTemplate,
    TimelineEntry,
)
from core.serializers import BaseModelSerializer
from ebios_rm.models import EbiosRMStudy, FearedEvent
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, Role, RoleAssignment, SCIMToken, User, UserGroup
from portals.models import FrameworkSnapshot, Portal
from test_fixtures import RISK_MATRIX_JSON_DEFINITION
from tprm.models import Entity, EntityAssessment
from webhooks.models import WebhookEventType

BACKEND = Path(__file__).resolve().parents[2]
PAYLOAD = '</w:t></w:r><w:fldSimple w:instr=" INCLUDEPICTURE x "/><w:r><w:t>'


def _client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}")
    return c


def _domain(name):
    d = Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(d)
    return d


class StubLLM:
    def __getattr__(self, name):
        return lambda *a, **k: ""


@pytest.mark.django_db
def test_chat_ebios_assist_needs_write_permission(app_config):
    dom = _domain("D1")
    Asset.objects.create(name="A1", folder=dom)
    RiskMatrix.objects.create(
        name="M1",
        folder=Folder.get_root_folder(),
        is_enabled=True,
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    reader = User.objects.create_user(email="reader@tests.com")
    ra = RoleAssignment.objects.create(
        user=reader,
        role=Role.objects.get(name="BI-RL-AUD"),
        folder=dom,
        is_recursive=True,
    )
    ra.perimeter_folders.add(dom)
    c = _client(reader)
    sid = c.post(
        "/api/chat/sessions/", {"folder": str(dom.id), "title": "t"}, format="json"
    ).json()["id"]
    with mock.patch("chat.views.get_llm", return_value=StubLLM()):
        r = c.post(
            f"/api/chat/sessions/{sid}/message/",
            {"content": "help me with ebios"},
            format="json",
        )
        body = b"".join(r.streaming_content)
    assert b"permission" in body
    assert EbiosRMStudy.objects.count() == 0


@pytest.mark.django_db
def test_audit_analytics_respect_respondent_scope(app_config):
    stored, err = StoredLibrary.store_library_content(
        (BACKEND / "core/tests/fixtures/test-splash-assessable.yaml").read_bytes()
    )
    assert err is None and stored.load() is None
    fw = Framework.objects.get(urn="urn:intuitem:test:framework:splash-assessable")
    dom = _domain("Dom")
    per = Perimeter.objects.create(name="Per", folder=dom)
    mine = ComplianceAssessment.objects.create(
        name="Mine", framework=fw, perimeter=per, folder=dom
    )
    mine.create_requirement_assessments()
    hidden = ComplianceAssessment.objects.create(
        name="Hidden", framework=fw, perimeter=per, folder=dom
    )
    hidden.create_requirement_assessments()
    RequirementAssessment.objects.filter(compliance_assessment=hidden).update(
        result="non_compliant"
    )
    u = User.objects.create_user("auditee@tests.com")
    actor, _ = Actor.objects.get_or_create(user=u)
    a = RequirementAssignment.objects.create(
        compliance_assessment=mine, folder=dom, status="in_progress"
    )
    a.actor.add(actor)
    a.requirement_assessments.set(
        RequirementAssessment.objects.filter(compliance_assessment=mine)
    )
    RequirementAssignment.objects.create(
        compliance_assessment=mine, folder=dom
    ).actor.add(actor)
    ComplianceAssessment.objects.filter(id=mine.id).update(status="in_progress")
    UserGroup.objects.get(name="BI-UG-ADE", folder=dom).user_set.add(u)
    c = _client(u)

    assert (
        "Hidden" not in c.get("/api/compliance-assessments/analytics/").content.decode()
    )
    names = c.get("/api/get_audits_metrics/").json()["results"]["audits_stats"]["names"]
    assert names == ["Mine"]
    compliance = c.get("/api/get_metrics/").json()["results"]["compliance"]
    assert compliance["audits"] == 1
    assert compliance["non_compliant_items"] == 0
    series = c.get("/api/get_combined_assessments_status/").json()["results"]["series"]
    audits = next(s for s in series if s["name"] == "complianceAssessments")
    assert sum(audits["data"]) == 1


@pytest.mark.django_db
def test_scim_token_rejected_outside_scim(app_config):
    admin = User.objects.create_user("admin@tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    instance, raw = AuthToken.objects.create(user=admin, expiry=None)
    SCIMToken.objects.create(auth_token=instance, name="IdP")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {raw}")
    assert c.get("/api/iam/current-user/").status_code == 401
    assert c.post("/api/iam/session-token/").status_code == 401


@pytest.mark.django_db
def test_password_change_revokes_other_login_tokens(app_config):
    u = User.objects.create_user("u@tests.com", password="Old-Pass-123!x")
    stolen = _client(u)
    current = _client(u)
    r = current.post(
        "/api/iam/change-password/",
        {
            "old_password": "Old-Pass-123!x",
            "new_password": "New-Pass-456!y",
            "confirm_new_password": "New-Pass-456!y",
        },
        format="json",
    )
    assert r.status_code == 200
    assert stolen.get("/api/iam/current-user/").status_code == 401
    assert current.get("/api/iam/current-user/").status_code == 200


HYPERLINK_PAYLOAD = (
    "Audit Q4</w:t></w:r><w:r><w:fldSimple w:instr=' HYPERLINK "
    '"https://example.com/phishing-test" \'><w:r><w:rPr><w:rStyle w:val="Hyperlink"/>'
    "</w:rPr><w:t>CLICK HERE TO RE-AUTHENTICATE</w:t></w:r></w:fldSimple></w:r>"
    "<w:r><w:t>"
)


@pytest.mark.parametrize("payload", [PAYLOAD, HYPERLINK_PAYLOAD])
def test_docx_report_escapes_stored_strings(payload):
    doc = DocxTemplate(BACKEND / "core/templates/core/audit_report_template_en.docx")
    item = {
        "name": payload,
        "description": "d",
        "prio": "P1",
        "status": "s",
        "eta": "-",
        "category": "c",
        "coverage": 1,
    }
    render_docx_report(
        doc,
        {
            "audit": {"name": payload, "framework": {"name": "F"}},
            "req": {},
            "p1_controls": [item],
            "full_controls": [item],
            "drifts_per_domain": [],
        },
    )
    out = io.BytesIO()
    doc.save(out)
    archive = zipfile.ZipFile(out)
    xml = archive.read("word/document.xml")
    root = etree.fromstring(xml)
    for tag in ("fldSimple", "fldChar", "instrText", "hyperlink"):
        assert not root.findall(f".//{{*}}{tag}"), tag
    assert b"example.com" not in archive.read("word/_rels/document.xml.rels")
    assert b"INCLUDEPICTURE" in xml or b"HYPERLINK" in xml


@pytest.mark.django_db
def test_portal_cannot_reference_foreign_snapshot(app_config):
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    gs.value = {**(gs.value or {}), "custom_portals": True}
    gs.save()
    clear_feature_flags_cache()
    fa = _domain("DomA")
    fb = _domain("DomB")
    snap = FrameworkSnapshot.objects.create(
        name="B snapshot", folder=fb, framework_ref_id="FX", summary={}, content=[]
    )
    u = User.objects.create_user(email="analyst@tests.com")
    ra = RoleAssignment.objects.create(
        user=u, role=Role.objects.get(name="BI-RL-ANA"), folder=fa, is_recursive=True
    )
    ra.perimeter_folders.add(fa)
    r = _client(u).post(
        "/api/portals/",
        {
            "name": "p",
            "folder": str(fa.id),
            "is_public": True,
            "status": "published",
            "enabled": True,
            "content": {
                "sections": [
                    {
                        "items": [
                            {"kind": "framework", "target": {"snapshot": str(snap.id)}}
                        ]
                    }
                ]
            },
        },
        format="json",
    )
    assert r.status_code == 403
    assert not Portal.objects.filter(name="p").exists()


@pytest.mark.django_db
def test_domain_import_ignores_foreign_attachment_names(
    authenticated_client, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    c = authenticated_client
    root = Folder.get_root_folder()
    victim = Folder.objects.create(
        name="Victim", parent_folder=root, content_type=Folder.ContentType.DOMAIN
    )
    vrev = EvidenceRevision.objects.create(
        evidence=Evidence.objects.create(name="v", folder=victim),
        folder=victim,
        version=1,
        attachment=ContentFile(b"SECRET", name="report.pdf"),
    )
    src = Folder.objects.create(
        name="Src", parent_folder=root, content_type=Folder.ContentType.DOMAIN
    )
    EvidenceRevision.objects.create(
        evidence=Evidence.objects.create(name="s", folder=src),
        folder=src,
        version=1,
        attachment=ContentFile(b"x", name="s.txt"),
    )
    r = c.get(f"/api/folders/{src.id}/export/")
    data = json.loads(
        zipfile.ZipFile(
            io.BytesIO(b"".join(r.streaming_content) if r.streaming else r.content)
        ).read("data.json")
    )
    for o in data["objects"]:
        if o["model"] == "core.evidencerevision":
            o["fields"]["attachment"] = vrev.attachment.name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zout:
        zout.writestr("data.json", json.dumps(data))
    r = c.post(
        "/api/folders/import/",
        data=buf.getvalue(),
        content_type="application/zip",
        HTTP_CONTENT_DISPOSITION='attachment; filename="d.zip"',
        HTTP_X_CISOASSISTANTDOMAINNAME="Imported",
    )
    assert r.status_code == 200
    imported = Folder.objects.get(name="Imported")
    assert not EvidenceRevision.objects.get(evidence__folder=imported).attachment
    c.delete(f"/api/folders/{imported.id}/")
    assert default_storage.exists(vrev.attachment.name)


@pytest.mark.django_db
def test_child_cannot_be_written_into_parent_folder_without_rights(app_config):
    a, b = _domain("dom-A"), _domain("dom-B")
    u = User.objects.create_user("ana@tests.com")
    UserGroup.objects.get(name="BI-UG-ANA", folder=a).user_set.add(u)
    c = _client(u)
    ma = RiskMatrix.objects.create(
        name="ma", folder=a, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    mb = RiskMatrix.objects.create(
        name="mb", folder=b, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    sa = EbiosRMStudy.objects.create(name="study-A", risk_matrix=ma, folder=a)
    sb = EbiosRMStudy.objects.create(name="study-B", risk_matrix=mb, folder=b)
    ib = Incident.objects.create(name="incident-B", folder=b)

    own = FearedEvent.objects.create(name="own", ebios_rm_study=sa)
    with (
        mock.patch.object(FearedEvent, "save") as fe_save,
        mock.patch.object(TimelineEntry, "save") as te_save,
    ):
        r = c.post(
            "/api/ebios-rm/feared-events/",
            {"name": "fe", "ebios_rm_study": str(sb.id), "folder": str(a.id)},
            format="json",
        )
        assert r.status_code == 403
        r = c.patch(
            f"/api/ebios-rm/feared-events/{own.id}/",
            {"ebios_rm_study": str(sb.id)},
            format="json",
        )
        assert r.status_code == 403
        r = c.post(
            "/api/timeline-entries/",
            {
                "entry": "te",
                "entry_type": "observation",
                "incident": str(ib.id),
                "folder": str(a.id),
                "timestamp": timezone.now().isoformat(),
            },
            format="json",
        )
        assert r.status_code == 403
    fe_save.assert_not_called()
    te_save.assert_not_called()
    own.refresh_from_db()
    assert own.folder_id == a.id

    r = c.post(
        "/api/ebios-rm/feared-events/",
        {"name": "ok", "ebios_rm_study": str(sa.id), "folder": str(a.id)},
        format="json",
    )
    assert r.status_code == 201


@pytest.mark.django_db
def test_refused_risk_assessment_move_leaves_its_scenarios(app_config):
    a, b = _domain("dom-A"), _domain("dom-B")
    u = User.objects.create_user("ana@tests.com")
    UserGroup.objects.get(name="BI-UG-ANA", folder=a).user_set.add(u)
    c = _client(u)
    ra = RiskAssessment.objects.create(
        name="ra",
        folder=a,
        perimeter=Perimeter.objects.create(name="pa", folder=a),
        risk_matrix=RiskMatrix.objects.create(
            name="ma", folder=a, json_definition=RISK_MATRIX_JSON_DEFINITION
        ),
    )
    scenario = RiskScenario.objects.create(name="rs", risk_assessment=ra)
    pb = Perimeter.objects.create(name="pb", folder=b)

    r = c.patch(
        f"/api/risk-assessments/{ra.id}/", {"perimeter": str(pb.id)}, format="json"
    )
    assert r.status_code == 403
    ra.refresh_from_db()
    scenario.refresh_from_db()
    assert ra.folder_id == a.id
    assert scenario.folder_id == a.id

    UserGroup.objects.get(name="BI-UG-ANA", folder=b).user_set.add(u)
    r = c.patch(
        f"/api/risk-assessments/{ra.id}/", {"perimeter": str(pb.id)}, format="json"
    )
    assert r.status_code == 200
    scenario.refresh_from_db()
    assert scenario.folder_id == b.id


@pytest.mark.django_db
def test_agg_data_with_visible_risk_assessment(authenticated_client):
    dom = _domain("RA-Dom")
    RiskAssessment.objects.create(
        name="ra",
        folder=dom,
        perimeter=Perimeter.objects.create(name="p", folder=dom),
        risk_matrix=RiskMatrix.objects.create(
            name="m", folder=dom, json_definition=RISK_MATRIX_JSON_DEFINITION
        ),
    )
    r = authenticated_client.get("/api/agg_data/")
    assert r.status_code == 200
    assert "degraded" in r.json()["results"]["mtg_status_out"]


def _cross_domain_audit():
    a, b = _domain("dom-A"), _domain("dom-B")
    analyst = User.objects.create_user("ana@tests.com")
    UserGroup.objects.get(name="BI-UG-ANA", folder=a).user_set.add(analyst)
    root = Folder.get_root_folder()
    framework = Framework.objects.create(name="fw", folder=root, urn="urn:x:fw")
    RequirementNode.objects.create(
        framework=framework, urn="urn:x:r1", assessable=True, folder=root, name="r1"
    )
    perimeter_a = Perimeter.objects.create(name="pa", folder=a)
    perimeter_b = Perimeter.objects.create(name="pb", folder=b)
    audit = ComplianceAssessment.objects.create(
        name="audit-B", framework=framework, folder=b, perimeter=perimeter_b
    )
    audit.create_requirement_assessments()
    requirement = RequirementAssessment.objects.get(compliance_assessment=audit)
    requirement.observation = "CANARY"
    requirement.save()
    return a, b, analyst, framework, perimeter_a, perimeter_b, audit, requirement


@pytest.mark.django_db
def test_entity_assessment_cannot_be_pointed_at_foreign_audit(app_config):
    a, b, analyst, _, perimeter_a, _, audit, requirement = _cross_domain_audit()
    c = _client(analyst)
    entity = Entity.objects.create(name="vendor", folder=a)
    assessment = EntityAssessment.objects.create(
        name="ea", entity=entity, folder=a, perimeter=perimeter_a
    )

    c.patch(
        f"/api/entity-assessments/{assessment.id}/",
        {"compliance_assessment": str(audit.id)},
        format="json",
    )
    c.patch(
        f"/api/entity-assessments/{assessment.id}/",
        {"representatives": [str(analyst.id)]},
        format="json",
    )

    assessment.refresh_from_db()
    assert assessment.compliance_assessment_id is None
    assert not analyst.user_groups.filter(folder=b).exists()
    assert c.get(f"/api/requirement-assessments/{requirement.id}/").status_code == 404


@pytest.mark.django_db
def test_audit_baseline_must_be_visible(app_config):
    a, _, analyst, framework, perimeter_a, _, audit, _ = _cross_domain_audit()
    r = _client(analyst).post(
        "/api/compliance-assessments/",
        {
            "name": "clone",
            "framework": str(framework.id),
            "perimeter": str(perimeter_a.id),
            "folder": str(a.id),
            "baseline": str(audit.id),
        },
        format="json",
    )
    assert r.status_code == 403
    assert not ComplianceAssessment.objects.filter(name="clone").exists()


@pytest.mark.django_db
def test_risk_assessment_study_must_be_visible(app_config):
    a, b, analyst, _, perimeter_a, perimeter_b, _, _ = _cross_domain_audit()
    matrix_a = RiskMatrix.objects.create(
        name="ma", folder=a, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    matrix_b = RiskMatrix.objects.create(
        name="mb", folder=b, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    study = EbiosRMStudy.objects.create(name="study-B", risk_matrix=matrix_b, folder=b)
    victim = RiskAssessment.objects.create(
        name="ra-b",
        folder=b,
        perimeter=perimeter_b,
        risk_matrix=matrix_b,
        ebios_rm_study=study,
    )
    r = _client(analyst).post(
        "/api/risk-assessments/",
        {
            "name": "x",
            "folder": str(a.id),
            "perimeter": str(perimeter_a.id),
            "risk_matrix": str(matrix_a.id),
            "ebios_rm_study": str(study.id),
        },
        format="json",
    )
    assert r.status_code == 403
    victim.refresh_from_db()
    assert victim.ebios_rm_study_id == study.id


@pytest.mark.django_db
def test_audit_in_global_folder_is_not_a_shared_baseline(app_config):
    a, _, analyst, framework, perimeter_a, _, _, _ = _cross_domain_audit()
    root = Folder.get_root_folder()
    global_audit = ComplianceAssessment.objects.create(
        name="global", framework=framework, folder=root
    )
    r = _client(analyst).post(
        "/api/compliance-assessments/",
        {
            "name": "clone",
            "framework": str(framework.id),
            "perimeter": str(perimeter_a.id),
            "folder": str(a.id),
            "baseline": str(global_audit.id),
        },
        format="json",
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_study_link_needs_change_on_the_study(app_config):
    a, b, analyst, _, perimeter_a, perimeter_b, _, _ = _cross_domain_audit()
    UserGroup.objects.get(name="BI-UG-AUD", folder=b).user_set.add(analyst)
    matrix_a = RiskMatrix.objects.create(
        name="ma", folder=a, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    matrix_b = RiskMatrix.objects.create(
        name="mb", folder=b, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    study = EbiosRMStudy.objects.create(name="study-B", risk_matrix=matrix_b, folder=b)
    victim = RiskAssessment.objects.create(
        name="ra-b",
        folder=b,
        perimeter=perimeter_b,
        risk_matrix=matrix_b,
        ebios_rm_study=study,
    )
    r = _client(analyst).post(
        "/api/risk-assessments/",
        {
            "name": "x",
            "folder": str(a.id),
            "perimeter": str(perimeter_a.id),
            "risk_matrix": str(matrix_a.id),
            "ebios_rm_study": str(study.id),
        },
        format="json",
    )
    assert r.status_code == 403
    victim.refresh_from_db()
    assert victim.ebios_rm_study_id == study.id


@pytest.mark.django_db
def test_study_link_cannot_unlink_a_foreign_assessment(app_config):
    a, b, analyst, _, perimeter_a, perimeter_b, _, _ = _cross_domain_audit()
    matrix_a = RiskMatrix.objects.create(
        name="ma", folder=a, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    study = EbiosRMStudy.objects.create(name="study-A", risk_matrix=matrix_a, folder=a)
    victim = RiskAssessment.objects.create(
        name="ra-b",
        folder=b,
        perimeter=perimeter_b,
        risk_matrix=matrix_a,
        ebios_rm_study=study,
    )
    r = _client(analyst).post(
        "/api/risk-assessments/",
        {
            "name": "x",
            "folder": str(a.id),
            "perimeter": str(perimeter_a.id),
            "risk_matrix": str(matrix_a.id),
            "ebios_rm_study": str(study.id),
        },
        format="json",
    )
    assert r.status_code == 403
    victim.refresh_from_db()
    assert victim.ebios_rm_study_id == study.id


@pytest.mark.django_db
def test_existing_foreign_link_survives_a_full_update(app_config):
    a, _, analyst, framework, perimeter_a, _, _, _ = _cross_domain_audit()
    audit = ComplianceAssessment.objects.create(
        name="mine", framework=framework, folder=a, perimeter=perimeter_a
    )
    r = _client(analyst).patch(
        f"/api/compliance-assessments/{audit.id}/",
        {"framework": str(framework.id), "perimeter": str(perimeter_a.id)},
        format="json",
    )
    assert r.status_code == 200


@pytest.mark.django_db
def test_shared_and_own_targets_can_be_linked(app_config):
    a, _, analyst, _, _, _, _, _ = _cross_domain_audit()
    vendor = Entity.objects.create(
        name="global vendor", folder=Folder.get_root_folder()
    )
    r = _client(analyst).post(
        "/api/contracts/",
        {"name": "c", "folder": str(a.id), "provider_entity": str(vendor.id)},
        format="json",
    )
    assert r.status_code == 201

    tester = User.objects.create_user("tester@tests.com")
    UserGroup.objects.get(name="BI-UG-TST", folder=a).user_set.add(tester)
    asset = Asset.objects.create(name="srv", folder=a)
    r = _client(tester).post(
        "/api/findings/",
        {"name": "f", "folder": str(a.id), "asset": str(asset.id)},
        format="json",
    )
    assert r.status_code == 201
    assert Finding.objects.get(id=r.json()["id"]).asset_id == asset.id


def _serializer_classes():
    for app in apps.get_app_configs():
        try:
            importlib.import_module(f"{app.name}.serializers")
        except ModuleNotFoundError:
            pass
    found, stack = set(), [BaseModelSerializer]
    while stack:
        for sub in stack.pop().__subclasses__():
            if sub not in found:
                found.add(sub)
                stack.append(sub)
    return [s for s in found if getattr(getattr(s, "Meta", None), "model", None)]


# system lookups with no domain to scope them by
UNSCOPED_LINK_TARGETS = {ContentType, Permission, WebhookEventType}


@pytest.mark.django_db
def test_every_link_field_refuses_an_invisible_target(app_config):
    request = SimpleNamespace(user=User.objects.create_user("nobody@tests.com"))
    unchecked = []
    for serializer_class in _serializer_classes():
        serializer = serializer_class(context={"request": request})
        for name, field in serializer.fields.items():
            many = isinstance(field, ManyRelatedField)
            relation = field.child_relation if many else field
            if field.read_only or not isinstance(relation, RelatedField):
                continue
            queryset = relation.get_queryset()
            if queryset is None or queryset.model in UNSCOPED_LINK_TARGETS:
                continue
            # the object's own folder is gated by the add/change check
            if queryset.model is Folder and field.source == "folder":
                continue
            model = queryset.model
            target = model(pk=uuid.uuid4())
            try:
                serializer._check_m2m_visibility(
                    {field.source: [target] if many else target}
                )
            except PermissionDenied:
                continue
            unchecked.append(f"{serializer_class.__name__}.{name}")
    assert not unchecked


def test_validate_overrides_keep_the_link_check():
    skipping = [
        klass.__qualname__
        for serializer_class in _serializer_classes()
        for klass in serializer_class.__mro__[
            : serializer_class.__mro__.index(BaseModelSerializer)
        ]
        if "validate" in vars(klass)
        and "super().validate(" not in inspect.getsource(klass.validate)
    ]
    assert not skipping


@pytest.mark.django_db
def test_calendar_range_is_capped(app_config):
    a = _domain("dom-A")
    reader = User.objects.create_user("reader@tests.com")
    UserGroup.objects.get(name="BI-UG-AUD", folder=a).user_set.add(reader)
    TaskTemplate.objects.create(
        name="daily",
        folder=a,
        is_recurrent=True,
        enabled=True,
        task_date="2026-01-01",
        schedule={
            "interval": 1,
            "frequency": "DAILY",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
        },
    )
    c = _client(reader)

    r = c.get("/api/task-templates/calendar/2026-01-01/2036-01-01/")
    assert r.status_code == 400
    assert not TaskNode.objects.exists()
    assert c.get("/api/task-templates/calendar/nope/2036-01-01/").status_code == 400
    assert (
        c.get("/api/task-templates/calendar/2026-04-01/2026-03-01/").status_code == 400
    )
    assert c.get("/api/task-templates/calendar/2026-3-01/2026-4-01/").status_code == 200
