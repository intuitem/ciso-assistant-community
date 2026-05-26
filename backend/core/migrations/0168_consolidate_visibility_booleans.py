from django.db import migrations, models


EVERYONE_EDIT = {"auditor": "edit", "respondent": "edit"}
AUDITOR_ONLY = {"auditor": "edit", "respondent": "hidden"}
HIDDEN = {"auditor": "hidden", "respondent": "hidden"}

# Translate legacy single-string field_visibility values (introduced in
# migration 0157) to the new per-role pair shape.
LEGACY_STRING_TO_PAIR = {
    "everyone": EVERYONE_EDIT,
    "auditor": AUDITOR_ONLY,
    "hidden": HIDDEN,
}


def _normalize(value):
    """Coerce a stored entry to a per-role pair, or return None if uninterpretable."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        pair = LEGACY_STRING_TO_PAIR.get(value)
        return dict(pair) if pair else None
    return None


def normalize_framework_field_visibility(apps, schema_editor):
    """Translate any legacy string values on Framework.field_visibility to pairs.

    Frameworks seed new CAs with their `field_visibility`, so a leftover
    single-string entry (legacy 0157 format) would silently be treated as
    `EVERYONE_EDIT` by the new resolver.
    """
    Framework = apps.get_model("core", "Framework")
    batch = []
    fields = ["field_visibility"]
    for fw in Framework.objects.all().iterator():
        raw = fw.field_visibility or {}
        if not raw:
            continue
        normalized = {}
        for key, value in raw.items():
            norm = _normalize(value)
            if norm is not None:
                normalized[key] = norm
        if normalized != raw:
            fw.field_visibility = normalized
            batch.append(fw)
        if len(batch) >= 1000:
            Framework.objects.bulk_update(batch, fields)
            batch = []
    if batch:
        Framework.objects.bulk_update(batch, fields)


def booleans_to_field_visibility(apps, schema_editor):
    """Translate legacy boolean toggles into per-role field_visibility entries.

    Storage shape: {field_name: {role: 'edit' | 'read' | 'hidden'}}.
    Any pre-existing single-string entry (legacy 0157 format) is normalized to
    the new pair shape. When a legacy boolean toggle is off (e.g. scoring_enabled
    is False), the corresponding fields are forced to HIDDEN — the boolean was
    the canonical control, so a stale "everyone" override on field_visibility
    would have been a no-op anyway.
    """
    CA = apps.get_model("core", "ComplianceAssessment")
    RA = apps.get_model("core", "RequirementAssessment")
    batch = []
    fields = ["field_visibility"]
    for ca in CA.objects.all().iterator():
        raw = ca.field_visibility or {}
        before = dict(raw)

        # Normalize any legacy string entries to per-role pairs; drop unknowns.
        fv = {}
        for key, value in raw.items():
            norm = _normalize(value)
            if norm is not None:
                fv[key] = norm

        # Legacy booleans were the canonical control. Off → force HIDDEN.
        # On → preserve any explicit override; otherwise default to AUDITOR_ONLY,
        # which matches the historical pre-PR default (`'auditor'`) — i.e. the
        # field was visible to auditors and hidden from respondents.
        if not ca.scoring_enabled:
            fv["score"] = dict(HIDDEN)
            fv["is_scored"] = dict(HIDDEN)
        else:
            fv.setdefault("score", dict(AUDITOR_ONLY))
            fv.setdefault("is_scored", dict(AUDITOR_ONLY))

        if not ca.show_documentation_score:
            fv["documentation_score"] = dict(HIDDEN)
        else:
            fv.setdefault("documentation_score", dict(AUDITOR_ONLY))

        if not ca.extended_result_enabled:
            fv["extended_result"] = dict(HIDDEN)
        else:
            fv.setdefault("extended_result", dict(AUDITOR_ONLY))

        if not ca.progress_status_enabled:
            fv["status"] = dict(HIDDEN)
        else:
            fv.setdefault("status", dict(AUDITOR_ONLY))

        # respondent_alignment has no legacy boolean. Keep visible only on CAs
        # that actively use it (any RA with a non-null alignment value).
        alignment_in_use = RA.objects.filter(
            compliance_assessment_id=ca.id,
            respondent_alignment__isnull=False,
        ).exists()
        fv.setdefault(
            "respondent_alignment",
            dict(EVERYONE_EDIT) if alignment_in_use else dict(HIDDEN),
        )

        if fv != before:
            ca.field_visibility = fv
            batch.append(ca)
        if len(batch) >= 1000:
            CA.objects.bulk_update(batch, fields)
            batch = []
    if batch:
        CA.objects.bulk_update(batch, fields)


def reverse_noop(apps, schema_editor):
    # Reverse migration is intentionally a no-op: the boolean columns are
    # re-added by the schema reverse, but their values cannot be recovered
    # losslessly from the per-role field_visibility map.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0167_backfill_respondent_alignment"),
    ]

    operations = [
        # Update help_text on field_visibility to reflect the new per-role model.
        migrations.AlterField(
            model_name="complianceassessment",
            name="field_visibility",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Per-field visibility map: "
                    "{field_name: {role: 'edit' | 'read' | 'hidden'}}. "
                    "Missing keys cascade through core.utils.DEFAULT_VISIBILITY "
                    "(e.g. score/documentation_score default to hidden, "
                    "status/extended_result to auditor-only) and finally to 'edit' "
                    "for every role for unknown fields."
                ),
                verbose_name="Field visibility",
            ),
        ),
        migrations.AlterField(
            model_name="framework",
            name="field_visibility",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Per-field visibility template seeded into new CAs: "
                    "{field_name: {role: 'edit' | 'read' | 'hidden'}}."
                ),
                verbose_name="Field visibility",
            ),
        ),
        migrations.RunPython(normalize_framework_field_visibility, reverse_noop),
        migrations.RunPython(booleans_to_field_visibility, reverse_noop),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="scoring_enabled",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="show_documentation_score",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="extended_result_enabled",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="progress_status_enabled",
        ),
    ]
