#!/usr/bin/env python3
"""Build the MonServiceSécurisé (ANSSI) V2 measures framework and its ReCyF mapping.

Source: github.com/betagouv/mon-service-securise at a pinned commit (Apache-2.0).
- donneesReferentielMesuresV2.ts: the 135 measures (title, long description,
  category, numeric id, ANSSI/CNIL origin)
- donneesComplementairesReferentielMesuresV2.ts: the theme of each measure
- src/moteurRegles/v2/mesures_V2_prod_05-02-2026.csv: the rules engine, i.e.
  whether a measure is indispensable or recommended at each security level
  (Basique, Modéré, Avancé), whether it is in the default set, and how service
  characteristics add, remove or re-rate it
- src/mesures/referentielsExternes/correspondanceMesuresV2VersReCyf.ts: MSS's
  own correspondence from each measure to ReCyF measures
- src/moteurRisques/v2/risqueV2.configuration.ts: the 14 V2 risks, one per
  attack vector (title, description, example)
- src/moteurRisques/v2/vraisemblance/vraisemblance.V*.configuration.ts: per
  vector, the measures whose status sets its likelihood

Structure: theme (depth 1) > measure (assessable, ref_id = MSS id such as
ADMIN.1, which is the id the MSS public API returns).

Implementation groups: one per level and rating (B-I = Basique, indispensable;
B-R = Basique, recommended; ...). A measure is in a level's group when the
rules engine keeps it at that level. The characteristic modifiers cannot be
expressed as groups, so they are written in the annotation.

Reference controls link each measure to the doc-pol key reference controls
(REFERENCE_CONTROLS below, reviewed by hand).

Threats: the 14 attack vectors (MSS-V1..MSS-V14). A measure carries a vector as a
threat when MSS reads it to compute that vector's likelihood, at any security
level. Shared threats are what relate an audit on this framework to the risk
scenarios of the same asset.

Usage:
    python tools/build_mss_referentiel.py [--source path/to/mon-service-securise] [--output-dir DIR]

Without --source, the pinned commit is downloaded from GitHub.
"""

import argparse
import csv
import io
import json
import re
import sys
import tarfile
import tempfile
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIBRARIES = ROOT / "backend/library/libraries"

MSS_COMMIT = "1362dc43fde880dc2f188383b760cbe38fada8c8"
SOURCE_URL = (
    f"https://github.com/betagouv/mon-service-securise/archive/{MSS_COMMIT}.tar.gz"
)
FILES = {
    "mesures": "donneesReferentielMesuresV2.ts",
    "complements": "donneesComplementairesReferentielMesuresV2.ts",
    "regles": "src/moteurRegles/v2/mesures_V2_prod_05-02-2026.csv",
    "recyf": "src/mesures/referentielsExternes/correspondanceMesuresV2VersReCyf.ts",
    "risques": "src/moteurRisques/v2/risqueV2.configuration.ts",
}
VECTORS = [f"V{n}" for n in range(1, 15)]
FILES |= {
    f"vraisemblance_{v}": f"src/moteurRisques/v2/vraisemblance/vraisemblance.{v}.configuration.ts"
    for v in VECTORS
}

LIBRARY_ID = "anssi-mss-v2"
MAPPING_ID = f"mapping-{LIBRARY_ID}-and-recyf"
URN_PREFIX = "urn:intuitem:risk"
FRAMEWORK_URN = f"{URN_PREFIX}:framework:{LIBRARY_ID}"
URN_NODE = f"{URN_PREFIX}:req_node:{LIBRARY_ID}"
RECYF_LIBRARY_URN = f"{URN_PREFIX}:library:recyf"
RECYF_FRAMEWORK_URN = f"{URN_PREFIX}:framework:recyf"
DOC_POL_LIBRARY_URN = f"{URN_PREFIX}:library:doc-pol"
DOC_POL_URN = f"{URN_PREFIX}:function:doc-pol"
PUBLICATION_DATE = date(2026, 10, 30)
VERSION = 2
# The ReCyF mapping did not change when the threats were added.
MAPPING_PUBLICATION_DATE = date(2026, 10, 27)
MAPPING_VERSION = 1
EXPECTED_MEASURES = 135

