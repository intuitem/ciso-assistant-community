#!/usr/bin/env python3
"""
Extract SCF to ISO 27001/27002 mapping from the SCF Excel file.
Retains only rows where at least one of the ISO mappings is present.
"""

import pandas as pd
from pathlib import Path


def extract_scf_mapping(input_file: str, output_file: str):
    """
    Extract specific columns from SCF Excel file and filter rows.

    Args:
        input_file: Path to the input SCF Excel file
        output_file: Path to the output Excel file
    """
    print(f"Reading {input_file}...")

    # Read the Excel file from the 'SCF 2025.3.1' sheet
    # Column letters: B=1, C=2, AT=45, AV=47 (0-indexed)
    df = pd.read_excel(input_file, sheet_name="SCF 2025.3.1")

    print(f"Total rows in file: {len(df)}")
    print(f"Columns in file: {len(df.columns)}")
    print(f"\nFirst few column names:")
    for i, col in enumerate(df.columns[:10]):
        print(f"  Column {i} ({chr(65 + i)}): {col}")

    # Get column names by position (Excel columns B, C, AT, AV)
    # B=1, C=2, AT=45, AV=47 (0-indexed: 1, 2, 45, 47)
    if len(df.columns) >= 48:
        col_b = df.columns[1]  # Column B (index 1)
        col_c = df.columns[2]  # Column C (index 2)
        col_at = df.columns[45]  # Column AT (index 45)
        col_av = df.columns[47]  # Column AV (index 47)

        print(f"\nSelected columns:")
        print(f"  B (index 1): {col_b}")
        print(f"  C (index 2): {col_c}")
        print(f"  AT (index 45): {col_at}")
        print(f"  AV (index 47): {col_av}")

        # Extract the desired columns
        result_df = df[[col_b, col_c, col_at, col_av]].copy()

        # Rename columns for clarity
        result_df.columns = [
            "source_name",
            "source_ref_id",
            "target_iso27001",
            "target_iso27002",
        ]

        # Filter out rows where BOTH ISO columns are empty/NaN
        initial_count = len(result_df)
        result_df = result_df[
            result_df["target_iso27001"].notna() | result_df["target_iso27002"].notna()
        ]
        filtered_count = len(result_df)

        print(f"\nFiltering results:")
        print(f"  Rows before filtering: {initial_count}")
        print(f"  Rows after filtering: {filtered_count}")
        print(f"  Rows removed: {initial_count - filtered_count}")

        # Save to Excel
        print(f"\nSaving to {output_file}...")
        result_df.to_excel(output_file, index=False)

        print(f"\n✓ Successfully created {output_file}")
        print(f"\nFirst 5 rows of output:")
        print(result_df.head())

    else:
        print(f"Error: File has only {len(df.columns)} columns, expected at least 48")
        print("Please verify the file structure.")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_file = script_dir / "secure-controls-framework-scf-2025-3-1.xlsx"
    output_file = script_dir / "scf_iso_mapping.xlsx"

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        exit(1)

    extract_scf_mapping(str(input_file), str(output_file))
