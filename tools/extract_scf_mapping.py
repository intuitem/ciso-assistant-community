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

        # Process ISO 27001 column
        def process_iso27001(cell_value):
            """
            Process ISO 27001 cell:
            - Split by lines
            - Drop anything after '('
            - Remove duplicates
            - Join back with line breaks
            """
            if pd.isna(cell_value):
                return cell_value

            # Split by newlines
            lines = str(cell_value).split("\n")

            # Process each line: strip whitespace and remove content after '('
            processed = []
            for line in lines:
                line = line.strip()
                if line:
                    # Remove anything after '('
                    if "(" in line:
                        line = line.split("(")[0].strip()
                    processed.append(line)

            # Remove duplicates while preserving order
            seen = set()
            unique = []
            for item in processed:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)

            # Join back with newlines
            return "\n".join(unique) if unique else None

        # Process ISO 27002 column
        def process_iso27002(cell_value):
            """
            Process ISO 27002 cell:
            - Split by lines
            - Prefix each with 'A.'
            - Join back with line breaks
            """
            if pd.isna(cell_value):
                return cell_value

            # Split by newlines
            lines = str(cell_value).split("\n")

            # Process each line: strip and prefix with 'A.'
            processed = []
            for line in lines:
                line = line.strip()
                if line:
                    # Add 'A.' prefix if not already present
                    if not line.startswith("A."):
                        line = f"A.{line}"
                    processed.append(line)

            # Join back with newlines
            return "\n".join(processed) if processed else None

        # Apply processing to the columns
        print("\nProcessing ISO 27001 column...")
        result_df["target_iso27001"] = result_df["target_iso27001"].apply(
            process_iso27001
        )

        print("Processing ISO 27002 column...")
        result_df["target_iso27002"] = result_df["target_iso27002"].apply(
            process_iso27002
        )

        # Create combined column 'iso27001-2022'
        def combine_iso_columns(row):
            """
            Combine ISO 27001 and ISO 27002 columns into a single column.
            """
            iso27001_val = row["target_iso27001"]
            iso27002_val = row["target_iso27002"]

            parts = []

            # Add ISO 27001 values if present
            if pd.notna(iso27001_val) and str(iso27001_val).strip():
                parts.append(str(iso27001_val).strip())

            # Add ISO 27002 values if present
            if pd.notna(iso27002_val) and str(iso27002_val).strip():
                parts.append(str(iso27002_val).strip())

            # Join with newline if both are present
            return "\n".join(parts) if parts else None

        print("Creating combined 'iso27001-2022' column...")
        result_df["iso27001-2022"] = result_df.apply(combine_iso_columns, axis=1)

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
