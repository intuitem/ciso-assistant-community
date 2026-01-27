# Generated manually for splitting legal basis choices

from django.db import migrations, models


def migrate_legal_basis_data(apps, schema_editor):
    """
    Migrate data from old mixed legal_basis choices to new separated fields.

    For Purpose:
    - Art 9 condition values move to article_9_condition field
    - Art 6 values stay in legal_basis
    - Combined/other values are mapped appropriately

    For DataTransfer:
    - Old transfer-related legal_basis values map to new transfer_mechanism field
    """
    Purpose = apps.get_model("privacy", "Purpose")
    DataTransfer = apps.get_model("privacy", "DataTransfer")

    # Art 9(2) condition values that should be moved to article_9_condition
    art9_values = {
        "privacy_explicit_consent",
        "privacy_employment_social_security",
        "privacy_vital_interests_incapacity",
        "privacy_nonprofit_organization",
        "privacy_public_data",
        "privacy_legal_claims",
        "privacy_substantial_public_interest",
        "privacy_preventive_medicine",
        "privacy_public_health",
        "privacy_archiving_research",
    }

    # Combined values that need special handling for Purpose
    combined_mappings = {
        "privacy_consent_and_contract": (
            "privacy_consent",
            None,
        ),  # Keep consent as primary
        "privacy_contract_and_legitimate_interests": ("privacy_contract", None),
        "privacy_child_consent": (
            "privacy_consent",
            None,
        ),  # Child consent is still consent
        "privacy_not_applicable": ("privacy_consent", None),  # Default to consent
        "privacy_other": ("privacy_consent", None),  # Default to consent
    }

    # Transfer mechanism mappings for DataTransfer
    transfer_mappings = {
        "privacy_data_transfer_adequacy": "privacy_adequacy_decision",
        "privacy_data_transfer_safeguards": "privacy_appropriate_safeguards",
        "privacy_data_transfer_binding_rules": "privacy_binding_corporate_rules",
        "privacy_data_transfer_derogation": "privacy_derogation",
    }

    # Migrate Purpose records
    for purpose in Purpose.objects.all():
        old_value = purpose.legal_basis

        if old_value in art9_values:
            # Move Art 9 value to article_9_condition, set default legal_basis
            purpose.article_9_condition = old_value
            purpose.legal_basis = "privacy_consent"
            purpose.save()
        elif old_value in combined_mappings:
            # Handle combined/special values
            new_legal_basis, new_art9 = combined_mappings[old_value]
            purpose.legal_basis = new_legal_basis
            purpose.article_9_condition = new_art9
            purpose.save()
        elif old_value in transfer_mappings:
            # Someone incorrectly used a transfer mechanism on Purpose - fix it
            purpose.legal_basis = "privacy_consent"
            purpose.save()
        # Art 6 values stay as-is (no change needed)

    # Migrate DataTransfer records
    for transfer in DataTransfer.objects.all():
        old_value = transfer.legal_basis

        if old_value in transfer_mappings:
            transfer.transfer_mechanism = transfer_mappings[old_value]
            transfer.save()
        elif old_value:
            # Non-transfer value was used - clear it (invalid for transfers)
            transfer.transfer_mechanism = ""
            transfer.save()


class Migration(migrations.Migration):
    dependencies = [
        ("privacy", "0017_processing_perimeters"),
    ]

    operations = [
        # Step 1: Add article_9_condition field to Purpose
        migrations.AddField(
            model_name="purpose",
            name="article_9_condition",
            field=models.CharField(
                blank=True,
                choices=[
                    (
                        "privacy_explicit_consent",
                        "Explicit Consent for Special Categories",
                    ),
                    (
                        "privacy_employment_social_security",
                        "Employment and Social Security Law",
                    ),
                    (
                        "privacy_vital_interests_incapacity",
                        "Vital Interests (Subject Physically/Legally Incapable)",
                    ),
                    (
                        "privacy_nonprofit_organization",
                        "Processing by Nonprofit Organization",
                    ),
                    (
                        "privacy_public_data",
                        "Data Manifestly Made Public by the Data Subject",
                    ),
                    (
                        "privacy_legal_claims",
                        "Establishment, Exercise or Defense of Legal Claims",
                    ),
                    (
                        "privacy_substantial_public_interest",
                        "Substantial Public Interest",
                    ),
                    (
                        "privacy_preventive_medicine",
                        "Preventive or Occupational Medicine",
                    ),
                    ("privacy_public_health", "Public Health"),
                    (
                        "privacy_archiving_research",
                        "Archiving, Research or Statistical Purposes",
                    ),
                ],
                max_length=255,
                null=True,
            ),
        ),
        # Step 2: Add transfer_mechanism field to DataTransfer
        migrations.AddField(
            model_name="datatransfer",
            name="transfer_mechanism",
            field=models.CharField(
                blank=True,
                choices=[
                    ("privacy_adequacy_decision", "Adequacy Decision (Art. 45)"),
                    (
                        "privacy_appropriate_safeguards",
                        "Appropriate Safeguards (Art. 46)",
                    ),
                    (
                        "privacy_binding_corporate_rules",
                        "Binding Corporate Rules (Art. 47)",
                    ),
                    (
                        "privacy_derogation",
                        "Derogation for Specific Situations (Art. 49)",
                    ),
                ],
                max_length=255,
            ),
        ),
        # Step 3: Run data migration
        migrations.RunPython(migrate_legal_basis_data, migrations.RunPython.noop),
        # Step 4: Update Purpose.legal_basis choices
        migrations.AlterField(
            model_name="purpose",
            name="legal_basis",
            field=models.CharField(
                choices=[
                    ("privacy_consent", "Consent"),
                    ("privacy_contract", "Performance of a Contract"),
                    ("privacy_legal_obligation", "Compliance with a Legal Obligation"),
                    ("privacy_vital_interests", "Protection of Vital Interests"),
                    (
                        "privacy_public_interest",
                        "Performance of a Task in the Public Interest",
                    ),
                    ("privacy_legitimate_interests", "Legitimate Interests"),
                ],
                default="privacy_consent",
                max_length=255,
            ),
        ),
        # Step 5: Remove legal_basis from DataTransfer
        migrations.RemoveField(
            model_name="datatransfer",
            name="legal_basis",
        ),
    ]
