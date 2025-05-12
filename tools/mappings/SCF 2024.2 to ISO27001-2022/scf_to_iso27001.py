import pandas as pd
import re

# Charger la feuille "SCF 2024.2", ignorer la première ligne
df = pd.read_excel("Secure.Controls.Framework.SCF.-.2024.2.xlsx", sheet_name="SCF 2024.2", skiprows=1, header=None)

# Initialiser un ensemble pour éviter les doublons
associations_set = set()
associations = []

for index, row in df.iterrows():
    scf_cat = row[2]   # Colonne C
    iso_data = row[40] # Colonne AO

    if pd.isna(scf_cat) or pd.isna(iso_data):
        continue

    scf_cat_clean = str(scf_cat).strip().lower()

    for line in str(iso_data).split("\n"):
        line = line.strip()

        # Supprimer toutes les parenthèses et leur contenu (plusieurs possibles par ligne)
        line_clean = re.sub(r"\s*\([^)]*\)", "", line).strip()

        if line_clean:  # Ne pas traiter les lignes vides
            pair = (scf_cat_clean, line_clean)
            if pair not in associations_set:
                associations.append(pair)
                associations_set.add(pair)

# Créer le DataFrame de sortie
result_df = pd.DataFrame(associations, columns=["SCF 2024.2 Category", "ISO/IEC 27001:2022"])

# Sauvegarder dans un fichier Excel
result_df.to_excel("scf_to_iso27001_cleaned.xlsx", index=False)
