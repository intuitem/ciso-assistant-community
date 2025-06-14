"""
Simple script to export a mapping from the Adobe CCF v5 PDF

Simply change the "target_column_name" variable to the column name you want in the original Excel file (e.g. SOC 2 Ref#).
You can also modify the "destination_file" variable to make the file name more consistent.
"""

import pandas as pd

# === Configurable parameters ===
source_file = "Open_Source_CCF.xlsx"
destination_file = "part_mapping_adobe-ccf-v5_to_soc2.xlsx"  # <--- You can change this
source_sheet = "CCF Open Source v5"
destination_sheet = "mappings"
target_column_name = "SOC 2 Ref#"   # <--- You can change this

# Load the Excel sheet (header is row 2, i.e., index 1)
df = pd.read_excel(source_file, sheet_name=source_sheet, header=1)

# Prepare result rows
results = []

for _, row in df.iterrows():
    ccf_id = str(row.get("CCF ID", "")).strip().lower()
    soc2_raw = row.get(target_column_name, "")

    # Skip empty SOC 2 references
    if pd.isna(soc2_raw) or not str(soc2_raw).strip():
        continue

    # Split on line breaks and clean
    refs = [str(ref).strip().lower() for ref in str(soc2_raw).splitlines() if str(ref).strip()]
    
    for ref in refs:
        results.append({
            "source_node_id": str(ccf_id),
            "target_node_id": str(ref)
        })

# Create DataFrame and force string type
df_result = pd.DataFrame(results, dtype=str)

# Export to Excel
with pd.ExcelWriter(destination_file, engine="openpyxl") as writer:
    df_result.to_excel(writer, sheet_name=destination_sheet, index=False)

print(f"✅ Conversion complete: \"{destination_file}\"")
