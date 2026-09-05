"""Seed a fully-populated entity assessment for exercising the PDF export.

Everything lands under a single domain named by DOMAIN_NAME, so it can be removed
by deleting that folder. Re-running deletes and recreates the domain.

    ../.venv/bin/python seed_tprm_demo.py
"""

import os
from datetime import date, timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from django.contrib.contenttypes.models import ContentType  # noqa: E402

from core.models import (  # noqa: E402
    AppliedControl,
    Commitment,
    Evidence,
    Framework,
    Perimeter,
    Question,
    RequirementAssessment,
    TaskTemplate,
)
from core.utils import build_answers_dict, visible_questions  # noqa: E402
from iam.models import Folder, User  # noqa: E402
from tprm.models import Entity, EntityAssessment, Representative  # noqa: E402
from tprm.services import create_enclave_audit  # noqa: E402

DOMAIN_NAME = "Demo — Northwind (TPRM export)"
FRAMEWORK_URN = "urn:intuitem:risk:framework:enisa-sme-cra-maturity"
TODAY = date.today()


def reset_domain():
    Folder.objects.filter(name=DOMAIN_NAME).delete()
    return Folder.objects.create(
        name=DOMAIN_NAME,
        description="Seeded demo data for the audit posture / attestation PDF exports.",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


def make_entity(folder):
    entity = Entity.objects.create(
        name="Northwind Logistics BV",
        ref_id="SUP-0042",
        description="Cross-border freight forwarding and customs brokerage.",
        folder=folder,
        mission="Move regulated goods across the EU under bonded transit.",
        address=(
            "Northwind Logistics BV\n"
            "Havenstraat 118, Unit 4\n"
            "3011 XT Rotterdam\n"
            "The Netherlands"
        ),
        country="NLD",
        currency="EUR",
        legal_identifiers={
            "LEI": "724500VKKSH9QOLTFR24",
            "EUID": "NLNHR.24681012",
            "VAT": "NL823456789B01",
            "DUNS": "40-123-4567",
        },
        reference_link="https://example.com/suppliers/northwind",
        is_active=True,
    )
    for first, last, role, email in [
        (
            "Marieke",
            "de Vries",
            "Chief Information Security Officer",
            "m.devries@northwind.example",
        ),
        ("Tomas", "Bakker", "Head of Operations", "t.bakker@northwind.example"),
    ]:
        # `EntityAssessment.representatives` is M2M to User, and the service fills it
        # from third-party users linked back through Representative.user.
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"first_name": first, "last_name": last, "is_third_party": True},
        )
        Representative.objects.update_or_create(
            email=email,
            defaults={
                "entity": entity,
                "first_name": first,
                "last_name": last,
                "role": role,
                "phone": "+31 10 555 0140",
                "description": "Signatory for third-party assurance.",
                "user": user,
            },
        )
    return entity


def answer_question(ra, question):
    """Give a plausible answer for each question type."""
    # `create_requirement_assessments` already lays down a blank answer per question.
    answer, _ = ra.answers.get_or_create(
        question=question, defaults={"folder": ra.folder}
    )
    if question.type == Question.Type.BOOLEAN:
        answer.value = True
    elif question.type == Question.Type.NUMBER:
        answer.value = 3
    elif question.type == Question.Type.DATE:
        answer.value = (TODAY - timedelta(days=45)).isoformat()
    elif question.type in (Question.Type.UNIQUE_CHOICE, Question.Type.MULTIPLE_CHOICE):
        choices = list(question.choices.all())
        if choices:
            picked = choices[
                : 2 if question.type == Question.Type.MULTIPLE_CHOICE else 1
            ]
            answer.selected_choices.set(picked)
    else:
        answer.value = (
            "Documented in the ISMS and reviewed at the last management review."
        )
    answer.save()


def fill_assessments(audit):
    results = ["compliant", "partially_compliant", "non_compliant", "not_applicable"]
    ras = [
        ra
        for ra in RequirementAssessment.objects.filter(
            compliance_assessment=audit
        ).select_related("requirement")
        if ra.requirement.assessable
    ]
    for i, ra in enumerate(ras):
        ra.result = results[i % len(results)]
        ra.status = "done" if i % 5 else "in_progress"
        ra.observation = (
            f"Evidence sampled for Q2-Q3; control owner interviewed on "
            f"{(TODAY - timedelta(days=20 + i)).isoformat()}."
        )
        ra.is_scored = True
        ra.score = [4, 3, 1, 0][i % 4]
        ra.save()

        for question in ra.requirement.questions.all():
            answer_question(ra, question)
    return ras


