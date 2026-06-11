import pandas as pd
import re
import sys

INPUT_FILE = "Excel d'origine.xlsx"
OUTPUT_FILE = "Excel_version1_generated.xlsx"

GROUPS = ["AS-WP", "AS-MS", "AS-AP", "AS-RP", "EW-PIO", "EW-DM"]

FINAL_COLUMNS = [
    "Assessable",
    "Depth",
    "ref_ID",
    "Implementation Group",
    "Name",
    "Description",
    "Annotation",
]

# ======================
# UTILS
# ======================

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def is_assessable(ref_id, desc):
    ref_id = clean(ref_id)
    desc = clean(desc)

    if ref_id.startswith("AS-MS"):
        return False
    if desc in ["Empty", "Empty."]:
        return False
    return True

def get_impl_group(ref_id):
    ref_id = clean(ref_id)
    for g in GROUPS:
        if ref_id.startswith(g):
            return g
    return ""

def build_annotation(notes, index):
    notes = clean(notes)
    index = clean(index)

    if notes and index:
        return f"{notes} | Legacy ref-id: {index}"
    if notes:
        return notes
    if index:
        return f"Legacy ref-id: {index}"
    return ""

def topic_name(topic):
    return clean(topic)

def parse_subsection(text):
    text = clean(text)

    if not text:
        return None, None

    # A. Governance
    m1 = re.match(r"^([A-Z])\.\s*(.*)$", text)
    if m1:
        return m1.group(1), text

    # Method D: ...
    m2 = re.match(r"^(Method\s+([A-Z]))\s*:", text, re.IGNORECASE)
    if m2:
        return f"Method {m2.group(2).upper()}", text

    return None, None

# ======================
# LOAD
# ======================

try:
    df = pd.read_excel(INPUT_FILE)
except Exception as e:
    print("❌ Erreur lecture fichier :", e)
    sys.exit(1)

print("Colonnes détectées :", list(df.columns))

required = [
    "Harmonized_ID",
    "Topic",
    "Subsection",
    "Requirement_specification",
    "Notes",
    "Index",
]

for col in required:
    if col not in df.columns:
        print(f"❌ Colonne manquante : {col}")
        sys.exit(1)

# ======================
# PHASE 1 : STRUCTURE
# ======================

topics = []
topic_map = {}

for _, row in df.iterrows():

    ref_id = clean(row["Harmonized_ID"])
    topic = clean(row["Topic"])
    subsection = clean(row["Subsection"])
    desc = clean(row["Requirement_specification"])
    notes = clean(row["Notes"])
    index = clean(row["Index"])

    assessable = is_assessable(ref_id, desc)

    topic_key = topic if topic else "NO_TOPIC"

    if topic_key not in topic_map:
        t = {
            "name": topic_name(topic),
            "subsections": {},
            "subsection_order": [],
            "requirements": []
        }
        topic_map[topic_key] = t
        topics.append(t)

    current_topic = topic_map[topic_key]

    req = {
        "ref_id": ref_id,
        "desc": desc,
        "notes": notes,
        "index": index,
        "assessable": assessable
    }

    sub_key, sub_name = parse_subsection(subsection)

    if sub_key:
        if sub_key not in current_topic["subsections"]:
            current_topic["subsections"][sub_key] = {
                "name": sub_name,
                "requirements": []
            }
            current_topic["subsection_order"].append(sub_key)

        current_topic["subsections"][sub_key]["requirements"].append(req)
    else:
        current_topic["requirements"].append(req)

# ======================
# PHASE 2 : OUTPUT
# ======================

rows = []
topic_counter = 0

