#!/usr/bin/env python3
"""Build the DPIA quick form library (backend/library/libraries/quick-form-dpia.yaml).

The CNIL PIA structure: context, core principles, three feared events rated on a
severity x likelihood grid, by-design risks and validation. Severity and likelihood
levels, their French translations and the risk grid come from the 4x4 privacy risk
matrix library, so the two stay aligned.

Pages assess what the processing already records rather than asking for it again:
they show its purposes, data, parties and controls as `facts`, and measure questions
offer the processing's own controls first (`subject_field`).

Usage:
    python tools/build_dpia_quick_form.py [output.yaml] [risk-matrix.yaml]

Defaults to the files in backend/library/libraries. Bump `version` below whenever
the generated content changes, or loaded instances will not pick it up.
"""

import sys
from pathlib import Path

import yaml

LIBRARIES = Path(__file__).resolve().parent.parent / "backend/library/libraries"
OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else LIBRARIES / "quick-form-dpia.yaml"
MATRIX = (
    Path(sys.argv[2])
    if len(sys.argv) > 2
    else LIBRARIES / "risk-matrix-4x4-privacy.yaml"
)

P = "urn:intuitem:risk:qf_page:dpia"


def text(t, required=True):
    q = {"type": "text", "text": t}
    if not required:
        q["required"] = False
    return q


# Severity and likelihood levels, and the risk they make, from the 4x4 privacy matrix.
_matrix = yaml.safe_load(MATRIX.read_text())["objects"]["risk_matrix"][0]
SLUG = {
    "Acceptable": "acceptable",
    "To reduce": "to_reduce",
    "Unacceptable": "unacceptable",
}


def _level(entry, ref_id):
    level = {
        "ref_id": ref_id,
        "label": entry["name"],
        "description": entry["description"],
    }
    fr = (entry.get("translations") or {}).get("fr")
    if fr:
        level["translations"] = {
            "fr": {"label": fr["name"], "description": fr["description"]}
        }
    return level


def _scale(ref_id, label, fr_label, entries):
    keys = ["negligible", "limited", "significant", "maximum"]
    return {
        "ref_id": ref_id,
        "label": label,
        "translations": {"fr": {"label": fr_label}},
        "levels": [_level(e, k) for e, k in zip(entries, keys)],
    }


SCALES = [
    _scale("severity", "Severity", "Gravité", _matrix["impact"]),
    _scale("likelihood", "Likelihood", "Vraisemblance", _matrix["probability"]),
]
RISK_LEVELS = [
    {**_level(r, SLUG[r["name"]]), "color": r["hexcolor"]} for r in _matrix["risk"]
]
# The matrix grid reads [likelihood][severity]; the rating's grid reads [severity][likelihood].
GRID = [
    [RISK_LEVELS[_matrix["grid"][l][s]]["ref_id"] for l in range(4)] for s in range(4)
]


def levels(page, key, t, required=True):
    scale = "severity" if key.endswith("severity") else "likelihood"
    config = {"widget": "slider", "scale": scale}
    if key.startswith("residual"):
        config["stage"] = "residual"
    q = {"type": "unique_choice", "text": t, "config": config}
    if not required:
        q["required"] = False
    return q


def measures(t, required=True):
    # The processing's own controls come first in the picker.
    q = {
        "type": "object_reference",
        "text": t,
        "config": {
            "model": "applied_control",
            "multiple": True,
            "subject_field": "associated_controls",
        },
    }
    if not required:
        q["required"] = False
    return q


def page(ref, name, description, questions, facts=None):
    p = {"urn": f"{P}:{ref}", "ref_id": ref, "name": name, "description": description}
    if facts:
        p["facts"] = [f"processing.{f}" for f in facts]
    p["questions"] = {f"{P}:{ref}:question:{k}": q for k, q in questions}
    return p


RECORD = (
    "Shown from the processing's record. To correct it, edit the processing: "
    "submitting this form keeps a copy of what was assessed."
)


