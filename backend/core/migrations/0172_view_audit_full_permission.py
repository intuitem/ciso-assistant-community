"""Introduce the ``view_audit_full`` permission and backfill existing roles.

The auditor-vs-respondent view is now permission-based (default-deny): a principal
sees the scoped/stripped respondent view unless it holds ``view_audit_full``.

This migration does two things:
  1. Declares the permission on ``ComplianceAssessment`` (Meta options).
  2. Backfills it onto every existing role EXCEPT the two respondent roles
     (AUDITEE, THIRD_PARTY_RESPONDENT), so current behaviour is preserved —
     only those two were ever scoped. Builtin auditor roles are also re-synced
     by ``startup`` on each migrate; this additionally covers custom (org-defined)
     roles so they keep the full auditor view they had before.

The permission row is created explicitly in the data step: custom permissions
declared via ``Meta.permissions`` are materialised by Django's ``create_permissions``
post_migrate signal, which has not run yet while this migration executes.
"""

from django.db import migrations

RESPONDENT_ROLE_CODENAMES = ("BI-RL-TPR", "BI-RL-ADE")  # third-party, auditee
PERM_CODENAME = "view_audit_full"
PERM_NAME = "Can view the full auditor view of an audit (all rows and fields)"


def grant_view_audit_full(apps, schema_editor):
    Role = apps.get_model("iam", "Role")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    ct, _ = ContentType.objects.get_or_create(
        app_label="core", model="complianceassessment"
    )
    perm, _ = Permission.objects.get_or_create(
        codename=PERM_CODENAME,
        content_type=ct,
        defaults={"name": PERM_NAME},
    )

    for role in Role.objects.exclude(name__in=RESPONDENT_ROLE_CODENAMES):
        role.permissions.add(perm)


def noop(apps, schema_editor):
    # Irreversible-by-design: we don't strip the grant on downgrade.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0171_requirementnode_score_and_target_score"),
        ("iam", "0021_fix_auditee_iam_groups"),
        ("auth", "0001_initial"),
        ("contenttypes", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="complianceassessment",
            options={
                "permissions": [(PERM_CODENAME, PERM_NAME)],
                "verbose_name": "Compliance assessment",
                "verbose_name_plural": "Compliance assessments",
            },
        ),
        migrations.RunPython(grant_view_audit_full, noop),
    ]
