"""What a form about a processing can show from its record (see core.quick_form_facts)."""

from core.quick_form_facts import Fact, register_fact

PROCESSING = "privacy.Processing"

for key, label, relation, columns in (
    (
        "purposes",
        "purposes",
        "purposes",
        ("name", "legal_basis", "article_9_condition"),
    ),
    (
        "personal_data",
        "personalData",
        "personal_data",
        ("name", "category", "retention", "deletion_policy", "is_sensitive", "assets"),
    ),
    ("data_subjects", "dataSubjects", "data_subjects", ("name", "category")),
    ("recipients", "dataRecipients", "data_recipients", ("name", "category")),
    (
        "contractors",
        "dataContractors",
        "contractors_involved",
        ("name", "entity", "relationship_type", "country"),
    ),
    (
        "transfers",
        "dataTransfers",
        "data_transfers",
        ("name", "entity", "country", "transfer_mechanism", "guarantees"),
    ),
    (
        "controls",
        "associatedControls",
        "associated_controls",
        ("name", "status", "eta"),
    ),
):
    register_fact(Fact(f"processing.{key}", PROCESSING, label, relation, columns))