NAME = "ANSSI - MonServiceSécurisé : référentiel de mesures V2"
DESCRIPTION = (
    "Référentiel de mesures V2 de MonServiceSécurisé, le service de l'ANSSI pour "
    "sécuriser et homologuer les services numériques publics : 135 mesures (129 "
    "ANSSI, 6 CNIL) réparties en 6 thématiques. Les groupes d'implémentation "
    "reprennent les besoins de sécurité de MonServiceSécurisé (Basique, Modéré, "
    "Avancé), chacun séparé en mesures indispensables et recommandées. "
    "MonServiceSécurisé ajuste en plus la liste selon les caractéristiques du "
    "service (données, disponibilité, ouverture, type de service, "
    "hébergement) : ces ajustements figurent dans l'annotation de chaque mesure. "
    "Les identifiants sont ceux renvoyés par l'API publique de "
    "MonServiceSécurisé. Les 14 risques V2 (un par vecteur d'attaque) sont fournis "
    "comme menaces : chaque mesure porte les menaces dont MonServiceSécurisé lit le "
    "statut pour en calculer la vraisemblance.\n\n"
    "Sources :\n"
    "- https://monservicesecurise.cyber.gouv.fr\n"
    f"- https://github.com/betagouv/mon-service-securise (commit {MSS_COMMIT[:7]})"
)
COPYRIGHT = (
    "Copyright ANSSI - Agence nationale de la sécurité des systèmes d'information "
    "(https://cyber.gouv.fr)\n\n"
    'Licensed under the Apache License, Version 2.0 (the "License");\n'
    "you may not use this file except in compliance with the License.\n"
    "You may obtain a copy of the License at\n\n"
    "    http://www.apache.org/licenses/LICENSE-2.0\n\n"
    "Unless required by applicable law or agreed to in writing, software distributed "
    'under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR '
    "CONDITIONS OF ANY KIND, either express or implied.\n"
    "See the License for the specific language governing permissions and "
    "limitations under the License."
)

LEVELS = [("B", "Basique"), ("M", "Modéré"), ("A", "Avancé")]
RATINGS = {"Indispensable": "I", "Recommandation": "R"}
IMPLEMENTATION_GROUPS = [
    {
        "ref_id": f"{code}-{rating}",
        "name": f"{level} : mesures {label}",
        "description": f"Mesures {label} pour un service au besoin de sécurité "
        f"{level.lower()}.",
    }
    for code, level in LEVELS
    for rating, label in (("I", "indispensables"), ("R", "recommandées"))
]

# rules CSV column -> readable characteristic
CHARACTERISTICS = {
    "Données : +": "données peu sensibles (+)",
    "Données : ++": "données sensibles (++)",
    "Données : +++": "données très sensibles (+++)",
    "Données : ++++": "données critiques (++++)",
    "Données : Hors UE": "données hors UE",
    "Dispo : +": "disponibilité +",
    "Dispo : ++": "disponibilité ++",
    "Dispo : +++": "disponibilité +++",
    "Dispo : ++++": "disponibilité ++++",
    "Ouv : +": "ouverture +",
    "Ouv : ++": "ouverture ++",
    "Ouv : +++": "ouverture +++",
    "Ouv : ++++": "ouverture ++++",
    "Accès physique : Salles techniques": "accès physique aux salles techniques",
    "Accès physique : Bureaux": "accès physique aux bureaux",
    "Annuaire": "annuaire",
    "Signature électronique": "signature électronique",
    "Application mobile": "application mobile",
    "Echange et/ou réception d'emails": "échange ou réception d'emails",
    "API": "API",
    "Portail d'information": "portail d'information",
    "Service en ligne": "service en ligne",
    "Autre Système d'information": "autre système d'information",
    "Poste de travail ou téléphone": "postes de travail ou téléphones",
    "EXT : Admin tech": "administration technique externalisée",
    "EXT : Dév": "développement externalisé",
    "EXT : MCO/MCS": "MCO/MCS externalisé",
    "EXT : On-premise": "hébergement on-premise",
    "EXT : PaaS / IaaS": "hébergement PaaS / IaaS",
    "EXT : SaaS": "hébergement SaaS",
}
# Projet / Presta / Mixte only say who carries the measure: not kept
MODIFIERS = {
    "Ajoutée": "Ajoutée si",
    "Retirée": "Retirée si",
    "Indispensable": "Rendue indispensable si",
    "Recommandation": "Rendue recommandée si",
}
RESPONSIBILITY = {"Projet", "Presta", "Mixte"}

CATEGORIES = {
    "gouvernance": "Gouvernance",
    "protection": "Protection",
    "defense": "Défense",
    "resilience": "Résilience",
}

