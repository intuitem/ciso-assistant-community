from datetime import date
from string import Template
from types import SimpleNamespace

import pytest

from core.email_utils import (
    format_email_date,
    format_task_node_list,
    get_email_preferences,
    load_email_template,
    localize_assignment_decision,
    localize_day_unit,
)
from global_settings.models import GlobalSettings
from iam.models import User


@pytest.mark.parametrize(
    ("days", "locale", "expected"),
    [
        (1, "de", "Tag"),
        (7, "de-DE", "Tagen"),
        (1, "en", "day"),
        (30, "en-US", "days"),
        (1, "fr", "jour"),
        (7, "fr-FR", "jours"),
    ],
)
def test_localize_day_unit(days, locale, expected):
    assert localize_day_unit(days, locale) == expected


@pytest.mark.parametrize(
    ("decision", "locale", "expected"),
    [
        ("closed", "de", "geschlossen"),
        ("reopened", "de-DE", "erneut geöffnet"),
        ("changes_requested", "de", "zur Überarbeitung zurückgegeben"),
        ("closed", "en", "closed"),
        ("reopened", "en-US", "reopened"),
        ("changes_requested", "en", "returned with changes requested"),
        ("closed", "fr", "clôturée"),
        ("reopened", "fr-FR", "rouverte"),
        (
            "changes_requested",
            "fr",
            "renvoyée avec des modifications demandées",
        ),
    ],
)
def test_localize_assignment_decision(decision, locale, expected):
    assert localize_assignment_decision(decision, locale) == expected


@pytest.mark.parametrize(
    ("template_name", "days_key", "unit_key"),
    [
        ("applied_control_expiring_soon", "days_remaining", "days_remaining_unit"),
        (
            "compliance_assessment_due_soon",
            "days_remaining",
            "days_remaining_unit",
        ),
        ("evidence_expiring_soon", "days_remaining", "days_remaining_unit"),
        ("expired_evidences", "expired_since", "expired_since_unit"),
        (
            "expired_security_exceptions",
            "expired_since",
            "expired_since_unit",
        ),
        (
            "security_exception_expiring_soon",
            "days_remaining",
            "days_remaining_unit",
        ),
        ("task_node_due_soon", "days_remaining", "days_remaining_unit"),
        ("validation_deadline", "days", "days_unit"),
    ],
)
def test_german_day_subjects_use_singular_day(template_name, days_key, unit_key):
    template = load_email_template(template_name, "de", builtin_only=True)

    subject = Template(template["subject"]).substitute(
        {days_key: 1, unit_key: localize_day_unit(1, "de")}
    )

    assert "1 Tag" in subject


def test_german_assignment_reviewed_subject_localizes_decision():
    template = load_email_template("assignment_reviewed", "de", builtin_only=True)

    subject = Template(template["subject"]).substitute(
        assessment_name="ISO 27001",
        decision=localize_assignment_decision("changes_requested", "de"),
    )

    assert subject == (
        "CISO Assistant: Ihre Aufgabe für 'ISO 27001' wurde zur Überarbeitung "
        "zurückgegeben"
    )


@pytest.mark.parametrize(
    ("locale", "expected_due", "expected_status"),
    [
        ("de", "Fällig: 30.09.2026", "Status: Ausstehend"),
        ("en", "Due: 09/30/2026", "Status: Pending"),
        ("fr", "Échéance: 30/09/2026", "Statut: En attente"),
    ],
)
def test_task_list_localizes_dynamic_details(locale, expected_due, expected_status):
    task_template = SimpleNamespace(
        id="template-id",
        name="Review access",
        is_recurrent=False,
    )
    task_node = SimpleNamespace(
        id="node-id",
        task_template=task_template,
        due_date=date(2026, 9, 30),
        status="pending",
    )

    task_list = format_task_node_list([task_node], locale=locale)

    assert expected_due in task_list
    assert expected_status in task_list


@pytest.mark.parametrize(
    ("preference", "expected"),
    [
        ("iso", "2026-09-30"),
        ("ddmmyyyy", "30/09/2026"),
        ("mmddyyyy", "09/30/2026"),
        ("long_dmy", "30 September 2026"),
        ("long_mdy", "September 30, 2026"),
    ],
)
def test_email_date_honors_recipient_preference(preference, expected):
    assert format_email_date(date(2026, 9, 30), "de", preference) == expected


