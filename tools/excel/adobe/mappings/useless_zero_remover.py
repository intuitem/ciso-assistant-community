import pandas as pd
import re

def clean_target_node_id(value):
    if pd.isna(value):
        return value
    value = str(value).replace(' ', '-')  # Remplacer les espaces par des tirets
    # Cas avec parenthèses ex: "aa-01 (01)"
    match = re.match(r'^([a-zA-Z]+)-0*(\d+)-?\(0*(\d+)\)$', value)
    if match:
        return f"{match.group(1)}-{int(match.group(2))}-({int(match.group(3))})"
    # Cas sans parenthèse : "aa-01"
    match = re.match(r'^([a-zA-Z]+)-0*(\d+)$', value)
    if match:
        return f"{match.group(1)}-{int(match.group(2))}"
    return value  # Retourner tel quel si non conforme

def process_excel(input_file, output_file):
    df = pd.read_excel(input_file)
    if "target_node_id" in df.columns:
        df["target_node_id"] = df["target_node_id"].apply(clean_target_node_id)
    else:
        print("Colonne 'target_node_id' non trouvée dans le fichier.")
    df.to_excel(output_file, index=False)

# Exemple d'utilisation
input_path = "part2_mapping-adobe-ccf-v5-to-fedramp-rev5.xlsx"
output_path = "FIX_part2_mapping-adobe-ccf-v5-to-fedramp-rev5.xlsx"
process_excel(input_path, output_path)