# MSS measure -> doc-pol reference controls; empty = no matching key control
REFERENCE_CONTROLS = {
    "RECENSEMENT.1": ["DOC.ASSET_REGISTER", "DOC.SCOPE"],
    "RECENSEMENT.2": ["DOC.ASSET_REGISTER", "TECH.CMDB", "TECH.SW_INVENTORY"],
    "RECENSEMENT.3": ["POL.RETENTION", "POL.CLASSIF"],
    "CONFORMITE.1": ["DOC.LEGAL", "PROC.COMPLIANCE_MONITORING"],
    "CONFORMITE.3": ["DOC.SO_REGISTER"],
    "PSSI.5": ["POL.MAIN", "DOC.DOC_REGISTER"],
    "CONTRAT.1": ["POL.SUPPLIER", "DOC.SAP"],
    "CONTRAT.2": ["PROC.TPRM_ASSESSMENT"],
    "DEV.1": ["POL.SECDEV", "PROC.SDLC", "TRAIN.SECDEV"],
    "ECOSYSTEME.1": ["DOC.SUPPLIER_REGISTER"],
    "ECOSYSTEME.2": ["DOC.FLOW_MATRIX", "DOC.IS_MAP"],
    "ECOSYSTEME.3": ["POL.DATA_LOCATION", "POL.CLOUD"],
    "ECOSYSTEME.4": ["POL.DATA_LOCATION", "POL.CLOUD"],
    "ECOSYSTEME.5": ["PROC.DOMAIN_MGMT"],
    "ECOSYSTEME.6": ["PROC.DOMAIN_MGMT"],
    "RH.2": ["POL.EDUC", "DOC.EDUC_PLAN", "DOC.EDUC_REGISTER"],
    "RH.4": ["PROC.HR_SECURITY"],
    "CARTO.2": ["DOC.IS_MAP", "DOC.ARC_PRINCIPLES"],
    "DONNEES.1": ["POL.CRYPTO", "TECH.DISK_ENCRYPTION", "TECH.FILE_ENCRYPTION"],
    "DONNEES.2": ["POL.PRIVACY"],
    "MCO_MCS.1": ["POL.MAINTENANCE", "PROC.UPDATE"],
    "MCO_MCS.10": ["TECH.MDM"],
    "MCO_MCS.11": ["PROC.DISPOSAL"],
    "MCO_MCS.12": ["PROC.DISPOSAL", "PHYS.EQUIPMENT_DISPOSAL"],
    "MCO_MCS.14": ["PROC.UPDATE", "TECH.UEM"],
    "MCO_MCS.15": ["PROC.UPDATE"],
    "MCO_MCS.16": ["TECH.NETWORK_FIREWALL"],
    "MCO_MCS.17": ["POL.VULNERABILITY", "PROC.UPDATE"],
    "MCO_MCS.3": ["POL.THREAT_INTEL", "PROC.THREAT_INTEL"],
    "MCO_MCS.4": ["POL.VULNERABILITY", "PROC.UPDATE"],
    "MCO_MCS.5": ["PROC.SOFTWARE_LIFECYCLE"],
    "MCO_MCS.6": ["PROC.UPDATE"],
    "MCO_MCS.7": ["PROC.UPDATE"],
    "RGPD.1": ["DOC.ROPA"],
    "RGPD.2": ["POL.PRIVACY"],
    "RGPD.3": ["POL.RETENTION", "POL.PRIVACY"],
    "RGPD.4": ["DOC.PRIVACY_NOTICE", "POL.PRIVACY"],
    "RGPD.5": ["DOC.PRIVACY_NOTICE", "PROC.DATA_SUBJECT_RIGHTS"],
    "RGPD.6": ["PROC.DPIA"],
    "PHYS.1": ["POL.PHYSICAL", "PHYS.SECURE_AREA", "PHYS.VISITOR_MGMT"],
    "PHYS.2": ["PROC.PHYSICAL_SECURITY", "PHYS.SECURE_AREA"],
    "CLOISON.1": ["POL.NETWORK", "TECH.NETWORK_FIREWALL", "TECH.VLAN"],
    "CLOISON.2": ["POL.NETWORK", "TECH.VLAN"],
    "CLOISON.3": ["TECH.VLAN", "TECH.MICROSEGMENTATION"],
    "CLOISON.4": ["TECH.REVERSE_PROXY", "TECH.WEB_PROXY"],
    "CLOISON.5": ["DOC.FLOW_MATRIX"],
    "CLOISON.6": ["DOC.FLOW_MATRIX"],
    "FILTRE.1": ["DOC.FLOW_MATRIX", "TECH.NETWORK_FIREWALL"],
    "FILTRE.2": ["DOC.FLOW_MATRIX", "TECH.NETWORK_FIREWALL"],
    "FILTRE.3": ["DOC.FLOW_MATRIX", "POL.NETWORK"],
    "FILTRE.4": ["TECH.DDOS_PROTECTION"],
    "FILTRE.5": ["TECH.WAF"],
    "FILTRE.6": ["TECH.ENDPOINT_PROTECTION"],
    "FILTRE.7": ["TECH.APP_AUTH_HARDENING", "POL.WEB_SEC"],
    "MAIL.1": ["TECH.MAIL_GATEWAY"],
    "MAIL.2": ["TECH.EMAIL_AUTH"],
    "DISTANCE.1": ["TECH.VPN", "TECH.ZTNA"],
    "DISTANCE.2": ["TECH.MFA"],
    "DISTANCE.3": ["TECH.DISK_ENCRYPTION"],
    "DISTANCE.4": ["POL.ACCESS", "TECH.VPN"],
    "MALWARE.3": ["TECH.NETWORK_ANTIVIRUS", "POL.REMOVABLE_MEDIA"],
    "MALWARE.4": ["POL.MALWARE", "TECH.ENDPOINT_PROTECTION"],
    "MALWARE.5": ["TECH.EDR", "TECH.ENDPOINT_PROTECTION"],
    "MALWARE.6": ["TECH.EDR", "PROC.INCIDENT"],
    "AUTH.1": ["POL.HARDENING"],
    "AUTH.10": ["POL.ACCESS"],
    "AUTH.11": ["TECH.APP_AUTH_HARDENING", "POL.CRYPTO"],
    "AUTH.12": ["TECH.PASSWORD_MANAGER"],
    "AUTH.2": ["POL.ACCESS", "TECH.PASSWORD_MANAGER"],
    "AUTH.3": ["POL.ACCESS", "TECH.PASSWORD_MANAGER"],
    "AUTH.4": ["POL.ACCESS", "TECH.MFA"],
    "AUTH.5": ["POL.ACCESS"],
    "AUTH.6": ["POL.ACCESS"],
    "AUTH.7": ["POL.ACCESS"],
    "AUTH.8": ["TECH.APP_AUTH_HARDENING", "POL.WEB_SEC"],
    "AUTH.9": ["TECH.APP_AUTH_HARDENING", "POL.ACCESS"],
    "DROITS.1": ["POL.ACCESS", "PROC.RBAC"],
    "DROITS.2": ["POL.ACCESS", "PROC.RBAC"],
    "DROITS.3": ["PROC.RECERTIFICATION"],
    "ID.1": ["POL.ACCESS", "TECH.IAM"],
    "ID.2": ["PROC.RECERTIFICATION", "PROC.HR_SECURITY"],
    "ID.3": ["PROC.PAM"],
    "ID.4": ["PROC.RECERTIFICATION"],
    "ANNUAIRE.1": ["TECH.ADMIN_NETWORK", "DOC.ASSET_REGISTER"],
    "ANNUAIRE.2": ["TECH.ADMIN_NETWORK", "PROC.PAM", "TECH.PAW"],
    "ANNUAIRE.3": ["PROC.GPO", "POL.HARDENING"],
    "ANNUAIRE.5": ["TECH.ADMIN_NETWORK", "PROC.PAM", "TECH.PAW"],
    "COMPADMIN.1": ["PROC.PAM"],
    "COMPADMIN.2": ["PROC.PAM"],
    "COMPADMIN.3": ["PROC.PAM"],
    "COMPADMIN.4": ["DOC.PAM_REGISTER"],
    "COMPADMIN.5": ["PROC.PAM", "PROC.RECERTIFICATION"],
    "COMPADMIN.6": ["PROC.PAM"],
    "COMPADMIN.7": ["TECH.UEM", "POL.WORK"],
    "COMPADMIN.9": ["PROC.PAM"],
    "INCIDENT.1": ["POL.INCIDENT", "PROC.INCIDENT"],
    "INCIDENT.2": ["POL.INCIDENT"],
    "INCIDENT.3": ["TECH.SIEM", "PROC.LOGGING"],
    "INCIDENT.4": ["PROC.POST_INCIDENT"],
    "INCIDENT.6": ["PROC.VULN_DISCLOSURE"],
    "INCIDENT.7": ["PROC.INCIDENT", "PROC.CRISIS_MGMT"],
    "INCIDENT.8": ["PROC.INCIDENT"],
    "CONTINU.1": ["POL.BACKUP"],
    "CONTINU.2": ["TECH.IMMUTABLE_BACKUP"],
    "CONTINU.3": ["PROC.BIA", "DOC.BIA"],
    "CONTINU.5": ["PROC.DRP"],
    "CONTINU.6": ["TECH.DR_SITE", "PROC.CAPACITY_MGMT"],
    "RISQUE.1": ["POL.RISK", "DOC.RISK_REGISTER"],
    "RISQUE.2": ["POL.RISK", "DOC.RISK_REGISTER"],
    "AUDIT.1": ["POL.AUDIT", "DOC.AUDIT_PLAN"],
    "AUDIT.2": ["POL.AUDIT", "TECH.SAST_DAST"],
    "AUDIT.3": ["POL.PENTEST", "PROC.PENTEST"],
    "AUDIT.4": ["POL.AUDIT", "POL.HARDENING"],
    "AUDIT.5": ["POL.AUDIT", "DOC.ARC_PRINCIPLES"],
    "AUDIT.6": ["TECH.SAST_DAST"],
    "AUDIT.7": ["POL.AUDIT"],
    "CONFIG.1": ["POL.HARDENING", "POL.APP_CONTROL"],
    "CONFIG.2": ["POL.HARDENING"],
    "CONFIG.3": ["POL.HARDENING"],
    "CONFIG.4": ["TECH.PKI"],
    "CONFIG.5": ["POL.CRYPTO", "POL.TRANSFER"],
    "CONFIG.6": ["POL.HARDENING"],
    "CONFIG.7": ["TECH.PKI"],
    "CONFIG.8": ["POL.REMOVABLE_MEDIA", "TECH.ENDPOINT_PROTECTION"],
    "ADMIN.1": ["TECH.ADMIN_NETWORK", "TECH.PAW", "PROC.PAM"],
    "ADMIN.2": ["TECH.ADMIN_NETWORK", "PROC.PAM"],
    "ADMIN.3": ["TECH.ADMIN_NETWORK", "TECH.PAW"],
    "ADMIN.4": ["TECH.PAW"],
    "ADMIN.5": ["TECH.ADMIN_NETWORK", "TECH.PAW"],
    "ADMIN.6": ["TECH.ADMIN_NETWORK", "POL.NETWORK", "PROC.PAM"],
    "ADMIN.7": ["TECH.ADMIN_NETWORK", "POL.CRYPTO", "PROC.PAM"],
    "SUPERVISION.4": ["PROC.LOGGING", "TECH.SIEM"],
    "SUPERVISION.5": ["PROC.LOGGING"],
    "SUPERVISION.6": ["TECH.ACCESS_LOG"],
    "SUPERVISION.7": ["TECH.SIEM"],
}