for topic in topics:

    topic_counter += 1
    topic_id = f"A.2.3.{topic_counter}"

    # TOPIC
    rows.append({
        "Assessable": "",
        "Depth": 1,
        "ref_ID": topic_id,
        "Implementation Group": "",
        "Name": topic["name"],
        "Description": "",
        "Annotation": ""
    })

    # REQUIREMENTS sans subsection (avant)
    for r in topic["requirements"]:
        rows.append({
            "Assessable": "x" if r["assessable"] else "",
            "Depth": 3,
            "ref_ID": r["ref_id"],
            "Implementation Group": get_impl_group(r["ref_id"]),
            "Name": "",
            "Description": r["desc"],
            "Annotation": build_annotation(r["notes"], r["index"])
        })

    # SUBSECTIONS
    for sub_key in topic["subsection_order"]:
        sub = topic["subsections"][sub_key]
        sub_id = f"{topic_id}.{sub_key}"

        rows.append({
            "Assessable": "",
            "Depth": 2,
            "ref_ID": sub_id,
            "Implementation Group": "",
            "Name": sub["name"],
            "Description": "",
            "Annotation": ""
        })

        for r in sub["requirements"]:
            rows.append({
                "Assessable": "x" if r["assessable"] else "",
                "Depth": 3,
                "ref_ID": r["ref_id"],
                "Implementation Group": get_impl_group(r["ref_id"]),
                "Name": "",
                "Description": r["desc"],
                "Annotation": build_annotation(r["notes"], r["index"])
            })

# ======================
# SAVE
# ======================

df_out = pd.DataFrame(rows, columns=FINAL_COLUMNS)

try:
    df_out.to_excel(OUTPUT_FILE, index=False)
except Exception as e:
    print("❌ Erreur écriture :", e)
    sys.exit(1)

print("✅ Fichier généré :", OUTPUT_FILE)
print("📊 Topics :", topic_counter)
print("📊 Lignes :", len(df_out))
def parse_subsection(text):
    text = clean(text)

    if not text:
        return None, None

    # CAS 1 : Method D: → on garde tel quel
    m_method = re.match(r"^(Method\s+([A-Z]))\s*:", text, re.IGNORECASE)
    if m_method:
        key = f"Method {m_method.group(2).upper()}"
        return key, text

    # CAS 2 : A. Governance → on enlève "A."
    m_letter = re.match(r"^([A-Z])\.\s*(.*)$", text)
    if m_letter:
        key = m_letter.group(1)
        clean_name = m_letter.group(2).strip()  # 🔥 suppression du "A."
        return key, clean_name

    return None, None
def parse_subsection(text):
    text = clean(text)

    if not text:
        return None, None

    # ===== CAS METHOD =====
    m_method = re.match(r"^(Method\s+([A-Z]))\s*:", text, re.IGNORECASE)
    if m_method:
        key = f"Method {m_method.group(2).upper()}"
        return key, text

    # ===== CAS LETTRE (A. / B. / C. / E. etc.) =====
    m_letter = re.match(r"^\s*([A-Z])\.\s*(.+)$", text)
    if m_letter:
        key = m_letter.group(1)
        clean_name = m_letter.group(2).strip()
        return key, clean_name

    return None, None
def parse_subsection(text):
    text = clean(text)

    if not text:
        return None, None

    # ===== CAS METHOD =====
    if text.lower().startswith("method"):
        m = re.match(r"(Method\s+([A-Z]))", text, re.IGNORECASE)
        if m:
            key = f"Method {m.group(2).upper()}"
            return key, text  # on garde le texte complet

    # ===== CAS LETTRE (ultra robuste) =====
    # Ex: "E. Wallet ..." / " E. Wallet ..." / "E.Wallet ..."
    m = re.match(r"\s*([A-Z])\.\s*(.*)", text)
    if m:
        key = m.group(1)
        clean_name = m.group(2).strip()
        return key, clean_name

    return None, None

def parse_subsection(text):
    text = clean(text)

    if not text:
        return None, None

    # ===== CAS METHOD =====
    if text.lower().startswith("method"):
        m = re.match(r"(Method\s+([A-Z]))", text, re.IGNORECASE)
        if m:
            key = f"Method {m.group(2).upper()}"
            return key, text  # on garde tout
        return None, text

    # ===== CAS LETTRE (A. B. C. D. etc.) =====
    # Supprime systématiquement "X." au début
    m = re.match(r"\s*([A-Z])\.\s*(.+)", text)
    if m:
        key = m.group(1)
        clean_name = m.group(2).strip()

        # 🔥 DOUBLE SÉCURITÉ : si jamais il reste encore "X." → on nettoie encore
        clean_name = re.sub(r"^[A-Z]\.\s*", "", clean_name)

        return key, clean_name

    return None, None
