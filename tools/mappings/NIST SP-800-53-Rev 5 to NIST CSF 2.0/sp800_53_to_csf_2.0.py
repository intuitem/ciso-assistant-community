import pandas as pd
import re

def clean_sp800_53_id(text):
    """
    Nettoie les zéros inutiles dans les identifiants SP 800-53 Rev 5.
    Exemple : "cp-02(08)" -> "cp-2(8)"
    """
    text = re.sub(r'-0+(\d+)', r'-\1', text)        # ex: cp-02 -> cp-2
    text = re.sub(r'\(0+(\d+)\)', r'(\1)', text)    # ex: (08) -> (8)
    return text

# Charger la feuille "CSF 2.0", ignorer la première ligne
df = pd.read_excel("./Cybersecurity_Framework_v2-0_Concept_Crosswalk_800-53_final.xlsx", sheet_name="Relationships", skiprows=1, header=None)

associations = []

for index, row in df.iterrows():
    csf_category = row[0]  # Colonne C (index 2)
    sp800_53 = row[2]      # Colonne E (index 4)

    if pd.isna(csf_category) or pd.isna(sp800_53):
        continue

    clean_id = clean_sp800_53_id(str(sp800_53).strip())
    associations.append((clean_id.lower(), str(csf_category).strip().lower()))

# Créer le DataFrame de sortie avec colonnes inversées
result_df = pd.DataFrame(associations, columns=["NIST SP-800-53 Rev 5", "NIST CSF 2.0 Category"])

# Sauvegarder dans un fichier Excel
result_df.to_excel("sp800_53_to_csf_2.0.xlsx", index=False)
