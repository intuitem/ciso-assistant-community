"""NIS2 incident deadlines and the GDPR 72h breach deadline."""

from datetime import timedelta

import pymupdf
import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from core.generators import breach_notification_context, nis2_notification_context
from core.models import Asset, Incident
from core.typst_render import render_pdf
from iam.models import Folder
from privacy.models import DataBreach, Processing, Purpose
from privacy.test_data_breach import admin_client, domain  # noqa: F401


@pytest.fixture
def folder():
    return Folder.objects.create(
        name="Regulatory follow-up", content_type=Folder.ContentType.DOMAIN
    )


@pytest.mark.django_db
def test_nis2_deadlines_only_for_significant(folder):
    incident = Incident.objects.create(name="Phishing", folder=folder)
    assert incident.nis2_deadlines() == []


@pytest.mark.django_db
def test_nis2_deadlines_clock_from_awareness(folder):
    aware = timezone.now() - timedelta(hours=30)
    incident = Incident.objects.create(
        name="Ransomware",
        folder=folder,
        reported_at=aware,
        nis2_significant=True,
        nis2_early_warning_at=aware + timedelta(hours=20),
    )
    stages = {s["stage"]: s for s in incident.nis2_deadlines()}
    assert stages["early_warning"]["due"] == aware + timedelta(hours=24)
    assert stages["early_warning"]["overdue"] is False
    assert stages["incident_notification"]["due"] == aware + timedelta(hours=72)
    assert stages["incident_notification"]["overdue"] is False
    # final report: one month after the notification due date until it is sent
    assert stages["final_report"]["due"] == aware + timedelta(hours=72) + relativedelta(
        months=1
    )

    incident.reported_at = timezone.now() - timedelta(hours=80)
    sent = timezone.now() - timedelta(hours=1)
    incident.nis2_notification_at = sent
    stages = {s["stage"]: s for s in incident.nis2_deadlines()}
    assert stages["incident_notification"]["overdue"] is False  # sent, even late
    assert stages["final_report"]["due"] == sent + relativedelta(months=1)


@pytest.mark.django_db
def test_nis2_unsent_notification_is_overdue(folder):
    incident = Incident.objects.create(
        name="DDoS",
        folder=folder,
        reported_at=timezone.now() - timedelta(hours=73),
        nis2_significant=True,
    )
    stages = {s["stage"]: s for s in incident.nis2_deadlines()}
    assert stages["early_warning"]["overdue"] is True
    assert stages["incident_notification"]["overdue"] is True
    assert stages["final_report"]["overdue"] is False


@pytest.mark.django_db
def test_breach_72h_deadline(folder):
    discovered = timezone.now() - timedelta(hours=73)
    breach = DataBreach.objects.create(
        name="Lost laptop", folder=folder, discovered_on=discovered
    )
    assert breach.authority_notification_due == discovered + timedelta(hours=72)
    assert breach.authority_notification_overdue is True

    breach.authority_notified_on = timezone.now()
    assert breach.authority_notification_overdue is False

    breach.authority_notified_on = None
    breach.risk_level = "privacy_no_risk"
    assert breach.authority_notification_due is None
    assert breach.authority_notification_overdue is False


@pytest.mark.django_db
def test_follow_up_over_the_api(admin_client, domain):  # noqa: F811
    incident = Incident.objects.create(
        name="Ransomware",
        folder=domain,
        reported_at=timezone.now() - timedelta(hours=2),
        nis2_significant=True,
        nis2_cross_border_impact="uncertain",
    )
    DataBreach.objects.create(
        name="HR files exfiltrated",
        folder=domain,
        incident=incident,
        discovered_on=timezone.now() - timedelta(hours=2),
    )

    res = admin_client.get(f"/api/incidents/{incident.id}/")
    assert res.status_code == 200
    stages = [s["stage"] for s in res.json()["nis2_deadlines"]]
    assert stages == ["early_warning", "incident_notification", "final_report"]
    assert res.json()["nis2_cross_border_impact"] == "uncertain"

    choices = admin_client.get("/api/incidents/nis2_cross_border_impact/").json()
    assert set(choices) == {"yes", "no", "uncertain"}

    res = admin_client.get(f"/api/privacy/data-breaches/?incident={incident.id}")
    (breach,) = res.json()["results"]
    assert breach["authority_notification_due"]
    assert breach["authority_notification_overdue"] is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "lang,nis2_title,apd_title",
    [
        ("en", "NIS2 notification worksheet", "Personal data breach notification"),
        ("fr", "Fiche de notification NIS2", "Fiche de notification de violation"),
        ("nl", "Werkblad NIS2-melding", "Werkblad melding van een datalek"),
    ],
)
def test_notification_worksheets_render(folder, lang, nis2_title, apd_title):
    incident = Incident.objects.create(
        name="Ransomware",
        folder=folder,
        nis2_significant=True,
        nis2_malicious_intent="yes",
        root_cause="Unpatched VPN appliance",
    )
    breach = DataBreach.objects.create(
        name="HR files exfiltrated",
        folder=folder,
        incident=incident,
        discovered_on=timezone.now() - timedelta(hours=80),
    )
    nis2 = pymupdf.open(
        stream=render_pdf(
            "nis2_notification.typ",
            nis2_notification_context(incident, [breach], lang),
        )
    )
    text = "".join(p.get_text() for p in nis2)
    assert nis2_title in text
    assert "Unpatched VPN appliance" in text
    assert "HR files exfiltrated" in text

    apd = pymupdf.open(
        stream=render_pdf(
            "breach_notification.typ", breach_notification_context(breach, lang)
        )
    )
    text = "".join(p.get_text() for p in apd)
    assert apd_title in text
    assert "Ransomware" in text  # linked incident