def fetch(dest: Path) -> Path:
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:  # nosec B310
        payload = response.read()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        root = archive.getnames()[0].split("/")[0]
        members = [archive.getmember(f"{root}/{path}") for path in FILES.values()]
        archive.extractall(dest, members=members, filter="data")
    return dest / root


def js_literal(source: str, name: str):
    """Parse the object literal assigned to `export const <name>` as data, without running it."""
    start = re.search(rf"export const {name}\b[^=]*=\s*", source)
    if not start:
        sys.exit(f"`{name}` not found")
    out, i, depth = [], start.end(), 0
    while True:
        char = source[i]
        if char in "'\"`":
            end = i + 1
            while source[end] != char:
                end += 2 if source[end] == "\\" else 1
            raw = source[i + 1 : end]
            if char == "`" and "${" in raw:
                sys.exit(f"`{name}`: template interpolation is not data")
            text = re.sub(
                r"\\(.)",
                lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)),
                raw,
            )
            out.append(json.dumps(text))
            i = end + 1
        elif char in "{[":
            depth += 1
            out.append(char)
            i += 1
        elif char in "}]":
            depth -= 1
            if out and out[-1] == ",":
                out.pop()
            out.append(char)
            i += 1
            if depth == 0:
                return json.loads("".join(out))
        elif char == "/" and source[i + 1] == "/":
            i = source.index("\n", i)
        elif m := re.match(r"[A-Za-z_$][\w$]*", source[i:]):
            word = m.group(0)
            out.append(word if word in ("true", "false", "null") else json.dumps(word))
            i += len(word)
        elif m := re.match(r"-?\d+(\.\d+)?", source[i:]):
            out.append(m.group(0))
            i += len(m.group(0))
        elif char.isspace():
            i += 1
        elif char in ",:":
            out.append(char)
            i += 1
        else:
            sys.exit(f"`{name}`: unexpected {char!r} at offset {i}")


