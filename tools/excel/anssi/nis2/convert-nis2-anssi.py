import csv
import re
from openpyxl import Workbook


def normalize_header(value):
    if value is None:
        return ""
    return str(value).strip()


def natural_sort_key(ref):
    """
    Sorts references like:
    1.2-EI/EE
    1.10-EI/EE
    2.1-XX
    by treating numeric parts as numbers.
    """
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


def read_csv_rows(input_csv_path):
    """
    Reads CSV and auto-handles common French/Excel separators.
    """
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

    required = ["Référence", "Contenu", "Objectif", "Thématique", "Cibles"]
    missing = [c for c in required if c not in col_idx]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    parsed_rows = []
    for row in data_rows:
        # pad short rows if needed
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))

        reference = row[col_idx["Référence"]].strip()
        contenu = row[col_idx["Contenu"]].strip()
        objectif = row[col_idx["Objectif"]].strip()
        thematique = row[col_idx["Thématique"]].strip()
        cibles = row[col_idx["Cibles"]].strip()

        # skip fully empty rows
        if not any([reference, contenu, objectif, thematique, cibles]):
            continue

        parsed_rows.append({
            "Référence": reference,
            "Contenu": contenu,
            "Objectif": objectif,
            "Thématique": thematique,
            "Cibles": cibles,
        })

    # Sort by reference using natural sort
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
        reference = row["Référence"]
        contenu = row["Contenu"]
        objectif = row["Objectif"]
        thematique = row["Thématique"]
        cibles = row["Cibles"]

        # depth 1 row when Objectif changes
        if objectif != last_objectif:
            ws.append(["", 1, "", objectif, "", ""])
            last_objectif = objectif
            last_thematique = None

        # depth 2 row when Thématique changes
        if thematique != last_thematique:
            ws.append(["", 2, "", thematique, "", ""])
            last_thematique = thematique

        # depth 3 row for every requirement
        ws.append([
            "x",
            3,
            reference,
            "",
            contenu,
            cibles,
        ])

    wb.save(output_xlsx_path)


if __name__ == "__main__":
    convert_nis2_csv_to_ciso_assistant(
        "Liste_des_exigences_applicables_a_NIS2.csv",
        "ciso_assistant_import.xlsx",
    )
    print("Created: ciso_assistant_import.xlsx")
