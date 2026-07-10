#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import unicodedata
import pandas as pd

TARGET_COLUMNS = [
    "Assessable",
    "Depth",
    "ref_ID",
    "Implementation Group",
    "Name",
    "Description",
    "typical_evidence",
    "Annotation",
]

EXPECTED_COLUMNS = [
    "Numéro chapitre",
    "Libellé chapitre",
    "Thématique",
    "Cible",
    "Niveau d'exigence",
    "Secteur",
    "Structures",
    "Publics",
    "Numéro Objectif",
    "Libellé objectifs",
    "Numéro Critère",
    "Libellé critères",
    "Éléments d'évaluation",
    "Consultation documentaire",
    "Observations",
]

GROUP_SPECS = [
    ("Thématique", "Thematique"),
    ("Cible", "Cible"),
    ("Niveau d'exigence", "Niveau"),
    ("Secteur", "Secteur"),
    ("Structures", "Structure"),
    ("Publics", "Public"),
]


def clean(x):
    if x is None or pd.isna(x):
        return ""
    return str(x).strip()


def strip_accents(text):
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(text))
        if not unicodedata.combining(c)
    )


def normalize_token(text):
    text = clean(text)
    text = strip_accents(text)
    text = text.replace("&", " et ")
    text = text.replace("/", "-")
    text = text.replace("'", "")
    text = text.replace("’", "")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^A-Za-z0-9\-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def build_group_ref(prefix, name):
    token = normalize_token(name)
    return f"{prefix}-{token}" if token else ""


def format_crit(ref):
    ref = clean(ref)
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", ref)
    if not m:
        return ref
    a, b, c = m.groups()
    return f"Critère {a}.{b}-{int(c):02d}"


def load_source(path):
    df = pd.read_excel(path)

    # Nettoyage des noms de colonnes
    df.columns = [str(c).strip() for c in df.columns]

    # Cas où la vraie ligne d'en-tête est sur la première ligne de données
    if "Numéro chapitre" not in df.columns and len(df) > 0:
        df.columns = [clean(x) for x in df.iloc[0]]
        df = df.iloc[1:].reset_index(drop=True)
        df.columns = [str(c).strip() for c in df.columns]

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        print("\nColonnes trouvées dans le fichier :")
        for c in df.columns:
            print("-", repr(c))
        raise ValueError(
            "\nColonnes source manquantes : " + ", ".join(missing)
        )

    return df


def build_row_groups(row):
    refs = []

    for col, prefix in GROUP_SPECS:
        if col in row.index:
            val = clean(row[col])
            if val:
                ref = build_group_ref(prefix, val)
                if ref:
                    refs.append(ref)

    return ",".join(refs)


def build_implementation_groups(df):
    rows = []
    seen = set()

    for col, prefix in GROUP_SPECS:
        if col not in df.columns:
            continue

        for val in df[col].dropna():
            val = clean(val)
            if not val:
                continue

            ref = build_group_ref(prefix, val)
            if not ref or ref in seen:
                continue

            rows.append({
                "ref_ID": ref,
                "name": val,
                "description": ""
            })
            seen.add(ref)

    return pd.DataFrame(rows, columns=["ref_ID", "name", "description"])


def build_target_from_source(df_source):
    rows = []
    last_chap = None
    last_obj = None

    for _, r in df_source.iterrows():
        chap = clean(r["Numéro chapitre"])
        chap_label = clean(r["Libellé chapitre"])

        obj = clean(r["Numéro Objectif"])
        obj_label = clean(r["Libellé objectifs"])

        crit = clean(r["Numéro Critère"])
        crit_label = clean(r["Libellé critères"])

        eval_ = clean(r["Éléments d'évaluation"])
        evidence = clean(r["Consultation documentaire"])
        obs = clean(r["Observations"])

        implementation_group = build_row_groups(r)

        # Depth 1 = Chapitre
        if chap and chap != last_chap:
            rows.append({
                "Assessable": "",
                "Depth": 1,
                "ref_ID": chap,
                "Implementation Group": "",
                "Name": f"Chapitre {chap}: {chap_label}" if chap_label else f"Chapitre {chap}",
                "Description": "",
                "typical_evidence": "",
                "Annotation": "",
            })
            last_chap = chap
            last_obj = None

        # Depth 2 = Objectif
        if obj and obj != last_obj:
            rows.append({
                "Assessable": "",
                "Depth": 2,
                "ref_ID": obj,
                "Implementation Group": "",
                "Name": "Objectif",
                "Description": obj_label,
                "typical_evidence": "",
                "Annotation": "",
            })
            last_obj = obj

        # Depth 3 = Critère
        rows.append({
            "Assessable": "",
            "Depth": 3,
            "ref_ID": format_crit(crit),
            "Implementation Group": "",
            "Name": "",
            "Description": crit_label,
            "typical_evidence": "",
            "Annotation": "",
        })

        # Depth 4 = Élément d'évaluation
        rows.append({
            "Assessable": "x",
            "Depth": 4,
            "ref_ID": "",
            "Implementation Group": implementation_group,
            "Name": "Éléments d'évaluation",
            "Description": eval_,
            "typical_evidence": evidence,
            "Annotation": obs,
        })

    return pd.DataFrame(rows, columns=TARGET_COLUMNS)


def main():
    parser = argparse.ArgumentParser(
        description="Transforme le fichier source en target + implementation_groups."
    )
    parser.add_argument("--source", required=True, help="Excel source")
    parser.add_argument("--output", required=True, help="Excel de sortie")
    args = parser.parse_args()

    df_source = load_source(args.source)
    df_target = build_target_from_source(df_source)
    df_groups = build_implementation_groups(df_source)

    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        df_target.to_excel(writer, sheet_name="target", index=False)
        df_groups.to_excel(writer, sheet_name="implementation_groups", index=False)

    print(f"OK - fichier généré : {args.output}")


if __name__ == "__main__":
    main()