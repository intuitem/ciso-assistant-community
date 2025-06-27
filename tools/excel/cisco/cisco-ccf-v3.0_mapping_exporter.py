"""
Simple script to export a mapping from the Cisco CCF v3 Excel

Simply change the "target_column_names" list to the column names you want in the original Excel file (e.g. SOC 2 Ref#).
You can also modify the "destination_file" variable to make the file name more consistent.
"""

import pandas as pd
import re  # <-- Needed for splitting by both \n and ,

# === Configurable parameters ===
source_file = "Cisco-CCFv3-Public_INFO.xlsx"
destination_file = "part_mapping.xlsx"  # <--- You can change this
source_sheet = "CCF V3"
destination_sheet = "mappings"
target_column_names = ["SOC TSC Common Criteria 2022", "SOC TSC Availability 2022", "SOC TSC Confidentiality 2022"]  # <--- You can add more columns here
rows_to_ignore = [6, 367]  # 1-based row indices to ignore

# Load the Excel sheet (header is row 5, i.e., index 4)
df = pd.read_excel(source_file, sheet_name=source_sheet, header=4)

# Drop ignored rows (convert to 0-based index)
df = df.drop(index=[i - 1 for i in rows_to_ignore], errors="ignore")

# Prepare result rows
results = []
seen_pairs = set()  # <-- Track unique (source_node_id, target_node_id) pairs

for column_name in target_column_names:
    first_entry = True  # Track first entry for this column
    for _, row in df.iterrows():
        ccf_id = str(row.get("Control Reference", "")).strip().lower().replace(" ", "-")
        soc2_raw = row.get(column_name, "")

        # Skip empty target references
        if pd.isna(soc2_raw) or not str(soc2_raw).strip():
            continue

        # Split on both newlines and commas, then clean
        refs = [str(ref).strip().lower() for ref in re.split(r'[\n,]+', str(soc2_raw)) if str(ref).strip()]

        for i, ref in enumerate(refs):
            pair = (ccf_id, ref)
            if pair in seen_pairs:
                continue  # Skip duplicates
            seen_pairs.add(pair)

            row_data = {
                "source_node_id": str(ccf_id),
                "target_node_id": str(ref)
            }
            if first_entry:
                row_data["Col Name"] = column_name
                first_entry = False
            results.append(row_data)

# Create DataFrame and force string type
df_result = pd.DataFrame(results, dtype=str)

# Export to Excel
with pd.ExcelWriter(destination_file, engine="openpyxl") as writer:
    df_result.to_excel(writer, sheet_name=destination_sheet, index=False)

print(f"✅ Conversion complete: \"{destination_file}\"")