def likelihood_config(source: str, vector: str) -> dict:
    """A vraisemblance.V*.configuration.ts as data. Its formulas are arrow
    functions: each one's body (an expression over the groups and their weights)
    is kept as a string."""
    as_data = re.sub(
        r"\(\{[^}]*\}\s*:\s*ConfigurationPredicatVraisemblance\)\s*=>\s*(.+?)(?=,\s*(?:\(\{|\]))",
        lambda m: json.dumps(" ".join(m.group(1).split())),
        source,
        flags=re.DOTALL,
    )
    return js_literal(as_data, vector)


def load(source: Path) -> dict:
    read = lambda key: (source / FILES[key]).read_text(encoding="utf-8")  # noqa: E731
    return {
        "mesures": js_literal(read("mesures"), "mesuresV2"),
        "complements": js_literal(
            read("complements"), "donneesComplementairesMesureV2"
        ),
        "regles": list(csv.DictReader(io.StringIO(read("regles").lstrip("﻿")))),
        "recyf": js_literal(read("recyf"), "correspondanceMesuresV2VersReCyf"),
        "risques": js_literal(read("risques"), "configurationRisqueV2"),
        "vraisemblance": {
            v: sorted(set(re.findall(r"'([A-Z_]+\.\d+)'", read(f"vraisemblance_{v}"))))
            for v in VECTORS
        },
        "vraisemblance_config": {
            v: likelihood_config(read(f"vraisemblance_{v}"), v) for v in VECTORS
        },
    }


