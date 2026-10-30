"""Build the MonServiceSécurisé V2 framing quick form from the MSS source.

The pages ask the MSS service description (what MSS calls "Décrire le service").
The outcomes reproduce MSS's own rules on those answers, so nothing is retyped:

- the security needs (`niveauSecuriteRequis`, src/moteurRegles/v2/niveauSecurite.ts),
  each carrying the implementation groups of the measures framework it applies;
- which of the 14 risks apply (`configurationSelectionVecteurs`) and which target
  objectives are in play (`configurationSelectionObjectifsVises`).

Usage:
    python tools/build_mss_framing_form.py [--source <mon-service-securise checkout>]
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

import build_mss_referentiel as mss

FORM_ID = "anssi-mss-v2-framing"
LIBRARY_URN = f"urn:intuitem:risk:library:quick-form-{FORM_ID}"
PAGE_URN = f"urn:intuitem:risk:qf_page:{FORM_ID}"
FRAMEWORK_URN = f"urn:intuitem:risk:framework:{mss.LIBRARY_ID}"
# MSS's risk grid is the EBIOS RM 4x4, cell for cell (niveauxRisques).
RISK_MATRIX_LIBRARY = "risk-matrix-4x4-ebios-rm"
OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "backend/library/libraries"
    / f"quick-form-{FORM_ID}.yaml"
)

SOURCES = {
    "questions": "donneesReferentielMesuresV2.ts",
    "niveaux": "svelte/lib/niveauxDeSecurite/donneesNiveauxDeSecurite.ts",
    "regles_niveau": "src/moteurRegles/v2/niveauSecurite.ts",
    "selection_vecteurs": "src/moteurRisques/v2/selectionVecteurs.configuration.ts",
    "selection_ov": "src/moteurRisques/v2/selectionObjectifsVises.configuration.ts",
    "gravite_ov": "src/moteurRisques/v2/graviteObjectifsVises.ts",
    "vecteur_ov": "src/moteurRisques/v2/graviteVecteurs.configuration.ts",
    "risques": "src/moteurRisques/v2/risqueV2.configuration.ts",
}

# (page ref_id, page name, questions). A question is (key, questionsV2 key or a
# fixed type, type, text as MSS words it, required, annotation). Texts are taken
# from the MSS creation screens (svelte/lib/creationV2/etapes/).
PAGES = [
    (
        "service",
        "Le service",
        [
            (
                "service",
                None,
                "object_reference",
                "Quel service homologuez-vous ?",
                True,
                "L'actif primaire qui représente le service dans CISO Assistant.",
            ),
            (
                "statut",
                "statutDeploiement",
                "unique_choice",
                "Quel est le statut de votre service ?",
                True,
                None,
            ),
            (
                "presentation",
                None,
                "text",
                "Présentez votre service en quelques lignes",
                False,
                None,
            ),
        ],
    ),
    (
        "perimetre",
        "Type de service et hébergement",
        [
            (
                "type_service",
                "typeDeService",
                "multiple_choice",
                "Quel est le type de service à sécuriser ?",
                True,
                None,
            ),
            (
                "specificites",
                "specificiteProjet",
                "multiple_choice",
                (
                    "L'une ou plusieurs des spécificités suivantes sont-elles incluses "
                    "dans le périmètre de l'homologation ?"
                ),
                False,
                None,
            ),
            (
                "hebergement",
                "typeHebergement",
                "unique_choice",
                "Quel type de cloud/hébergement utilisez-vous ?",
                True,
                None,
            ),
            (
                "activites",
                "activiteExternalisee",
                "multiple_choice",
                "Quelles activités du projet sont entièrement externalisées ?",
                False,
                None,
            ),
        ],
    ),
    (
        "donnees",
        "Données traitées",
        [
            (
                "categories",
                "categorieDonneesTraitees",
                "multiple_choice",
                "Quelles données sont traitées ?",
                False,
                None,
            ),
            (
                "autres_donnees",
                None,
                "text",
                "Données traitées supplémentaires",
                False,
                "Une catégorie par ligne.",
            ),
            (
                "volumetrie",
                "volumetrieDonneesTraitees",
                "unique_choice",
                "Quel est le volume des données traitées au sein du système d'information ?",
                True,
                None,
            ),
            (
                "localisation",
                "localisationDonneesTraitees",
                "unique_choice",
                "Où sont localisées les données traitées ?",
                True,
                None,
            ),
        ],
    ),
    (
        "usages",
        "Audience, disponibilité et ouverture",
        [
            (
                "audience",
                "audienceCible",
                "unique_choice",
                "Quelle est l'audience cible du service ?",
                True,
                (
                    "En cas de socle technique (ex. système d'hébergement d'autres "
                    "systèmes), l'audience doit être identifiée en prenant en compte "
                    "l'audience de l'ensemble des systèmes utilisant ce socle."
                ),
            ),
            (
                "duree",
                "dureeDysfonctionnementAcceptable",
                "unique_choice",
                "Quelle serait la durée maximale acceptable de dysfonctionnement du système ?",
                True,
                None,
            ),
            (
                "ouverture",
                "ouvertureSysteme",
                "unique_choice",
                "Quelle est l'ouverture du système ?",
                True,
                None,
            ),
        ],
    ),
]

# Severity of each target objective: the answer it reads and MSS's mapping of that
# answer (GraviteObjectifsVises.calculePourService, graviteObjectifsVises.ts).
OV_SEVERITY = {
    "OV1": ("usages:audience", "mappingAudienceCible"),
    "OV2": ("donnees:volumetrie", "mappingVolumetrieDonnees"),
    "OV3": ("usages:duree", "mappingDureeDysfonctionnement"),
    "OV4": ("usages:audience", "mappingAudienceCible"),
}

# Keys of the MSS service description, as the selection rules name them → question.
# `niveauSecurite` is not asked: rules on it read the computed security needs.
DESCRIPTION_KEYS = {
    "typeService": "perimetre:type_service",
    "specificitesProjet": "perimetre:specificites",
    "typeHebergement": "perimetre:hebergement",
    "activitesExternalisees": "perimetre:activites",
    "ouvertureSysteme": "usages:ouverture",
}


def load(source: Path) -> dict:
    read = lambda key: (source / SOURCES[key]).read_text(encoding="utf-8")
    lit = mss.js_literal
    regles = read("regles_niveau")
    return {
        "questions": lit(read("questions"), "questionsV2"),
        # Not exported upstream, so name it the way js_literal expects.
        "niveaux": lit(
            read("niveaux").replace(
                "const donneesNiveauxDeSecurite",
                "export const donneesNiveauxDeSecurite",
            ),
            "donneesNiveauxDeSecurite",
        ),
        "matrice_donnees": lit(regles, "matriceCriticiteVolumetrieDonneesTraitees"),
        "matrice_disponibilite": lit(
            regles, "matriceCriticiteAudienceCibleDisponibilite"
        ),
        "matrice_exposition": lit(regles, "matriceExposition"),
        "matrice_besoins": lit(regles, "matriceBesoinsSecuriteCriticiteExposition"),
        "selection_vecteurs": lit(
            read("selection_vecteurs"), "configurationSelectionVecteurs"
        ),
        "selection_ov": lit(
            read("selection_ov"), "configurationSelectionObjectifsVises"
        ),
        "risques": lit(read("risques"), "configurationRisqueV2"),
        "vecteur_ov": lit(read("vecteur_ov"), "matriceVecteurOV"),
        # Module-private upstream: exported here only so js_literal can read them.
        "gravite_ov": {
            name: lit(
                read("gravite_ov").replace(f"const {name}", f"export const {name}"),
                name,
            )
            for name in {mapping for _, mapping in OV_SEVERITY.values()}
        },
    }


def question_urn(key: str) -> str:
    page, q = key.split(":")
    return f"{PAGE_URN}:{page}:question:{q}"


def choice_urn(key: str, choice: str) -> str:
    return f"{question_urn(key)}:choice:{choice}"


# CEL reads answers by the URN tail after the 5th colon: "<page>:question:<q>".
def cel_answer(key: str) -> str:
    page, q = key.split(":")
    return f'answers["{page}:question:{q}"]'


def cel_selected(key: str, choice: str) -> str:
    page, q = key.split(":")
    return (
        f'"{page}:question:{q}:choice:{choice}" in {cel_answer(key)}.selected_choices'
    )


def cel_level(key: str, levels: dict, default: int | None = None) -> str:
    """Nested ternary giving the level of the chosen option(s), highest first."""
    ordered = sorted(levels.items(), key=lambda kv: -kv[1])
    expression = str(default if default is not None else ordered[-1][1])
    for choice, level in reversed(ordered if default is not None else ordered[:-1]):
        expression = f"({cel_selected(key, choice)} ? {level} : {expression})"
    return expression


def choices(data: dict, key: str, source_key: str) -> list[dict]:
    options = {}
    for choice, option in data["questions"][source_key].items():
        label = option.get("nom") or option.get("description") or choice
        if option.get("nom") and option.get("description"):
            label = f"{option['nom']} : {option['description']}"
        options[choice] = label.strip()
    return [{"urn": choice_urn(key, c), "value": v} for c, v in options.items()]


def criticite(data: dict, source_key: str) -> dict:
    return {c: o["criticite"] for c, o in data["questions"][source_key].items()}


def besoins(data: dict) -> tuple[str, str]:
    """niveauSecuriteRequis: max(criticité données, criticité disponibilité) crossed
    with the exposure, each factor a lookup in MSS's own matrices. Returns the CEL
    giving the level position (1-3) and the guard that its inputs are answered."""
    volume = cel_level(
        "donnees:volumetrie", criticite(data, "volumetrieDonneesTraitees")
    )
    # No category, or only "other" data, counts as criticité 1 (MSS reduces from 1).
    donnees = cel_level(
        "donnees:categories", criticite(data, "categorieDonneesTraitees"), default=1
    )
    audience = cel_level("usages:audience", criticite(data, "audienceCible"))
    duree = cel_level(
        "usages:duree", criticite(data, "dureeDysfonctionnementAcceptable")
    )
    ouverture = cel_level("usages:ouverture", criticite(data, "ouvertureSysteme"))

    crit_donnees = f"{data['matrice_donnees']}[{volume} - 1][{donnees} - 1]"
    crit_dispo = f"{data['matrice_disponibilite']}[{audience} - 1][{duree} - 1]"
    generale = f"({crit_donnees} > {crit_dispo} ? {crit_donnees} : {crit_dispo})"
    exposition = f"{data['matrice_exposition']}[0][{ouverture} - 1]"
    positions = positions_of(data)
    matrice = [[positions[v] for v in row] for row in data["matrice_besoins"]]
    level = f"{matrice}[{generale} - 1][{exposition} - 1]"
    answered = " && ".join(
        f"{cel_answer(k)}.answered"
        for k in (
            "donnees:volumetrie",
            "usages:audience",
            "usages:duree",
            "usages:ouverture",
        )
    )
    return level, answered


def positions_of(data: dict) -> dict:
    return {n["id"]: i + 1 for i, n in enumerate(data["niveaux"])}


# MSS's indicative homologation approach per level (`demarcheIndicative`) → the
# accreditation category it opens.
ACCREDITATION_CATEGORIES = {
    "simplifiée": "accreditation_simplified",
    "intermédiaire": "accreditation_elaborated",
    "renforcée": "accreditation_advanced",
}

NEEDS = "besoins_securite"
# Number rules run first and are stored as floats, read back as `values.<ref_id>`.
NEEDS_VALUE = f"values.{NEEDS}"


def niveau_outcomes(data: dict) -> list[dict]:
    """The needs level computed once as a number (0 until its inputs are
    answered), then one outcome per level carrying the framework implementation
    groups that level applies (indispensable and recommended), for the audit."""
    level, answered = besoins(data)
    positions = positions_of(data)
    outcomes = [
        {
            "ref_id": NEEDS,
            "kind": "number",
            "label": "Besoins de sécurité (1 Basiques, 2 Modérés, 3 Avancés)",
            "internal": True,
            "expression": f"{answered} ? {level} : 0",
        }
    ]
    for n in data["niveaux"]:
        code = mss.LEVELS[positions[n["id"]] - 1][0]
        outcomes.append(
            {
                "ref_id": f"besoins_{n['id']}",
                "label": f"Besoins de sécurité : {n['nom']}",
                "description": mss.html_to_markdown(n["resume"]),
                "group": "besoins_securite",
                "framework": FRAMEWORK_URN,
                "audit_implementation_groups": [f"{code}-I", f"{code}-R"],
                "accreditation_category": ACCREDITATION_CATEGORIES[
                    n["description"]["demarcheIndicative"]
                ],
                "expression": f"{NEEDS_VALUE} == {positions[n['id']]}.0",
            }
        )
    return outcomes


def selection(rule: dict, data: dict) -> str:
    """MSS keeps an item when something adds it and nothing removes it."""
    positions = positions_of(data)
    adds, removes = [], []
    for key, modifiers in rule["regles"].items():
        if key != "niveauSecurite" and key not in DESCRIPTION_KEYS:
            sys.exit(f"selection rule on unmapped description key `{key}`")
        for choice, order in modifiers.items():
            condition = (
                f"{NEEDS_VALUE} == {positions[choice]}.0"
                if key == "niveauSecurite"
                else cel_selected(DESCRIPTION_KEYS[key], choice)
            )
            (adds if order == "Ajouter" else removes).append(condition)
    added = (
        " || ".join((["true"] if rule["presentInitialement"] else []) + adds) or "false"
    )
    return f"({added}) && !({' || '.join(removes)})" if removes else f"({added})"


def cel_max(items: list[str]) -> str:
    expression = items[0]
    for item in items[1:]:
        expression = f"({item} > {expression} ? {item} : {expression})"
    return expression


def gravite_outcomes(data: dict) -> list[dict]:
    """Severity as MSS computes it (GraviteVecteurs): each selected target
    objective takes the level of one answer, and a risk takes the highest level
    among its objectives. Number rules, 0 while undetermined; the risk ones are
    read on accept as the scenario's impact."""
    outcomes = []
    for ov, rule in data["selection_ov"].items():
        question, mapping = OV_SEVERITY[ov]
        outcomes.append(
            {
                "ref_id": f"gravite_{ov.lower()}",
                "kind": "number",
                "label": f"Gravité {ov} (1 à 4)",
                "internal": True,
                "expression": (
                    f"({selection(rule, data)}) && {cel_answer(question)}.answered ? "
                    f"{cel_level(question, data['gravite_ov'][mapping])} : 0"
                ),
            }
        )
    for vector, ovs in data["vecteur_ov"].items():
        outcomes.append(
            {
                "ref_id": f"gravite_r{vector[1:]}",
                "kind": "number",
                "label": f"Gravité R{vector[1:]} (1 à 4)",
                "internal": True,
                "expression": cel_max([f"values.gravite_{ov.lower()}" for ov in ovs]),
            }
        )
    return outcomes