def commit(obj, state, eta=None, notes=None):
    Commitment.objects.create(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.id,
        state=state,
        committed_eta=eta,
        notes=notes,
        folder=obj.folder,
        is_current=True,
    )


def make_undertakings(folder, ras):
    controls = [
        ("Deploy phishing-resistant MFA on remote access", "committed", 75, None),
        ("Encrypt customs data at rest (AES-256)", "committed", 150, None),
        ("Quarterly privileged access review", "in_negotiation", None, None),
        (
            "Independent penetration test of the customer portal",
            "declined",
            None,
            "Out of scope for the current contract term; revisit at renewal.",
        ),
        ("Formalise supplier incident notification within 24h", "committed", 30, None),
    ]
    for i, (name, state, days, notes) in enumerate(controls):
        eta = TODAY + timedelta(days=days) if days else None
        ac = AppliedControl.objects.create(
            name=name,
            description="Agreed remediation arising from the assessment.",
            folder=folder,
            eta=eta,
        )
        ac.requirement_assessments.set([ras[i % len(ras)]])
        commit(ac, state, eta, notes)

    tasks = [
        ("Annual security awareness training", 60, "committed"),
        ("Submit updated business continuity plan", 20, "committed"),
        ("Provide SOC 2 Type II report", 90, "in_negotiation"),
    ]
    for i, (name, days, state) in enumerate(tasks):
        due = TODAY + timedelta(days=days)
        tt = TaskTemplate.objects.create(
            name=name,
            description="Deliverable owed by the supplier.",
            folder=folder,
            task_date=due,
        )
        # Spread across several requirements so the per-requirement block shows up.
        tt.requirement_assessments.set(
            [ras[(i * 3 + 1) % len(ras)], ras[(i * 3 + 6) % len(ras)]]
        )
        commit(tt, state, due if state == "committed" else None)


def make_evidences(folder, ras):
    names = [
        "ISO 27001 certificate (2026-2029)",
        "Penetration test summary — Q2 2026",
        "Business continuity plan v4.2",
        "Data processing agreement (signed)",
        "Access review extract — Q3 2026",
        "Vulnerability scan report — August 2026",
        "Supplier incident response runbook",
    ]
    for i, name in enumerate(names):
        ev = Evidence.objects.create(
            name=name,
            description="Provided by the supplier during the assessment.",
            folder=folder,
        )
        # Every third requirement carries one, and a couple carry two.
        ras[(i * 3) % len(ras)].evidences.add(ev)
        if i % 3 == 0:
            ras[(i * 3 + 1) % len(ras)].evidences.add(ev)


def main():
    framework = Framework.objects.filter(urn=FRAMEWORK_URN).first()
    if framework is None:
        raise SystemExit(f"Framework not loaded: {FRAMEWORK_URN}")

    folder = reset_domain()
    Perimeter.objects.create(name="Supplier assurance 2026", folder=folder)
    entity = make_entity(folder)

    ea = EntityAssessment.objects.create(
        name="Northwind Logistics — annual assurance 2026",
        description="Annual third-party assessment ahead of contract renewal.",
        folder=folder,
        entity=entity,
        version="1.0",
        status="in_progress",
        criticality=3,
        conclusion=EntityAssessment.Conclusion.WARNING,
        eta=TODAY + timedelta(days=14),
        due_date=TODAY + timedelta(days=45),
        expiry_date=TODAY + timedelta(days=365),
        observation="Two blocking findings pending remediation commitments.",
        reference_link="https://example.com/assurance/northwind-2026",
    )
    audit = create_enclave_audit(ea, framework)
    ras = fill_assessments(audit)
    make_undertakings(folder, ras)
    make_evidences(folder, ras)

    answered = sum(
        len(
            visible_questions(
                ra.requirement.get_questions_translated,
                build_answers_dict(ra.answers.all()),
            )
        )
        for ra in ras
    )
    print(f"domain            : {folder.name} ({folder.id})")
    print(f"entity            : {entity.name}")
    print(f"entity assessment : {ea.name} ({ea.id})")
    print(f"audit             : {audit.name} ({audit.id})")
    print(f"requirements filled: {len(ras)}   visible questions answered: {answered}")
    print(f"commitments        : {Commitment.objects.filter(folder=folder).count()}")
    print(f"export             : /api/compliance-assessments/{audit.id}/posture-pdf/")


if __name__ == "__main__":
    main()
