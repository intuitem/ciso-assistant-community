import pandas as pd

# Charger la feuille "Relationships", ignorer la première ligne
df = pd.read_excel("./SP_800_171_Rev2_to_SP_800_171_Rev3_CROSSWALK.xlsx", sheet_name="Relationships", skiprows=1, header=None)

associations = []

for index, row in df.iterrows():
    nist171r3 = row[0]  # Colonne A (index 0)
    nist171r2 = row[2]  # Colonne C (index 2)

    if pd.isna(nist171r3) or pd.isna(nist171r2):
        continue

    associations.append((str(nist171r3).strip(), str(nist171r2).strip()))

# Créer le DataFrame de sortie
result_df = pd.DataFrame(associations, columns=["NIST SP-800-171 Rev 3", "NIST SP-800-171 Rev 2"])

# Sauvegarder dans un fichier Excel
result_df.to_excel("nist_171_rev3_to_rev2.xlsx", index=False)
