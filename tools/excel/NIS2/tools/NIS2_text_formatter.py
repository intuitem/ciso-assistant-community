### TEXT EXTRACTION (WARNING: footnotes in the resulting exported text must be removed manually) ###
# NOTE : The output text will need some modifications in order to work properly with the script.

# import sys
# from pathlib import Path

# parent_dir = Path(__file__).resolve().parent.parent.parent.parent
# sys.path.insert(0, str(parent_dir))

# from misc.simple_pdf_extractor import extract_structured_text

# FILENAME = "NIS2_OJ_L_202402690_EN_TXT"

# extract_structured_text(FILENAME + ".pdf", FILENAME + "_extracted.txt", None, None, False)

### Excel CONVERSION ###
## IMPORTANT NOTE : "depth" column will have incorrect numbering. It's not important here since we only want translation here

import re
import pandas as pd
from openpyxl import Workbook

# Line list to ignore (after strip), for a specific language
IGNORE_PATTERNS_FR = [
    "ELI: http://data.europa.eu/eli/reg_impl/2024/2690/oj",
    "FR",
    "JO L du 18.10.2024",
    "A ADOPTÉ LE PRÉSENT RÈGLEMENT:"
]

# Name of fields in the "name" column, for a specific language
EXCEL_FIELD_NAME_FR = {
    "recitals": "Préambule",
    "recital": "Préambule",
    "article": "Article"
}




IGNORE_PATTERNS_EN = [
    "ELI: http://data.europa.eu/eli/reg_impl/2024/2690/oj",
    "EN",
    "OJ L, 18.10.2024",
    "HAS ADOPTED THIS REGULATION:",
]

EXCEL_FIELD_NAME_EN = {
    "recitals": "Recitals",
    "recital": "Recital",
    "article": "Article"
}




# Select the line list to ignore according to your language 
IGNORE_PATTERNS = IGNORE_PATTERNS_EN

# Select the Excel field name to put in the "name" column 
EXCEL_FIELD_NAME = EXCEL_FIELD_NAME_EN

TEXT_LANGUAGE = "EN"


SOURCE_TEXT_FILE = "NIS2_OJ_L_202402690_EN_TXT_extracted.txt"
TARGET_EXCEL_FILE_NAME = ""