def ref_ids(path: Path, key: str) -> set[str]:
    objects = yaml.safe_load(path.read_text(encoding="utf-8"))["objects"]
    if key == "reference_controls":
        return {c["ref_id"] for c in objects[key]}
    return {n["urn"] for n in objects["framework"]["requirement_nodes"]}


def recyf_urn(recyf_id: str) -> str:
    # MSS suffixes ReCyF ids with the entity type they apply to: 19.1-EE, 10.B.2-EI/EE
    return f"{URN_PREFIX}:req_node:recyf:{recyf_id.split('-')[0].lower()}"


def validate(data: dict, libraries: Path) -> None:
    mesures, regles = data["mesures"], data["regles"]
    rule_ids = [r["REF"] for r in regles]
    errors = []
    if len(mesures) != EXPECTED_MEASURES:
        errors.append(f"expected {EXPECTED_MEASURES} measures, found {len(mesures)}")
    if set(rule_ids) != set(mesures) or len(rule_ids) != len(set(rule_ids)):
        errors.append("rules and measures do not list the same ids")
    if missing := set(mesures) - set(data["complements"]):
        errors.append(f"no theme for {sorted(missing)}")
    if set(REFERENCE_CONTROLS) != set(mesures):
        errors.append(
            f"REFERENCE_CONTROLS out of sync: {sorted(set(REFERENCE_CONTROLS) ^ set(mesures))}"
        )
    known_controls = ref_ids(
        libraries / "key-reference-controls.yaml", "reference_controls"
    )
    if (
        unknown := {c for cs in REFERENCE_CONTROLS.values() for c in cs}
        - known_controls
    ):
        errors.append(f"unknown doc-pol controls: {sorted(unknown)}")
    known_recyf = ref_ids(libraries / "recyf.yaml", "requirement_nodes")
    if unknown := {
        t
        for ts in data["recyf"].values()
        for t in ts
        if recyf_urn(t) not in known_recyf
    }:
        errors.append(f"ReCyF ids not in recyf.yaml: {sorted(unknown)}")
    if unknown := set(data["recyf"]) - set(mesures):
        errors.append(f"ReCyF correspondence on unknown measures: {sorted(unknown)}")
    for rule in regles:
        for column, value in rule.items():
            if column in CHARACTERISTICS and value:
                if (
                    bad := {t.strip() for t in value.split(",")}
                    - set(MODIFIERS)
                    - RESPONSIBILITY
                ):
                    errors.append(f"{rule['REF']} {column}: unknown modifiers {bad}")
        for _, level in LEVELS:
            if rule[level] and rule[level] not in RATINGS:
                errors.append(f"{rule['REF']} {level}: unknown rating {rule[level]!r}")
    if errors:
        sys.exit("invalid MSS data:\n  " + "\n  ".join(errors))


def html_to_markdown(text: str) -> str:
    text = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", text)
    text = re.sub(r"(<br>\s*){2,}", "\n\n", text).replace("<br>", "\n")
    if leftover := re.findall(r"<[^>]+>", text):
        sys.exit(f"unhandled HTML: {leftover}")
    return text.strip()


def annotation(mesure: dict, rule: dict) -> str:
    lines = [
        f"Identifiant MSS : #{mesure['identifiantNumerique']} · "
        f"Catégorie : {CATEGORIES[mesure['categorie']]} · "
        f"Origine : {mesure['referentiel']}"
    ]
    if rule["Statut initial"] == "Absente":
        lines.append(
            "Non retenue par défaut : seules les caractéristiques ci-dessous l'ajoutent."
        )
    for modifier, label in MODIFIERS.items():
        when = [
            CHARACTERISTICS[column]
            for column, value in rule.items()
            if column in CHARACTERISTICS
            and modifier in {t.strip() for t in value.split(",")}
        ]
        if when:
            lines.append(f"{label} : {', '.join(when)}.")
    return "\n".join(lines)


SELECTED = "assessment.selected_implementation_groups"
FORMULA = re.compile(
    r"(\s*(\d+|poids[A-Z]|(siTout|siAucune|siPasTout)\([a-z]\)|[-+*()]))+\s*"
)


