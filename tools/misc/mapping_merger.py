"""
Merge 2 mappings together
Version 0.3

This script merges two Excel mapping files:
- File 1: mapping from A -> B
- File 2: mapping from B -> C

The output is an Excel file that provides a merged A -> C mapping.

Input Parameters:
-----------------
- File 1: Path to the Excel file containing the A -> B mapping
- File 2: Path to the Excel file containing the B -> C mapping
- [Optional] Output file name (default: "merged_output.xlsx")

Sheet Names to Edit:
--------------------
- A_TO_B_MAPPING_TAB_NAME: name of the sheet in File 1 (default: "mappings_content")
- B_TO_C_MAPPING_TAB_NAME: name of the sheet in File 2 (default: "mappings")

Output:
-------
The generated Excel file contains three sheets:
1. "info": metadata about the merge operation (version, source filenames, etc.)
2. "merged": the resulting A -> C mapping table
3. "warning": optional sheet listing unmatched mappings from B to C

Features:
---------
- Ensures selected sheets exist; fails gracefully if not.
- Trims column names to avoid whitespace mismatches.
- Automatically fills in missing columns (relationship, rationale).
- Removes duplicates and rows with no C match.
- Detects and logs any unmatched B nodes (target_node_id_x with no corresponding C).
- Displays warnings in both console and the "warning" sheet of the output file.
- Output is safe for analysis, but not directly usable in "prepare_mapping.py".

Usage:
------
    python merge_mappings.py <file1.xlsx> <file2.xlsx> [output.xlsx]

Tested with v1 and v2 mapping files.
"""


A_TO_B_MAPPING_TAB_NAME = "mappings_content"
B_TO_C_MAPPING_TAB_NAME = "mappings"


import pandas as pd
import sys
import os
from openpyxl.styles import Font
from openpyxl import Workbook

SCRIPT_VERSION = '0.3'

# Validate arguments
if len(sys.argv) < 3 or len(sys.argv) > 4:
    print("Usage: python merge_mappings.py <a_to_b.xlsx> <b_to_c.xlsx> [output.xlsx]")
    sys.exit(1)

file1_path = sys.argv[1]
file2_path = sys.argv[2]
output_path = sys.argv[3] if len(sys.argv) == 4 else "merged_output.xlsx"

# Check and open Excel files safely
try:
    excel1 = pd.ExcelFile(file1_path)
except Exception as e:
    print(f"❌ [ERROR] Could not open input file 1: \"{file1_path}\".\nDetails: {e}")
    sys.exit(1)

try:
    excel2 = pd.ExcelFile(file2_path)
except Exception as e:
    print(f"❌ [ERROR] Could not open input file 2: \"{file2_path}\".\nDetails: {e}")
    sys.exit(1)

# Check if required sheets exist
if A_TO_B_MAPPING_TAB_NAME not in excel1.sheet_names:
    print(f"❌ [ERROR] Sheet \"{A_TO_B_MAPPING_TAB_NAME}\" not found in \"{file1_path}\"")
    sys.exit(1)

if B_TO_C_MAPPING_TAB_NAME not in excel2.sheet_names:
    print(f"❌ [ERROR] Sheet \"{B_TO_C_MAPPING_TAB_NAME}\" not found in \"{file2_path}\"")
    sys.exit(1)


# Load and clean file 1 (A -> B)
df1 = excel1.parse(sheet_name=A_TO_B_MAPPING_TAB_NAME)
df1.columns = df1.columns.str.strip()

# Load and clean file 2 (B -> C)
df2 = excel2.parse(sheet_name=B_TO_C_MAPPING_TAB_NAME)
df2.columns = df2.columns.str.strip()

# Merge A -> B -> C
merged_df = df1.merge(
    df2,
    left_on="target_node_id",
    right_on="source_node_id",
    how="left"
)

# Check for unmatched B nodes
unmatched = merged_df[merged_df["target_node_id_y"].isna()]
if not unmatched.empty:
    unmatched_ids = unmatched["target_node_id_x"].dropna().unique()
    print("⚠️  [WARNING] The following target_node_id values from file 1 (A to B) had no match in file 2 (B to C):")
    for val in unmatched_ids:
        print(f"   - {val}")

# Ensure relationship and rationale columns exist
for col in ["relationship_y", "rationale_y"]:
    if col not in merged_df.columns:
        merged_df[col] = ""

# Select and rename final columns
merged_df = merged_df[[
    "source_node_id_x",      # A
    "target_node_id_y",      # C
    "relationship_y",
    "rationale_y"
]]

# Rename columns for clarity
merged_df.columns = [
    "source_node_id",        # A
    "target_node_id",        # C
    "relationship",
    "rationale"
]

# Remove duplicate rows
merged_df = merged_df.drop_duplicates()

# Drop rows with no match to C
merged_df = merged_df.dropna(subset=["target_node_id"])

# Fill blanks in optional fields
merged_df["relationship"] = merged_df["relationship"].fillna("")
merged_df["rationale"] = merged_df["rationale"].fillna("")

try:
    # Open Excel writer context
    with pd.ExcelWriter(output_path, engine="openpyxl", mode="w") as writer:
        # Write merged data
        merged_df.to_excel(writer, sheet_name="merged", index=False)

        # Prepare info sheet
        wb: Workbook = writer.book
        ws_info = wb.create_sheet("info", 0)

        file_a = os.path.basename(file1_path)
        file_b = os.path.basename(file2_path)

        ws_info["A1"] = "Mapping Merger v" + SCRIPT_VERSION
        ws_info["A1"].font = Font(size=48, bold=True)

        ws_info["A2"] = "File A → B : " + file_a
        ws_info["A2"].font = Font(size=15)
        ws_info["A3"] = f"Sheet used (A → B) : {A_TO_B_MAPPING_TAB_NAME}"
        ws_info["A3"].font = Font(size=15)

        ws_info["A4"] = "File B → C : " + file_b
        ws_info["A4"].font = Font(size=15)
        ws_info["A5"] = f"Sheet used (B → C) : {B_TO_C_MAPPING_TAB_NAME}"
        ws_info["A5"].font = Font(size=15)

        ws_info["A6"] = "Please note that this Excel file doesn't replace the one generated by prepare_mapping.py."
        ws_info["A6"].font = Font(size=20, italic=True)

        # Add warning sheet if needed
        if not unmatched.empty:
            warning_df = unmatched[["source_node_id_x", "target_node_id_x"]].copy()
            warning_df.columns = ["source_node_id", "unmatched_target_node_id"]
            warning_df["reason"] = "No corresponding B → C mapping found"
            warning_df.to_excel(writer, sheet_name="warning", index=False)

except Exception as e:
    print(f"❌ [ERROR] Could not write output Excel file \"{output_path}\".\nDetails: {e}")
    print("💡 Tip: Make sure the file is not open in Excel or locked by another process.")
    sys.exit(1)

print(f"✅ Output written to \"{output_path}\"")

# Console summary for unmatched mappings
if not unmatched.empty:
    print(f"⚠️  [WARNING] {len(unmatched)} mapping{'s' if len(unmatched)>1 else ''} could not be done and were written to the \"warning\" sheet.")
