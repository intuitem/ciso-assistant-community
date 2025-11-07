#!/usr/bin/env python3
"""
Convert PDIS Excel framework to intermediate format.

This script reads the PDIS framework Excel file and converts it to an intermediate
format that can be processed by other tools.
"""

import pandas as pd
import sys
from pathlib import Path


def count_dots(text):
    """Count the number of dots in a string."""
    if pd.isna(text) or text == "":
        return 0
    return str(text).count(".")


def convert_pdis_excel(input_file, output_file=None):
    """
    Convert PDIS Excel file to intermediate format.

    Args:
        input_file: Path to input Excel file
        output_file: Path to output Excel file (optional, defaults to input_intermediate.xlsx)
    """
    # Read the Excel file, starting from row 5 (skiprows=4 to skip rows 0-3)
    df = pd.read_excel(
        input_file,
        sheet_name="I-Etude-documentaire",
        header=None,  # No header row, we'll handle columns manually
        skiprows=4,  # Skip rows 0-4 (rows 1-5 in Excel)
    )

    # Create output dataframe with expected columns
    output_data = []

    for _, row in df.iterrows():
        # Extract values from columns
        col_a = row[0] if not pd.isna(row[0]) else ""  # name (column A = index 0)
        col_c = row[2] if not pd.isna(row[2]) else ""  # ref_id (column C = index 2)
        col_d = (
            row[3] if not pd.isna(row[3]) else ""
        )  # description (column D = index 3)
        col_e = row[4] if not pd.isna(row[4]) else ""  # annotation (column E = index 4)

        # Calculate assessable: 'x' if column E has content, empty otherwise
        assessable = "x" if col_e != "" else ""

        # Calculate depth: if column C is empty, put 1, otherwise count dots
        if col_c == "":
            depth = 1
        else:
            depth = count_dots(
                col_c
            )  # Add 1 because 0 dots = depth 1, 1 dot = depth 2, etc.

        # Calculate implementation_groups: 'R' if column E equals 'RECOMMANDATION', otherwise 'E'
        implementation_groups = (
            "R" if str(col_e).strip().upper() == "RECOMMANDATION" else "E"
        )

        # Create output row
        output_row = {
            "assessable": assessable,
            "depth": depth,
            "ref_id": col_c,
            "name": col_a,
            "implementation_groups": implementation_groups,
            "description": col_d,
            "annotation": col_e,
        }

        output_data.append(output_row)

    # Create output dataframe
    output_df = pd.DataFrame(output_data)

    # Determine output file name
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.parent / f"{input_path.stem}_intermediate.xlsx"

    # Write to Excel
    output_df.to_excel(output_file, index=False, sheet_name="intermediate")

    print(f"✓ Conversion complete!")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Rows processed: {len(output_df)}")

    return output_file


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python convert_pdis_excel.py <input_file> [output_file]")
        print("\nExample:")
        print(
            "  python convert_pdis_excel.py Trame-d-evaluation-PDIS-v2.0-version-1.1.xlsx"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    try:
        convert_pdis_excel(input_file, output_file)
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