def selection_outcomes(data: dict) -> list[dict]:
    outcomes = []
    for vector, rule in data["selection_vecteurs"].items():
        risk = data["risques"][vector]
        outcomes.append(
            {
                "ref_id": f"risque_r{vector[1:]}",
                "label": f"R{vector[1:]} · {risk['intitule']}",
                "description": risk["description"],
                "group": "risques_retenus",
                # Read on accept by `asset.risk_assessment`: one scenario per fired risk.
                "scenario": {
                    "ref_id": f"R{vector[1:]}",
                    "name": risk["intitule"],
                    "threats": [mss.threat_urn(vector)],
                    # The number rule giving the scenario's impact (1-based level).
                    "impact_value": f"gravite_r{vector[1:]}",
                },
                "expression": selection(rule, data),
            }
        )
    labels = {
        ov: text
        for risk in data["risques"].values()
        for ov, text in risk["intitulesObjectifsVises"].items()
    }
    for ov, rule in data["selection_ov"].items():
        outcomes.append(
            {
                "ref_id": f"objectif_{ov.lower()}",
                "label": f"Objectif visé {ov} : {labels[ov].removeprefix('pour ')}",
                "group": "objectifs_vises",
                "expression": selection(rule, data),
            }
        )
    return outcomes


def validate(data: dict) -> None:
    """Every choice a rule names must exist in the question it maps to."""
    choice_keys = {
        f"{page}:{key}": set(data["questions"][src])
        if src and src in data["questions"]
        else set()
        for page, _, questions in PAGES
        for key, src, *_ in questions
    }
    for question, mapping in OV_SEVERITY.values():
        if set(data["gravite_ov"][mapping]) != choice_keys[question]:
            sys.exit(f"{mapping} does not match the choices of {question}")
    if set(data["vecteur_ov"]) != set(data["selection_vecteurs"]):
        sys.exit("matriceVecteurOV and the vector selection disagree")
    for name in ("selection_vecteurs", "selection_ov"):
        for item, rule in data[name].items():
            for key, modifiers in rule["regles"].items():
                known = (
                    set(positions_of(data))
                    if key == "niveauSecurite"
                    else choice_keys[DESCRIPTION_KEYS[key]]
                )
                unknown = set(modifiers) - known
                if unknown:
                    sys.exit(
                        f"{name} {item}: {key} names unknown choices {sorted(unknown)}"
                    )