def cel_formula(formula: str, groups: dict, in_scope) -> str:
    """One MSS likelihood formula in CEL. Its predicates (vraisemblance.predicats.ts)
    read the group's measures; every number is a double, as CEL will not mix types.

    MSS counts a measure as done when it is `fait`, or not in the service's own
    set. Here: compliant or not applicable, or outside the level's groups, which
    are the groups the audit is scoped to. The scope is settled now, so a measure
    out of it drops out of the expression. `non_compliant` stands for both
    `aLancer` and `nonFait`, which MSS tells apart."""
    if not FORMULA.fullmatch(formula):
        sys.exit(f"unexpected likelihood formula: {formula}")

    def predicate(match) -> str:
        measures = groups[match.group(2)]["idsMesures"]
        checked = [
            f'requirements["{m.lower()}"].result in ["compliant", "not_applicable"]'
            for m in measures
            if in_scope(m)
        ]
        all_done = " && ".join(checked) or "true"
        if match.group(1) == "siTout":
            return f"({all_done} ? 1.0 : 0.0)"
        if match.group(1) == "siPasTout":
            return f"({all_done} ? 0.0 : 1.0)"
        # siAucune: a measure out of scope counts as done, so the group has one.
        if len(checked) < len(measures):
            return "0.0"
        return f"(({' || '.join(checked)}) ? 0.0 : 1.0)"

    expression = re.sub(r"\b(\d+)\b", r"\1.0", formula)
    expression = re.sub(
        r"poids([A-Z])",
        lambda m: f"{float(groups[m.group(1).lower()]['poids'])}",
        expression,
    )
    return (
        f"({re.sub(r'(siTout|siAucune|siPasTout)\(([a-z])\)', predicate, expression)})"
    )


def cel_max(items: list[str]) -> str:
    expression = items[0]
    for item in items[1:]:
        expression = f"({item} > {expression} ? {item} : {expression})"
    return expression


def likelihood_rules(config: dict, vector: str, measure_groups: dict) -> list[dict]:
    """MSS's likelihood of a vector (VraisemblanceRisque), as two audit number
    rules: the highest formula of the audit's level, read from its selected
    groups (-1 where MSS has no formula at that level), then bounded to 1-4.
    `likelihood_of` names the threat whose scenarios it scores."""
    by_level = {}
    for position, (code, _) in enumerate(LEVELS, start=1):
        level = config.get(f"niveau{position}")
        scope = {f"{code}-I", f"{code}-R"}

        def in_scope(mss_id, scope=scope):
            return bool(scope & set(measure_groups.get(mss_id, [])))

        by_level[code] = (
            cel_max(
                [cel_formula(f, level["groupes"], in_scope) for f in level["formules"]]
            )
            if level
            else "-1.0"
        )
    has = lambda code: f'("{code}-I" in {SELECTED} || "{code}-R" in {SELECTED})'
    raw = f"vraisemblance_brute_{vector.lower()}"
    value = f"values.{raw}"
    return [
        {
            "ref_id": raw,
            "kind": "number",
            "label": f"Vraisemblance MSS-{vector} avant bornage",
            "internal": True,
            "expression": (
                f"{has('A')} ? {by_level['A']} : ({has('M')} ? {by_level['M']} : "
                f"{by_level['B']})"
            ),
        },
        {
            "ref_id": f"vraisemblance_{vector.lower()}",
            "kind": "number",
            "label": f"Vraisemblance MSS-{vector} (1 à 4)",
            "internal": True,
            "likelihood_of": threat_urn(vector),
            "expression": (
                f"{value} < 0.0 ? 0.0 : ({value} < 1.0 ? 1.0 : "
                f"({value} > 4.0 ? 4.0 : {value}))"
            ),
        },
    ]


def threat_urn(vector: str) -> str:
    return f"{URN_PREFIX}:threat:{LIBRARY_ID}:{vector.lower()}"


