### TEXT EXTRACTION (WARNING: footnotes in the resulting exported text must be removed manually) ###

# import sys
# from pathlib import Path

# parent_dir = Path(__file__).resolve().parent.parent.parent.parent
# sys.path.insert(0, str(parent_dir))

# from misc.simple_pdf_extractor import extract_structured_text

# FILENAME = "RTS-DORA-ICT-risk-management_OJ_L_202401774_FR_TXT"

# extract_structured_text(FILENAME + ".pdf", FILENAME + "_extracted.txt", 6, None, False)

### Excel CONVERSION ###
### IMPORTANT NOTE : "depth" column will have incorrect numbering. It's not important here since we only want translation here

import re
import pandas as pd

# Liste des lignes à ignorer (après strip)
IGNORE_PATTERNS = [
    "ELI: http://data.europa.eu/eli/reg_del/2024/1774/oj",
    "FR",
    "JO L du 25.6.2024"
]

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
    debug_val = True
    nbr = 3
    rows = []
    current_context = {
        "depth": None,
        "article": None,
        "y": None,
        "z": None,
        "w": None,
        "article_depth": None,
        "y_depth": None,
        "in_a_chapter" : False,
        "section_depth": None,
        "anon_depth": None,  # pour suivre le niveau des points sans numéro
        "previous_letter" : None
    }

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if is_ignored(line):
            i += 1
            continue

        # TITRE
        if line.startswith("TITRE"):
            desc_lines = []
            i += 1
            while i < len(lines) and not re.match(r"^(TITRE|CHAPITRE|Section|Article)", lines[i].strip()):
                if not is_ignored(lines[i]):
                    desc_lines.append(lines[i].strip())
                i += 1
            rows.append({
                "depth": "1",
                "ref_id": line,
                "name": line,
                "description": " ".join(desc_lines).strip()
            })
            current_context["depth"] = 1
            current_context["in_a_chapter"] = False
            continue

        # CHAPITRE
        if line.startswith("CHAPITRE"):
            desc_lines = []
            i += 1
            while i < len(lines) and not re.match(r"^(TITRE|CHAPITRE|Section|Article)", lines[i].strip()):
                if not is_ignored(lines[i]):
                    desc_lines.append(lines[i].strip())
                i += 1
            rows.append({
                "depth": "2",
                "ref_id": line,
                "name": line,
                "description": " ".join(desc_lines).strip()
            })
            current_context["depth"] = 2
            current_context["in_a_chapter"] = True
            current_context["section_depth"] = None
            continue

        # Section
        if line.startswith("Section"):
            desc_lines = []
            i += 1
            while i < len(lines) and not re.match(r"^(TITRE|CHAPITRE|Section|Article)", lines[i].strip()):
                if not is_ignored(lines[i]):
                    desc_lines.append(lines[i].strip())
                i += 1
            depth = (3 if current_context["in_a_chapter"] == True else 2)
            rows.append({
                "depth": str(depth),
                "ref_id": line,
                "name": line,
                "description": " ".join(desc_lines).strip()
            })
            current_context["depth"] = depth
            current_context["section_depth"] = depth
            continue

        # Article
        if line.startswith("Article"):
            current_context["article"] = re.sub(r"Article\s+", "", line)
            depth = str((current_context["section_depth"] or current_context["depth"]) + 1)
            desc = ""
            if i + 1 < len(lines):
                desc = lines[i+1].strip()
                i += 1
            rows.append({
                "depth": depth,
                "ref_id": line,
                "name": line,
                "description": desc
            })
            current_context["depth"] = int(depth)
            current_context["anon_depth"] = None  # reset des points sans numéro
            current_context["previous_letter"] = None
            current_context["article_depth"] = depth
            current_context["y_depth"] = None
            current_context["y"] = None
            i += 1
            continue

        # Y. (numérique)
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
            rows.append({
                "depth": str(current_context["depth"] + 1),
                "ref_id": f"{current_context['article']}.{y_num}",
                "name": None,
                "description": " ".join(desc_lines).strip()
            })
            current_context["anon_depth"] = None
            current_context["previous_letter"] = None
            current_context["y_depth"] = int(depth)
            i += 1
            continue

        # Z) (lettre)
        if re.match(r"^[a-z]\)$", line) :
            z_letter = line.replace(")", "")
            
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
                    
                    rows.append({
                        "depth": str(depth),
                        "ref_id": f"{current_context['article']}.{current_context['y'] + "." if current_context['y'] is not None else ""}{z_letter}",
                        "name": None,
                        "description": " ".join(desc_lines).strip()
                    })
                    current_context["depth"] = depth
                    current_context["previous_letter"] = z_letter
                    i += 1
                    continue

        # W) (romain minuscule)
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

        # T) (numérique)
        if re.match(r"^\d+\)", line.strip()):
            # Extraire le numéro avant la parenthèse
            match = re.match(r"^(\d+)\)\s*(.*)$", line.strip())
            if match:
                t_num = match.group(1)
                first_text = match.group(2)  # texte après le numéro sur la même ligne
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

        
        # Nouveau cas : ligne avec texte direct (point sans numéro)
        if line and not is_ignored(line):
            # si on a déjà rencontré un point sans numéro, garder le même niveau
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
                "depth": str(depth),
                "ref_id": None,
                "name": None,
                "description": " ".join(desc_lines).strip()
            })
            i += 1
            continue

        i += 1

    df = pd.DataFrame(rows, columns=["depth", "ref_id", "name", "description"])
    df.to_excel(output_file, index=False)

if __name__ == "__main__":
    parse_txt_to_excel('./RTS-DORA-ICT-risk-management_OJ_L_202401774_FR_TXT_extracted.txt', "destination.xlsx")
