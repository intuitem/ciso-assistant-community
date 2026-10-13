from string import Template

import pytest

from core.email_utils import (
    load_email_template,
    localize_assignment_decision,
    localize_day_unit,
)


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
