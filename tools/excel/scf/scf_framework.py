"""
Script to transform a SCF Framework Excel source file into a structured destination file for CISO Assistant.

Input:
    - Excel file with a sheet named "SCF 2025.2.2" (change "sheet_name" value for future updates)
    - Relevant columns:
        * "SCF Domain"
        * "SCF Control"
        * "SCF #"
        * "Secure Controls Framework (SCF)\nControl Description"
        * "SCF Control Question"
        * "SCRM Focus\n\nTIER 1\nSTRATEGIC"
        * "SCRM Focus\n\nTIER 2\nOPERATIONAL"
        * "SCRM Focus\n\nTIER 3\nTACTICAL"

Processing:
    - For each new "SCF Domain", insert a row with depth=1 and the domain name in the name column.
    - For each control, insert a row with:
        * assessable = "x"
        * depth = 2
        * ref_id = "SCF #"
        * name = "SCF Control"
        * description = control description
        * annotation = control question
        * implementation_groups = comma-separated tiers (e.g., "tier1,tier3")

Output:
    - Excel file with a sheet named "scf" and the following columns:
        * assessable
        * depth
        * ref_id
        * name
        * description
        * annotation
        * implementation_groups
"""


from warnings import deprecated
from xml.etree.ElementTree import tostring
import pandas as pd

# File paths (adjust as needed)
source_file = "secure-controls-framework-scf-2025-2-2.xlsx"
destination_file = "scf_framework.xlsx"
sheet_name = "SCF 2025.2.2"

# Columns of interest in the source file
columns_to_use = [
    "SCF Domain",
    "SCF Control",
    "SCF #",
    "Secure Controls Framework (SCF)\nControl Description",
    "SCF Control Question",
    "SCRM Focus\n\nTIER 1\nSTRATEGIC",
    "SCRM Focus\n\nTIER 2\nOPERATIONAL",
    "SCRM Focus\n\nTIER 3\nTACTICAL"
]

# Load the source file
df = pd.read_excel(source_file, sheet_name=sheet_name, usecols=columns_to_use)

# List to store rows for the destination file
rows = []

previous_domain = None

for _, row in df.iterrows():
    current_domain = row["SCF Domain"]
    current_domain = current_domain.strip()

    # If the domain has changed, add a depth=1 row
    if pd.notna(current_domain) and current_domain != previous_domain:
        rows.append({
            "assessable": "",
            "depth": 1,
            "ref_id": str(row.get("SCF #", "")).split("-")[0],
            "name": current_domain,
            "description": "",
            "annotation": "",
            "implementation_groups": ""
        })
        previous_domain = current_domain

    # Determine implementation groups
    tiers = []
    if str(row.get("SCRM Focus\n\nTIER 1\nSTRATEGIC", "")).strip().lower() == "x":
        tiers.append("tier1")
    if str(row.get("SCRM Focus\n\nTIER 2\nOPERATIONAL", "")).strip().lower() == "x":
        tiers.append("tier2")
    if str(row.get("SCRM Focus\n\nTIER 3\nTACTICAL", "")).strip().lower() == "x":
        tiers.append("tier3")
    tier_str = ",".join(tiers)

    # Add a depth=2 row for the control
    is_deprecated = (
        True if str(row.get("Secure Controls Framework (SCF)\nControl Description", ""))
                .strip().lower().startswith("[deprecated")
        else False
    )
    
    rows.append({
        "assessable": ("x" if is_deprecated is False else ""),
        "depth": 2,
        "ref_id": row.get("SCF #", ""),
        "name": row.get("SCF Control", ""),
        "description": row.get("Secure Controls Framework (SCF)\nControl Description", ""),
        "annotation": row.get("SCF Control Question", ""),
        "implementation_groups": tier_str
    })

# Create the final DataFrame
df_result = pd.DataFrame(rows, columns=[
    "assessable", "depth", "ref_id", "name", "description", "annotation", "implementation_groups"
])

# Write to the destination Excel file
with pd.ExcelWriter(destination_file, engine="openpyxl") as writer:
    df_result.to_excel(writer, sheet_name="scf", index=False)

print(f"✅ Destination file created: \"{destination_file}\"")
