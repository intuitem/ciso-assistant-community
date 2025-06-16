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
current_name = None

def is_reference_line(line):
    return bool(re.match(r'^[A-Z]{2}\.[A-Z]{2}-\d+', line.strip()))

def format_annotation(text):
    # Ajoute un retour à la ligne avant chaque •
    text = re.sub(r'•', r'\n•', text)
    # Ajoute un retour à la ligne + tabulation avant chaque o (sous-point)
    text = re.sub(r'\bo ', r'\n\to ', text)
    return text.strip()

while i < n:
    line = lines[i].strip()

    if line.startswith("--- Page "):
        i += 1
        if i + 2 < n:
            header1 = lines[i].strip()
            header2 = lines[i+1].strip()

            # Lire la 3ème ligne (qui peut être sur plusieurs lignes jusqu'à un ")")
            header3_lines = [lines[i+2].strip()]
            i += 3
            while i < n and not header3_lines[-1].endswith(")") and lines[i].strip() != "":
                header3_lines.append(lines[i].strip())
                i += 1
            header3 = " ".join(header3_lines).strip()

            # Ajouter header2 s'il est nouveau
            if header2 not in seen_second_headers:
                data.append({"name": header2.upper(), "description": "", "annotation": ""})
                seen_second_headers.add(header2)
                seen_third_headers_per_second[header2] = set()

            # Ajouter header3 s'il est nouveau dans ce contexte de header2
            if header3 not in seen_third_headers_per_second[header2]:
                data.append({"name": header3, "description": "", "annotation": ""})
                seen_third_headers_per_second[header2].add(header3)
                current_name = header3
            else:
                current_name = None

            if i < n and lines[i].strip().upper() == "ESSENTIEEL":
                i += 1
        continue

    elif current_name:
        paragraph_lines = []
        while i < n and lines[i].strip() and not is_reference_line(lines[i]):
            paragraph_lines.append(lines[i].strip())
            i += 1
        description = " ".join(paragraph_lines).strip()
        for row in reversed(data):
            if row["name"] == current_name:
                row["description"] = description
                break
        current_name = None
        continue

    elif is_reference_line(line):
        # Bloc commençant par une référence de style AA.AA-B
        ref_line = line
        paragraph_lines = [ref_line]
        i += 1

        # Continuer à collecter tant que le dernier mot ne se termine pas par "."
        while i < n and not paragraph_lines[-1].strip().endswith("."):
            paragraph_lines.append(lines[i].strip())
            i += 1
        if i < n and not paragraph_lines[-1].strip().endswith("."):
            paragraph_lines.append(lines[i].strip())
            i += 1

        description = " ".join(paragraph_lines).strip()
        data.append({"name": "", "description": description, "annotation": ""})

        # 2e paragraphe
        paragraph_lines = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith("Richtlijnen") and not lines[i].strip().startswith("Referenties"):
            paragraph_lines.append(lines[i].strip())
            i += 1
        if paragraph_lines:
            data.append({"name": "", "description": " ".join(paragraph_lines), "annotation": ""})

        # Annotation Richtlijnen
        if i < n and lines[i].strip().startswith("Richtlijnen"):
            i += 1
            annotation_lines = []
            while i < n and lines[i].strip():
                annotation_lines.append(lines[i].strip())
                i += 1
            if annotation_lines:
                formatted = format_annotation(" ".join(annotation_lines))
                data[-1]["annotation"] = formatted
            i += 1  # Sauter ligne vide

        # Skip Referenties
        while i < n and lines[i].strip().startswith("Referenties"):
            i += 1
        while i < n and lines[i].strip():
            i += 1
        i += 1
        continue

    else:
        i += 1

# Export vers Excel
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "ccf"
ws.append(["name", "description", "annotation"])
for row in data:
    ws.append([row["name"], row["description"], row["annotation"]])

wb.save("converted.xlsx")
print("✅ Fichier Excel 'converted.xlsx' généré avec succès.")