def feared_event(ref, name, what):
    return page(
        ref,
        name,
        f"Analyse the causes and consequences of {what}, then estimate its severity and likelihood "
        "given the measures in place. Then estimate them again as they will stand once the "
        "planned measures are implemented.",
        [
            (
                "impacts",
                text(
                    "What would the main impacts on the data subjects be if this happened?"
                ),
            ),
            ("threats", text("What are the main threats that could make it happen?")),
            (
                "sources",
                text(
                    "Which risk sources could be behind it (internal or external people, non-human sources)?"
                ),
            ),
            ("measures", measures("Which measures treat this risk?", required=False)),
            (
                "severity",
                levels(
                    ref,
                    "severity",
                    "How severe is the risk, given the potential impacts and the measures in place?",
                ),
            ),
            ("severity_justification", text("Justify the severity")),
            (
                "likelihood",
                levels(
                    ref,
                    "likelihood",
                    "How likely is the risk, given the threats, the risk sources and the measures in place?",
                ),
            ),
            ("likelihood_justification", text("Justify the likelihood")),
            (
                "residual_severity",
                levels(
                    ref,
                    "residual_severity",
                    "Severity once the planned measures are implemented",
                    required=False,
                ),
            ),
            (
                "residual_likelihood",
                levels(
                    ref,
                    "residual_likelihood",
                    "Likelihood once the planned measures are implemented",
                    required=False,
                ),
            ),
        ],
    )


pages = [
    page(
        "overview",
        "Context: overview",
        "Identify the processing under study. Its purposes, data, parties and measures come from "
        "its record: the following pages show them for you to assess.\n\n"
        "Keep the completed response as the record of the assessment: Article 35 GDPR requires it.",
        [
            (
                "processing",
                {
                    "type": "object_reference",
                    "text": "Processing",
                    "config": {"model": "processing"},
                },
            ),
            (
                "benefits",
                text(
                    "What benefits are expected from the processing, and in what context is it used?"
                ),
            ),
            (
                "standards",
                text(
                    "Which standards apply to the processing? (approved codes of conduct, certifications…)",
                    required=False,
                ),
            ),
        ],
    ),
    page(
        "data",
        "Context: data, processes and supports",
        f"The data processed, about whom and for whom. {RECORD}",
        [
            ("access", text("Who can access the data, beyond the recipients listed?")),
            (
                "lifecycle",
                text(
                    "How does the data lifecycle unfold, from collection to deletion?"
                ),
            ),
            (
                "supports",
                text(
                    "What else does the data rely on, beyond the assets listed? (people, paper…)",
                    required=False,
                ),
            ),
        ],
        facts=["personal_data", "data_subjects", "recipients"],
    ),
    page(
        "proportionality",
        "Core principles: proportionality and necessity",
        f"Show that the processing complies with the core data protection principles. {RECORD}",
        [
            (
                "purposes",
                text(
                    "Are these purposes specified, explicit and legitimate, and does each rest on the right legal basis?"
                ),
            ),
            (
                "minimisation",
                text(
                    "Is the data adequate, relevant and limited to what is necessary for the purposes?"
                ),
            ),
            ("accuracy", text("Is the data accurate and kept up to date?")),
            (
                "retention",
                text(
                    "Why are the retention periods recorded for each kind of data necessary?"
                ),
            ),
        ],
        facts=["purposes"],
    ),
    page(
        "rights",
        "Core principles: measures protecting data subjects' rights",
        f"Show how data subjects can exercise their rights. {RECORD}",
        [
            (
                "information",
                text("How are data subjects informed about the processing?"),
            ),
            (
                "consent",
                text(
                    "If applicable, how is the data subjects' consent obtained?",
                    required=False,
                ),
            ),
            (
                "access_portability",
                text(
                    "How can data subjects exercise their rights of access and to data portability?"
                ),
            ),
            (
                "rectification_erasure",
                text(
                    "How can data subjects exercise their rights to rectification and erasure?"
                ),
            ),
            (
                "restriction_objection",
                text(
                    "How can data subjects exercise their rights to restriction and to object?"
                ),
            ),
            (
                "processors",
                text(
                    "Is a contract setting out their obligations in place with each of these parties?"
                ),
            ),
            (
                "transfers",
                text(
                    "Do the safeguards listed protect the data transferred outside the EU adequately?",
                    required=False,
                ),
            ),
        ],
        facts=["contractors", "transfers"],
    ),
    page(
        "measures",
        "Risks: existing or planned measures",
        "The measures the processing already has, existing or planned. Each is an applied control, so "
        "its owner, due date and status are tracked like any other. Measures picked in this form join "
        "the processing once the DPIA is accepted.",
        [
            (
                "measures",
                measures("Which measures should the processing add?", required=False),
            ),
            ("notes", text("Anything to add about these measures?", required=False)),
        ],
        facts=["controls"],
    ),
    feared_event(
        "illegitimate_access",
        "Risks: illegitimate access to data",
        "an illegitimate access to data",
    ),
    feared_event(
        "unwanted_modification",
        "Risks: unwanted modification of data",
        "an unwanted modification of data",
    ),
    feared_event(
        "disappearance", "Risks: disappearance of data", "a disappearance of data"
    ),
    page(
        "by_design",
        "Risks: by-design risks",
        "Risks the processing creates for data subjects even when everything works as intended "
        "(profiling, excessive monitoring, unfair automated decisions…), beyond security incidents.",
        [
            (
                "risks",
                text(
                    "Which risks does the processing create by design?", required=False
                ),
            ),
            ("measures", measures("Which measures treat them?", required=False)),
        ],
    ),
    page(
        "validation",
        "Validation",
        "Record the opinions sought and the decision on the processing.",
        [
            ("dpo_opinion", text("What is the DPO's opinion?")),
            (
                "dpo_advice_applied",
                text("How was the DPO's advice applied, or why not?", required=False),
            ),
            (
                "data_subject_views",
                text(
                    "What are the views of the data subjects or their representatives?",
                    required=False,
                ),
            ),
            (
                "views_not_sought_reason",
                text("If their views were not sought, why not?", required=False),
            ),
            (
                "decision",
                {
                    "type": "unique_choice",
                    "text": "Decision",
                    "choices": [
                        {
                            "urn": f"{P}:validation:question:decision:choice:{k}",
                            "value": v,
                        }
                        for k, v in [
                            ("proceed", "Proceed"),
                            ("proceed_conditionally", "Proceed with conditions"),
                            ("consult_sa", "Consult the supervisory authority"),
                            ("abandon", "Abandon"),
                        ]
                    ],
                },
            ),
            ("conditions", text("Conditions and action plan", required=False)),
        ],
    ),
]

