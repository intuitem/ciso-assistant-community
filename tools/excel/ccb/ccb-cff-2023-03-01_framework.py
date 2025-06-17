import openpyxl
import re

# Charger le texte
with open("extract.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

data = []
i = 0
n = len(lines)

seen_second_headers = set()
seen_third_headers_per_second = dict()
current_second_header = None
current_third_header = None

def is_reference_line(line):
    return bool(re.match(r'^[A-Z]{2}\.[A-Z]{2}-\d+', line.strip()))

def format_annotation(text):
    text = re.sub(r'•', r'\n•', text)
    text = re.sub(r'\bo ', r'\n\to ', text)
    return text.strip()

def process_paragraph_and_annotation_block(i):
    paragraph_lines = []
    while i < n and lines[i].strip() and not lines[i].strip().startswith("Richtlijnen") and not lines[i].strip().startswith("Referenties") and not is_reference_line(lines[i]) and not lines[i].strip().startswith("--- Page "):
        paragraph_lines.append(lines[i].strip())
        i += 1

    if not paragraph_lines:
        return i, None

    entry = {"name": "", "description": " ".join(paragraph_lines), "annotation": ""}

    if i < n and lines[i].strip().startswith("Richtlijnen"):
        i += 1
        annotation_lines = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith("--- Page "):
            annotation_lines.append(lines[i].strip())
            i += 1
        entry["annotation"] = format_annotation(" ".join(annotation_lines))
        if i < n and not lines[i].strip():
            i += 1

    return i, entry

while i < n:
    line = lines[i].strip()

    if line.startswith("--- Page "):
        i += 1
        if i + 2 < n:
            header1 = lines[i].strip()
            header2 = lines[i+1].strip()

            header3_lines = [lines[i+2].strip()]
            i += 3
            while i < n and not header3_lines[-1].endswith(")") and lines[i].strip() != "":
                header3_lines.append(lines[i].strip())
                i += 1
            header3 = " ".join(header3_lines).strip()

            if header2 != current_second_header:
                current_second_header = header2
                seen_second_headers.add(header2)
                seen_third_headers_per_second[header2] = set()
                data.append({"name": header2.upper(), "description": "", "annotation": ""})

            if header3 not in seen_third_headers_per_second[current_second_header]:
                # 🔽 Stocke temporairement l'entrée
                temp_entry = {"name": header3, "description": "", "annotation": ""}
                seen_third_headers_per_second[current_second_header].add(header3)
                current_third_header = header3
            else:
                current_third_header = None
                temp_entry = None

            # Gérer "ESSENTIEEL"
            if i < n and lines[i].strip().upper() == "ESSENTIEEL":
                i += 1

            # 🔽 Récupérer paragraphe qui suit ESSENTIEEL pour l’ajouter à l’entrée précédente
            if temp_entry:
                paragraph_lines = []
                while i < n and lines[i].strip() and not lines[i].strip().startswith("Richtlijnen") and not is_reference_line(lines[i]) and not lines[i].strip().startswith("--- Page "):
                    paragraph_lines.append(lines[i].strip())
                    i += 1
                temp_entry["description"] = " ".join(paragraph_lines)
                data.append(temp_entry)

    # 🔁 Traiter tous les blocs paragraphes + Richtlijnen tant qu'on ne tombe pas sur une référence
    while i < n:
        line = lines[i].strip()
        if line.startswith("--- Page "):
            break
        if is_reference_line(line):
            break
        if line.startswith("Referenties"):
            while i < n and lines[i].strip():
                i += 1
            i += 1
            continue
        i, entry = process_paragraph_and_annotation_block(i)
        if entry:
            data.append(entry)
        else:
            i += 1

    # 🔁 Si on tombe sur une ligne de référence
    if i < n and is_reference_line(lines[i]):
        ref_line = lines[i].strip()
        paragraph_lines = [ref_line]
        i += 1
        while i < n and not paragraph_lines[-1].endswith("."):
            paragraph_lines.append(lines[i].strip())
            i += 1
        description = " ".join(paragraph_lines)
        data.append({"name": "", "description": description, "annotation": ""})

        # 🔁 Traitement paragraphes + annotations suivant la référence
        while i < n:
            line = lines[i].strip()
            if line.startswith("--- Page ") or is_reference_line(line):
                break
            if line.startswith("Referenties"):
                while i < n and lines[i].strip():
                    i += 1
                i += 1
                continue
            i, entry = process_paragraph_and_annotation_block(i)
            if entry:
                data.append(entry)
            else:
                i += 1

# Sauvegarde Excel
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "ccf"
ws.append(["name", "description", "annotation"])
for row in data:
    ws.append([row["name"], row["description"], row["annotation"]])
wb.save("converted.xlsx")
