import csv
import re
from openpyxl import Workbook


INPUT_PATH = "Comparaison_ReCyf-NIS2_Annexe_Reglement_execution_2024_2690.csv"
OUTPUT_PATH = "recyf_to_reglement_2024_2690_mapping.xlsx"


def normalize_header(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_source_node_id(reference: str) -> str:
    """
    3.A.2-EI/EE -> 3.A.2
    """
    if not reference:
        return ""
    return str(reference).strip().split("-", 1)[0]


def parse_target_node_id(reg_ref: str) -> str:
    """
    Keep annex reference as-is, for example:
    12.4.2 -> 12.4.2
    """
    if not reg_ref:
        return ""

    text = str(reg_ref).strip()

    # Basic validation: keep references like 1.2.3 / 12.4.2 / etc.
    if re.fullmatch(r"\d+(?:\.\d+)+", text):
        return text

    return ""


def map_relationship_and_strength(correspondance: str):
    """
    élevé -> intersect, 90
    moyen -> intersect, 50
    other -> dropped
    """
    value = str(correspondance or "").strip().lower()

    if value == "élevé":
        return "intersect", 90
    if value == "moyen":
        return "intersect", 50

    return None, None


def read_csv(input_path):
    with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
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
        raise ValueError("Empty CSV")

    return rows


def generate_mapping(input_path, output_path):
    rows = read_csv(input_path)

    headers = [normalize_header(h) for h in rows[0]]
    data_rows = rows[1:]

    col_idx = {name: i for i, name in enumerate(headers)}

    required = ["Référence", "Correspondance"]
    missing = [c for c in required if c not in col_idx]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    reg_columns = [
        h for h in headers
        if h.startswith("Référence Annexe au Règlement d’exécution 2024/2690")
    ]

    if not reg_columns:
        raise ValueError(
            "No regulation reference columns found "
            "(expected headers starting with 'Référence Annexe au Règlement d’exécution 2024/2690')."
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "mapping"

    ws.append([
        "source_node_id",
        "target_node_id",
        "relationship",
        "strength_of_relationship",
    ])

    seen = set()

    for row in data_rows:
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))

        reference = row[col_idx["Référence"]]
        correspondance = row[col_idx["Correspondance"]]

        relationship, strength = map_relationship_and_strength(correspondance)
        if not relationship:
            continue

        source_node_id = parse_source_node_id(reference)
        if not source_node_id:
            continue

        for col in reg_columns:
            reg_ref = row[col_idx[col]]
            target_node_id = parse_target_node_id(reg_ref)

            if not target_node_id:
                continue

            mapping = (
                source_node_id,
                target_node_id,
                relationship,
                strength,
            )

            if mapping in seen:
                continue

            seen.add(mapping)
            ws.append(list(mapping))

    wb.save(output_path)

    print(f"Created: {output_path}")
    print(f"Mappings: {len(seen)}")


if __name__ == "__main__":
    generate_mapping(INPUT_PATH, OUTPUT_PATH)
