import pandas as pd

# Charger la feuille "Relationships", ignorer la première ligne
df = pd.read_excel("./SSDF_to_CSF_2_0_0_CROSSWALK.xlsx", sheet_name="Relationships", skiprows=1, header=None)

associations = []

for index, row in df.iterrows():
    ssdf = row[0]  # Colonne A (index 0)
    csf = row[2]   # Colonne C (index 2)

    if pd.isna(ssdf) or pd.isna(csf):
        continue

    associations.append((str(csf).strip().lower(), str(ssdf).strip().lower()))

# Créer le DataFrame de sortie
result_df = pd.DataFrame(associations, columns=["NIST SSDF v1.1", "NIST CSF 2.0"])

# Sauvegarder dans un fichier Excel
result_df.to_excel("ssdf_1.1_to_csf_2.0.xlsx", index=False)