def test_task_list_keeps_recipient_locale_when_labels_fall_back():
    task_template = SimpleNamespace(
        id="template-id",
        name="Review access",
        is_recurrent=False,
    )
    task_node = SimpleNamespace(
        id="node-id",
        task_template=task_template,
        due_date=date(2026, 9, 30),
        status="pending",
    )

    task_list = format_task_node_list([task_node], locale="es", date_format="long_dmy")

    assert "Due: 30 septiembre 2026" in task_list
    assert "Status: Pending" in task_list


def test_email_date_falls_back_to_english_for_unknown_locale():
    assert (
        format_email_date(date(2026, 9, 30), "unknown", "long_dmy")
        == "30 September 2026"
    )


@pytest.mark.django_db
def test_email_preferences_use_user_values_before_instance_defaults():
    GlobalSettings.objects.update_or_create(
        name="general",
        defaults={"value": {"default_language": "en", "default_date_format": "iso"}},
    )
    user = User.objects.create_user(email="localized-email@tests.com")
    user.preferences = {"lang": "de", "date_format": "long_dmy"}
    user.save(update_fields=["preferences"])

    assert get_email_preferences(user.email) == ("de", "long_dmy")


@pytest.mark.django_db
def test_email_preferences_use_instance_defaults_for_missing_user():
    GlobalSettings.objects.update_or_create(
        name="general",
        defaults={
            "value": {"default_language": "fr", "default_date_format": "mmddyyyy"}
        },
    )

    assert get_email_preferences("external@tests.com") == ("fr", "mmddyyyy")


def test_email_preferences_fall_back_when_settings_are_unavailable(monkeypatch):
    no_result = SimpleNamespace(first=lambda: None)
    monkeypatch.setattr(User.objects, "filter", lambda **_: no_result)
    monkeypatch.setattr(GlobalSettings.objects, "filter", lambda **_: no_result)

    assert get_email_preferences("external@tests.com") == ("en", "auto")


@pytest.mark.django_db
def test_email_preferences_fall_back_for_invalid_instance_defaults():
    GlobalSettings.objects.update_or_create(
        name="general",
        defaults={
            "value": {
                "default_language": "invalid",
                "default_date_format": ["invalid"],
            }
        },
    )

    assert get_email_preferences("external@tests.com") == ("en", "auto")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("sender_name", "sender_kwargs", "expected_subject"),
    [
        (
            "send_task_node_due_soon_notification",
            {"days": 7},
            "Tâche à échéance",
        ),
        ("send_task_node_overdue_notification", {}, "tâche(s) en retard"),
    ],
)
def test_task_email_senders_forward_recipient_preferences(
    monkeypatch, sender_name, sender_kwargs, expected_subject
):
    from core import tasks as core_tasks

    GlobalSettings.objects.update_or_create(
        name="general",
        defaults={"value": {"default_language": "en", "default_date_format": "iso"}},
    )
    user = User.objects.create_user(email=f"{sender_name}@tests.com")
    user.preferences = {"lang": "fr", "date_format": "long_dmy"}
    user.save(update_fields=["preferences"])

    task_template = SimpleNamespace(
        id="template-id",
        name="Review access",
        description="",
        is_recurrent=False,
    )
    task_node = SimpleNamespace(
        id="node-id",
        task_template=task_template,
        due_date=date(2026, 9, 30),
        status="pending",
    )
    sent_messages = []

    monkeypatch.setattr(core_tasks, "check_email_configuration", lambda *_: True)
    monkeypatch.setattr(
        core_tasks,
        "send_notification_email",
        lambda subject, body, recipient, html_body=None: sent_messages.append(
            (subject, body, recipient, html_body)
        ),
    )

    sender = getattr(core_tasks, sender_name)
    sender.call_local(user.email, [task_node], **sender_kwargs)

    assert len(sent_messages) == 1
    subject, body, recipient, html_body = sent_messages[0]
    assert expected_subject in subject
    assert recipient == user.email
    assert "Échéance: 30 septembre 2026" in body
    assert "Statut: En attente" in body
    assert "Échéance: 30 septembre 2026" in html_body