library = {
    "urn": "urn:intuitem:risk:library:dpia",
    "locale": "en",
    "ref_id": "dpia",
    "name": "Data protection impact assessment (DPIA)",
    "description": "A DPIA following the structure of the CNIL PIA method: context, core principles, "
    "risks to data subjects and validation. Accepting a response records it as the "
    "processing's DPIA and adds the measures it picks to the processing.",
    "copyright": "© intuitem",
    "version": 6,
    "publication_date": "2026-10-13",
    "provider": "intuitem",
    "packager": "intuitem",
    "objects": {
        "quick_forms": [
            {
                "urn": "urn:intuitem:risk:quick_form:dpia",
                "ref_id": "dpia",
                "name": "DPIA",
                "description": "Data protection impact assessment of a processing.",
                "ref_id_prefix": "DPIA",
                "subject_question_urn": f"{P}:overview:question:processing",
                "on_accept": [
                    {"target": "processing.dpia", "config": {}},
                    {"target": "processing.controls", "config": {}},
                ],
                "scales_definition": SCALES,
                "outcomes_definition": [
                    {
                        "ref_id": "privacy_risk",
                        "kind": "rating",
                        "label": "Privacy risk",
                        "translations": {"fr": {"label": "Risque vie privée"}},
                        "dimensions": ["severity", "likelihood"],
                        "levels": RISK_LEVELS,
                        "grid": GRID,
                    },
                    {
                        "ref_id": "residual_risk_unacceptable",
                        "label": "Residual risk unacceptable: consult the supervisory authority",
                        "description": "A risk stays unacceptable once the planned measures are in "
                        "place. Article 36 GDPR requires prior consultation of the supervisory authority.",
                        "color": "#dc2626",
                        "expression": "has(values.privacy_risk_residual) && values.privacy_risk_residual >= 3.0",
                    },
                ],
                "pages": pages,
            }
        ]
    },
}
with OUTPUT.open("w") as out:
    yaml.safe_dump(library, out, sort_keys=False, allow_unicode=True, width=100)