def build(data: dict) -> tuple[dict, dict]:
    mesures, complements = data["mesures"], data["complements"]
    if set(data["risques"]) != set(VECTORS):
        sys.exit(f"risk vectors changed upstream: {sorted(data['risques'])}")
    unknown = {m for ids in data["vraisemblance"].values() for m in ids} - set(mesures)
    if unknown:
        sys.exit(f"likelihood configs name unknown measures: {sorted(unknown)}")
    threats = [
        {
            "urn": threat_urn(vector),
            "ref_id": f"MSS-{vector}",
            "name": data["risques"][vector]["intitule"],
            "description": "\n\n".join(
                html_to_markdown(data["risques"][vector][key])
                for key in ("description", "exemple")
            ),
        }
        for vector in VECTORS
    ]
    nodes, themes = [], {}
    for rule in data["regles"]:
        mss_id = rule["REF"]
        mesure = mesures[mss_id]
        theme = complements[mss_id]["thematique"]
        if theme not in themes:
            themes[theme] = f"{URN_NODE}:t{len(themes) + 1}"
            nodes.append(
                {
                    "urn": themes[theme],
                    "assessable": False,
                    "depth": 1,
                    "ref_id": f"T{len(themes)}",
                    "name": theme,
                }
            )
        node = {
            "urn": f"{URN_NODE}:{mss_id.lower()}",
            "assessable": True,
            "depth": 2,
            "parent_urn": themes[theme],
            "ref_id": mss_id,
            "name": mesure["description"].strip(),
            "description": html_to_markdown(mesure["descriptionLongue"]),
            "annotation": annotation(mesure, rule),
        }
        groups = [
            f"{code}-{RATINGS[rule[level]]}" for code, level in LEVELS if rule[level]
        ]
        if groups:
            node["implementation_groups"] = groups
        if controls := REFERENCE_CONTROLS[mss_id]:
            node["reference_controls"] = [
                f"{DOC_POL_URN}:{c.lower()}" for c in controls
            ]
        if vectors := [v for v in VECTORS if mss_id in data["vraisemblance"][v]]:
            node["threats"] = [threat_urn(v) for v in vectors]
        nodes.append(node)

    library = {
        "urn": f"{URN_PREFIX}:library:{LIBRARY_ID}",
        "locale": "fr",
        "ref_id": "ANSSI-MSS-V2",
        "name": NAME,
        "description": DESCRIPTION,
        "copyright": COPYRIGHT,
        "version": VERSION,
        "publication_date": PUBLICATION_DATE,
        "provider": "ANSSI",
        "packager": "intuitem",
        "dependencies": [DOC_POL_LIBRARY_URN],
        "objects": {
            "threats": threats,
            "framework": {
                "urn": FRAMEWORK_URN,
                "ref_id": "ANSSI-MSS-V2",
                "name": NAME,
                "description": DESCRIPTION,
                "field_visibility": {
                    "extended_result": {"auditor": "hidden", "respondent": "hidden"}
                },
                "implementation_groups_definition": IMPLEMENTATION_GROUPS,
                "outcomes_definition": [
                    rule
                    for vector in VECTORS
                    for rule in likelihood_rules(
                        data["vraisemblance_config"][vector],
                        vector,
                        {
                            n["ref_id"]: n.get("implementation_groups", [])
                            for n in nodes
                            if n["assessable"]
                        },
                    )
                ],
                "requirement_nodes": nodes,
            },
        },
    }

    mapping_description = (
        f"Mapping between {NAME} and ReCyF, taken from the correspondence table "
        "published by MonServiceSécurisé (correspondanceMesuresV2VersReCyf, commit "
        f"{MSS_COMMIT[:7]}). Measures without a ReCyF counterpart in that table are "
        "left unmapped."
    )
    mappings = [
        {
            "source_requirement_urn": f"{URN_NODE}:{mss_id.lower()}",
            "target_requirement_urn": urn,
            "relationship": "intersect",
            "rationale": "semantic",
        }
        for rule in data["regles"]
        for mss_id in [rule["REF"]]
        for urn in dict.fromkeys(recyf_urn(t) for t in data["recyf"].get(mss_id, []))
    ]
    mapping = {
        "urn": f"{URN_PREFIX}:library:{MAPPING_ID}",
        "locale": "fr",
        "ref_id": MAPPING_ID,
        "name": f"{NAME} <-> ReCyF",
        "description": mapping_description,
        "copyright": COPYRIGHT,
        "version": MAPPING_VERSION,
        "publication_date": MAPPING_PUBLICATION_DATE,
        "provider": "ANSSI",
        "packager": "intuitem",
        "dependencies": [library["urn"], RECYF_LIBRARY_URN],
        "objects": {
            "requirement_mapping_sets": [
                {
                    "urn": f"{URN_PREFIX}:req_mapping_set:{MAPPING_ID}",
                    "ref_id": MAPPING_ID,
                    "name": f"{NAME} <-> ReCyF",
                    "description": mapping_description,
                    "source_framework_urn": FRAMEWORK_URN,
                    "target_framework_urn": RECYF_FRAMEWORK_URN,
                    "requirement_mappings": mappings,
                }
            ]
        },
    }
    return library, mapping


def _str_representer(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the MSS V2 measures library.")
    parser.add_argument("--source", type=Path, help="mon-service-securise checkout")
    parser.add_argument("--output-dir", type=Path, default=LIBRARIES)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        data = load(args.source or fetch(Path(tmp)))
    validate(data, LIBRARIES)
    library, mapping = build(data)
    yaml.add_representer(str, _str_representer)
    for name, document in ((LIBRARY_ID, library), (MAPPING_ID, mapping)):
        path = args.output_dir / f"{name}.yaml"
        path.write_text(
            yaml.dump(document, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
        print(f"wrote {path}")
    nodes = library["objects"]["framework"]["requirement_nodes"]
    print(
        "groups:",
        dict(Counter(g for n in nodes for g in n.get("implementation_groups", []))),
        "| no reference control:",
        [
            n["ref_id"]
            for n in nodes
            if n["assessable"] and "reference_controls" not in n
        ],
        "| ReCyF links:",
        len(mapping["objects"]["requirement_mapping_sets"][0]["requirement_mappings"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
