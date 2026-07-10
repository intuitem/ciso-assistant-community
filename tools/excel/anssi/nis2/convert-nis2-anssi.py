import csv
import re
from openpyxl import Workbook


def normalize_header(value):
    if value is None:
        return ""
    return str(value).strip()


def natural_sort_key(ref):
    if ref is None:
        return []

    text = str(ref).strip()
    parts = re.split(r"(\d+)", text)

    key = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part.lower())

    return key


def split_reference(ref):
    """
    Example:
    5.B.2-EI/EE -> ("5.B.2", "EI, EE")
    4.1-EI/EE   -> ("4.1", "EI, EE")
    """
    if not ref:
        return "", ""

    ref = str(ref).strip()

    if "-" in ref:
        left, right = ref.split("-", 1)
        groups = [g.strip() for g in right.split("/") if g.strip()]
        return left.strip(), ", ".join(groups)

    return ref, ""


def extract_objectif_id(objectif):
    """
    "Objectif de sécurité 3" -> "3"
    """
    if not objectif:
        return ""

    match = re.search(r"(\d+)", str(objectif))
    return match.group(1) if match else ""


def extract_thematique_id(reference):
    """
    Rules:
    - 3.A.1-EI/EE -> "3.A"
    - 4.1-EI/EE   -> ""   (no level-2 ref_id)
    """
    if not reference:
        return ""

    ref = str(reference).strip().split("-")[0]
    parts = ref.split(".")

    if len(parts) >= 2 and parts[1].isalpha():
        return f"{parts[0]}.{parts[1]}"

    return ""


def read_csv_rows(input_csv_path):
    with open(input_csv_path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ";"

        reader = csv.reader(f, delimiter=delimiter)
        rows = list(reader)

    if not rows:
        raise ValueError("The CSV file is empty.")

    return rows


def convert_nis2_csv_to_ciso_assistant(input_csv_path: str, output_xlsx_path: str) -> None:
    rows = read_csv_rows(input_csv_path)

    headers = [normalize_header(h) for h in rows[0]]
    data_rows = rows[1:]

    col_idx = {name: i for i, name in enumerate(headers)}

    required = ["Référence", "Contenu", "Objectif", "Thématique"]
    missing = [c for c in required if c not in col_idx]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    parsed_rows = []
    for row in data_rows:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))

        reference = str(row[col_idx["Référence"]] or "").strip()
        contenu = str(row[col_idx["Contenu"]] or "").strip()
        objectif = str(row[col_idx["Objectif"]] or "").strip()
        thematique = str(row[col_idx["Thématique"]] or "").strip()

        if not any([reference, contenu, objectif, thematique]):
            continue

        parsed_rows.append({
            "Référence": reference,
            "Contenu": contenu,
            "Objectif": objectif,
            "Thématique": thematique,
        })

    parsed_rows.sort(key=lambda r: natural_sort_key(r["Référence"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "requirements"

    ws.append([
        "assessable",
        "depth",
        "ref_id",
        "name",
        "description",
        "implementation_groups",
    ])

    last_objectif = None
    last_thematique = None

    for row in parsed_rows:
        full_reference = row["Référence"]
        contenu = row["Contenu"]
        objectif = row["Objectif"]
        thematique = row["Thématique"]

        objectif_id = extract_objectif_id(objectif)
        thematique_id = extract_thematique_id(full_reference)
        ref_id, implementation_groups = split_reference(full_reference)

        # Depth 1
        if objectif != last_objectif:
            ws.append([
                "",
                1,
                objectif_id,
                objectif,
                "",
                "",
            ])
            last_objectif = objectif
            last_thematique = None

        # Case 1: there is a real level 2 (e.g. 3.A.1)
        if thematique_id:
            if thematique != last_thematique:
                ws.append([
                    "",
                    2,
                    thematique_id,
                    thematique,
                    "",
                    "",
                ])
                last_thematique = thematique

            ws.append([
                "x",
                3,
                ref_id,
                "",
                contenu,
                implementation_groups,
            ])

        # Case 2: no level 2 (e.g. 4.1), requirement becomes level 2
        else:
            last_thematique = None
            ws.append([
                "x",
                2,
                ref_id,
                "",
                contenu,
                implementation_groups,
            ])

    wb.save(output_xlsx_path)


if __name__ == "__main__":
    convert_nis2_csv_to_ciso_assistant(
        "Liste_des_exigences_applicables_a_NIS2.csv",
        "ciso_assistant_import.xlsx",
    )
    print("Created: ciso_assistant_import.xlsx")
