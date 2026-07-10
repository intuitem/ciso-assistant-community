import csv
import re
from openpyxl import Workbook


INPUT_PATH = "Comparaison_ReCyf-NIS2_ISO.csv"
OUTPUT_PATH = "recyf_to_iso27001_mapping.xlsx"


def normalize_header(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_source_node_id(reference: str) -> str:
    if not reference:
        return ""
    return str(reference).strip().split("-", 1)[0]


def parse_target_node_id(iso_ref: str) -> str:
    if not iso_ref:
        return ""

    text = str(iso_ref).strip()
    match = re.match(r"2700(1|2):2022-([0-9]+(?:\.[0-9]+)+)", text)

    if not match:
        return ""

    standard = match.group(1)
    control = match.group(2)

    return control if standard == "1" else f"A.{control}"


def map_relationship_and_strength(correspondance: str):
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

    iso_columns = [h for h in headers if h.startswith("Référence ISO")]

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

        for col in iso_columns:
            iso_ref = row[col_idx[col]]
            target_node_id = parse_target_node_id(iso_ref)

            if not target_node_id:
                continue

            mapping = (source_node_id, target_node_id, relationship, strength)

            if mapping in seen:
                continue

            seen.add(mapping)
            ws.append(list(mapping))

    wb.save(output_path)

    print(f"Created: {output_path}")
    print(f"Mappings: {len(seen)}")


if __name__ == "__main__":
    generate_mapping(INPUT_PATH, OUTPUT_PATH)