def build(data: dict) -> dict:
    pages = []
    for page_ref, page_name, questions in PAGES:
        entries = {}
        for key, source_key, q_type, text, required, annotation in questions:
            full_key = f"{page_ref}:{key}"
            question = {"type": q_type, "text": text}
            if not required:
                question["required"] = False
            if annotation:
                question["annotation"] = annotation
            if q_type == "object_reference":
                question["config"] = {"model": "asset"}
            if source_key:
                question["choices"] = choices(data, full_key, source_key)
            entries[question_urn(full_key)] = question
        pages.append(
            {
                "urn": f"{PAGE_URN}:{page_ref}",
                "ref_id": page_ref,
                "name": page_name,
                "questions": entries,
            }
        )

    return {
        "urn": LIBRARY_URN,
        "locale": "fr",
        "ref_id": f"quick-form-{FORM_ID}",
        "name": "ANSSI - MonServiceSécurisé : cadrage du service",
        "description": (
            "Description d'un service numérique telle que MonServiceSécurisé la demande "
            "(type, hébergement, données, audience, disponibilité, ouverture). Les "
            "résultats reprennent les règles de MonServiceSécurisé V2 : besoins de "
            "sécurité, avec les groupes d'implémentation du référentiel de mesures qu'ils "
            "appliquent, risques retenus parmi les 14 du référentiel et objectifs visés."
            "\n\n"
            f"Source : https://github.com/betagouv/mon-service-securise (commit {mss.MSS_COMMIT})"
        ),
        "copyright": mss.COPYRIGHT,
        "version": 1,
        "publication_date": date.today().isoformat(),
        "provider": "ANSSI",
        "packager": "intuitem",
        "dependencies": [
            f"urn:intuitem:risk:library:{mss.LIBRARY_ID}",
            f"urn:intuitem:risk:library:{RISK_MATRIX_LIBRARY}",
        ],
        "objects": {
            "quick_forms": [
                {
                    "urn": f"urn:intuitem:risk:quick_form:{FORM_ID}",
                    "ref_id": FORM_ID,
                    "name": "Cadrage MonServiceSécurisé",
                    "description": (
                        "Décrire le service à homologuer. Les besoins de sécurité "
                        "et les risques retenus se mettent à jour à chaque réponse."
                    ),
                    "ref_id_prefix": "MSS",
                    "subject_question_urn": question_urn("service:service"),
                    "on_accept": [
                        {
                            "target": "asset.risk_assessment",
                            "config": {
                                "risk_matrix": f"urn:intuitem:risk:matrix:{RISK_MATRIX_LIBRARY}"
                            },
                        },
                        {
                            "target": "asset.audit",
                            "config": {"framework": FRAMEWORK_URN},
                        },
                        # Last: it files the two above in the cycle's collection.
                        {
                            "target": "asset.accreditation",
                            "config": {"name": "Homologation"},
                        },
                    ],
                    "title_question_urn": question_urn("service:service"),
                    "outcomes_definition": niveau_outcomes(data)
                    + gravite_outcomes(data)
                    + selection_outcomes(data),
                    "pages": pages,
                }
            ]
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the MonServiceSécurisé V2 framing quick form."
    )
    parser.add_argument("--source", type=Path, help="mon-service-securise checkout")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.source:
        data = load(args.source)
    else:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            mss.FILES = SOURCES
            data = load(mss.fetch(Path(tmp)))
    validate(data)
    library = build(data)
    yaml.add_representer(str, mss._str_representer)
    args.output.write_text(
        yaml.dump(library, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
