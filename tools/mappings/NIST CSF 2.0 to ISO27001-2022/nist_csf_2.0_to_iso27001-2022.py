import pandas as pd

# Charger la feuille utile en ignorant les 2 premières lignes
df = pd.read_excel("csf2.xlsx", sheet_name="CSF 2.0", skiprows=2, header=None)

# Initialiser la liste des associations NIST CSF 2.0 -> ISO/IEC 27001:2022
associations = []

for index, row in df.iterrows():
    categorie_cell = row[2]  # Colonne C (index 2)
    mapping_cell = row[4]    # Colonne E (index 4)

    if pd.isna(categorie_cell) or pd.isna(mapping_cell):
        continue

    # Extraire la catégorie NIST CSF 2.0 (avant les ":")
    if ':' not in str(categorie_cell):
        continue
    categorie_nist = str(categorie_cell).split(":")[0].strip().lower()

    for line in str(mapping_cell).split("\n"):
        line = line.strip()
        prefix = "ISO/IEC 27001:2022:"
        if line.startswith(prefix):
            content = line[len(prefix):].strip()

            if content.startswith("Mandatory Clause:"):
                clause = content[len("Mandatory Clause:"):].strip().lower()
                if clause != "none":
                    associations.append((categorie_nist, clause))

            elif content.startswith("Annex A Controls:"):
                control = content[len("Annex A Controls:"):].strip().lower()
                if control != "none":
                    associations.append((categorie_nist, f"a.{control}"))

# Créer le DataFrame final
result_df = pd.DataFrame(associations, columns=["NIST CSF 2.0 Category", "ISO/IEC 27001:2022"])

# Sauvegarder dans un nouveau fichier Excel
result_df.to_excel("nist_to_iso27001.xlsx", index=False)