def is_ignored(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    if line in IGNORE_PATTERNS:
        return True
    if re.match(r"^\d+/\d+$", line):  # motif x/y
        return True
    return False

def parse_txt_to_excel(input_file: str, output_file: str):
    rows = []
    current_context = {
        "depth": None,
        "article": None,
        "y": None,
        "z": None,
        "w": None,
        "article_depth": None,
        "y_depth": None,
        "anon_depth": None,  # pour suivre le niveau des points sans numéro
        "previous_letter" : None,
        "in_recital": True   # on commence dans les recitals
    }

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Ajouter la racine Recital
    rows.append({
        "depth": "1",
        "urn_id": "recital",
        "name": EXCEL_FIELD_NAME.get("recitals"),
        "description": ""
    })
    current_context["depth"] = 1

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if is_ignored(line):
            i += 1
            continue

        # Recital (A)
        if re.match(r"^\([0-9]+\)$", line):
            recital_num = line.strip("()")
            desc_lines = []
            i += 1
            while i < len(lines) and not re.search(r"[.:]$", lines[i].strip()):
                if not is_ignored(lines[i]):
                    desc_lines.append(lines[i].strip())
                i += 1
            if i < len(lines):
                desc_lines.append(lines[i].strip())

            rows.append({
                "depth": "2",
                "ref_id": None,
                "name": f"{EXCEL_FIELD_NAME.get("recital")} {recital_num}",
                "urn_id": f"recital-{recital_num}",
                "description": " ".join(desc_lines).strip()
            })
            i += 1
            continue

        # Article (on sort des recitals ici)
        if line.startswith(EXCEL_FIELD_NAME.get("article")):
            current_context["in_recital"] = False
            
            
            regex_to_use = re.escape(EXCEL_FIELD_NAME.get("article")) + r"\s+"
            
            current_context["article"] = re.sub(regex_to_use, "", line)
            
            if TEXT_LANGUAGE == "FR":
                if current_context["article"] in ["premier"]:
                    current_context["article"] = 1
            
            depth = "1"  # maintenant les Articles sont au niveau 1
            desc = ""
            if i + 1 < len(lines):
                desc = lines[i+1].strip()
                i += 1
            rows.append({
                "depth": depth,
                # "ref_id": current_context["article"],
                "urn_id" : f"article-{current_context["article"]}",
                "name": line,
                "description": desc
            })
            current_context["depth"] = int(depth)
            current_context["anon_depth"] = None
            current_context["previous_letter"] = None
            current_context["article_depth"] = depth
            current_context["y_depth"] = None
            current_context["y"] = None
            i += 1
            continue

        # Y. (inchangé)
        if re.match(r"^\d+\.$", line):
            y_num = line.replace(".", "")
            current_context["y"] = y_num
            desc_lines = []
            i += 1
            while i < len(lines) and not re.search(r"[.:]$", lines[i].strip()):
                if not is_ignored(lines[i]):
                    desc_lines.append(lines[i].strip())
                i += 1
            if i < len(lines):
                desc_lines.append(lines[i].strip())
            depth = int(current_context["article_depth"]) + 1
            rows.append({
                "assessable": "x",
                "depth": str(depth),
                "ref_id": f"{current_context['article']}.{y_num}",
                "name": None,
                "description": " ".join(desc_lines).strip()
            })
            current_context["anon_depth"] = None
            current_context["previous_letter"] = None
            current_context["y_depth"] = int(depth)
            i += 1
            continue

        # Z) (inchangé)
        if re.match(r"^\(*[a-z]\)$", line) :
            z_letter = line.replace(")", "").replace("(", "")
            
            if not z_letter.startswith("i") or (z_letter.startswith("i") and current_context["previous_letter"].startswith("h")) :
                if not z_letter.startswith("v") or (z_letter.startswith("v") and current_context["previous_letter"].startswith("u")) :
                    current_context["z"] = z_letter
                    desc_lines = []
                    i += 1
                    while i < len(lines) and not re.search(r"[.:;]$", lines[i].strip()):
                        if not is_ignored(lines[i]):
                            desc_lines.append(lines[i].strip())
                        i += 1
                    if i < len(lines):
                        desc_lines.append(lines[i].strip())
                    depth = (
                        current_context["anon_depth"] + 1 if current_context["anon_depth"] is not None
                        else (
                            current_context["y_depth"] + 1 if current_context["y_depth"] is not None else current_context["article_depth"] + 1
                        )
                    )
                    print(f"ARTICLE : {current_context["article"]} :: ANON_D : {current_context["anon_depth"]} ; Y_DEPTH : {current_context["y_depth"]} ; ARTICLE_D : {current_context["article_depth"]} ; CHOOSEN : {depth}")
                    
                    
                    rows.append({
                        "assessable": "x",
                        "depth": str(depth),
                        "ref_id": f"{current_context['article']}.{current_context['y'] + "." if current_context['y'] is not None else ""}{z_letter}",
                        "name": None,
                        "description": " ".join(desc_lines).strip()
                    })
                    current_context["depth"] = depth
                    current_context["previous_letter"] = z_letter
                    i += 1
                    continue

        # W) (inchangé)
        if re.match(r"^(i|ii|iii|iv|v|vi|vii|viii|ix)\)$", line):
            w_roman = line.replace(")", "")
            current_context["w"] = w_roman
            desc_lines = []
            i += 1
            while i < len(lines) and not re.search(r"[.:;]$", lines[i].strip()):
                if not is_ignored(lines[i]):
                    desc_lines.append(lines[i].strip())
                i += 1
            if i < len(lines):
                desc_lines.append(lines[i].strip())
            
            depth = (current_context["anon_depth"] + 2 if current_context["anon_depth"] is not None else current_context["depth"] + 1)
            
            rows.append({
                "depth": str(depth),
                "ref_id": f"{current_context['article']}.{current_context['y'] + "." if current_context['y'] is not None else ""}{current_context['z']}.{w_roman}",
                "name": None,
                "description": " ".join(desc_lines).strip()
            })
            i += 1
            continue

        # T) (inchangé avec texte sur même ligne)
        if re.match(r"^\d+\)", line.strip()):
            match = re.match(r"^(\d+)\)\s*(.*)$", line.strip())
            if match:
                t_num = match.group(1)
                first_text = match.group(2)
            else:
                t_num = line.replace(")", "")
                first_text = ""

            desc_lines = []
            if first_text:
                desc_lines.append(first_text)

            if not re.search(r"[.:;]$", first_text.strip()):
                i += 1
                while i < len(lines) and not re.search(r"[.:;]$", lines[i].strip()):
                    if not is_ignored(lines[i]):
                        desc_lines.append(lines[i].strip())
                    i += 1
                if i < len(lines):
                    desc_lines.append(lines[i].strip())

            depth = (current_context["anon_depth"] + 2 
                    if current_context["anon_depth"] is not None 
                    else current_context["depth"] + 1)

            rows.append({
                "depth": str(depth),
                "ref_id": f"{current_context['article']}.{current_context['y'] + "." if current_context['y'] is not None else ""}{current_context['z']}.{current_context['w']}.{t_num}",
                "name": None,
                "description": " ".join(desc_lines).strip()
            })
            i += 1
            continue

        # Texte direct (inchangé)
        if line and not is_ignored(line):
            if current_context["anon_depth"]:
                depth = current_context["anon_depth"]
            else:
                depth = current_context["depth"] + 1
                current_context["anon_depth"] = depth

            desc_lines = [line]
            if not re.search(r"[.:;]$", line.strip()):
                i += 1
                while i < len(lines) and not re.search(r"[.:;]$", lines[i].strip()):
                    if not is_ignored(lines[i]):
                        desc_lines.append(lines[i].strip())
                    i += 1
                if i < len(lines):
                    desc_lines.append(lines[i].strip())

            rows.append({
                "assessable": "x",
                "depth": str(depth),
                "ref_id": None,
                "name": None,
                "description": " ".join(desc_lines).strip()
            })
            i += 1
            continue

        i += 1

    df = pd.DataFrame(rows, columns=["assessable", "depth", "ref_id", "name", "urn_id", "description"])
    save_df_as_excel(df, output_file)


def save_df_as_excel(df, output_file, sheet_name="Sheet1"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Write Header
    ws.append(list(df.columns))

    # Write lines with everything ast str
    for _, row in df.iterrows():
        ws.append([str(x) if pd.notna(x) else "" for x in row])

    # Force text format on sheet
    for row in ws.iter_rows():
        for cell in row:
            cell.number_format = "@"

    wb.save(output_file)




if __name__ == "__main__":
    parse_txt_to_excel(SOURCE_TEXT_FILE, (f"destination_{TEXT_LANGUAGE}.xlsx" if not TARGET_EXCEL_FILE_NAME else TARGET_EXCEL_FILE_NAME))