@pytest.mark.django_db
def test_notification_worksheet_endpoints(admin_client, domain):  # noqa: F811
    incident = Incident.objects.create(name="DDoS", folder=domain)
    breach = DataBreach.objects.create(
        name="Leak", folder=domain, discovered_on=timezone.now()
    )
    res = admin_client.get(f"/api/incidents/{incident.id}/nis2_notification/")
    assert res.status_code == 200
    assert res["Content-Type"] == "application/pdf"
    res = admin_client.get(f"/api/privacy/data-breaches/{breach.id}/notification/")
    assert res.status_code == 200
    assert res["Content-Type"] == "application/pdf"


@pytest.mark.django_db
def test_overdue_72h_notification_stays_the_next_stage(folder):
    """Once 72h pass unrecorded, the upcoming final report must not take over."""
    incident = Incident.objects.create(
        name="Wiper",
        folder=folder,
        nis2_significant=True,
        reported_at=timezone.now() - timedelta(hours=80),
        nis2_early_warning_at=timezone.now() - timedelta(hours=70),
    )
    assert incident.nis2_next_stage()["stage"] == "incident_notification"
    incident.nis2_notification_at = timezone.now()
    assert incident.nis2_next_stage()["stage"] == "final_report"


@pytest.mark.django_db
def test_nis2_dates_are_validated(admin_client, domain):  # noqa: F811
    # reported_at defaults to creation: only an explicit clear leaves it empty
    incident = Incident.objects.create(name="DDoS", folder=domain, reported_at=None)
    url = f"/api/incidents/{incident.id}/"
    res = admin_client.patch(url, {"nis2_significant": True}, format="json")
    assert res.status_code == 400 and "reported_at" in res.json()

    reported = timezone.now() - timedelta(hours=10)
    incident.reported_at = reported
    incident.save()
    for sent in (timezone.now() + timedelta(hours=1), reported - timedelta(hours=1)):
        res = admin_client.patch(
            url, {"nis2_notification_at": sent.isoformat()}, format="json"
        )
        assert res.status_code == 400 and "nis2_notification_at" in res.json()
    res = admin_client.patch(
        url,
        {"nis2_significant": True, "nis2_notification_at": timezone.now().isoformat()},
        format="json",
    )
    assert res.status_code == 200


@pytest.mark.django_db
def test_worksheets_keep_what_the_requester_cannot_see_out(folder):
    incident = Incident.objects.create(
        name="Ransomware", folder=folder, status="closed"
    )
    secret = Asset.objects.create(name="Secret vault", folder=folder)
    incident.assets.set([secret])
    processing = Processing.objects.create(name="Payroll", folder=folder)
    Purpose.objects.create(name="Pay salaries", processing=processing)
    Purpose.objects.create(processing=processing, legal_basis="privacy_contract")
    breach = DataBreach.objects.create(
        name="Leak", folder=folder, incident=incident, discovered_on=timezone.now()
    )
    breach.affected_processings.set([processing])

    ctx = breach_notification_context(breach)["breach"]
    # an unnamed purpose shows its legal basis instead of breaking the sort
    assert ctx["purposes"] == ["Pay salaries", "privacy_contract"]
    assert ctx["resolved"] is False  # the breach is open, whatever its incident

    hidden = {secret.id, processing.id, incident.id}
    readable = lambda obj: obj.id not in hidden  # noqa: E731
    ctx = breach_notification_context(breach, readable=readable)["breach"]
    assert (ctx["processings"], ctx["purposes"], ctx["incident"]) == ([], [], "")
    nis2 = nis2_notification_context(incident, [], readable=readable)
    assert nis2["incident"]["assets"] == []
