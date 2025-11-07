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


def clean_ref_id(ref_id):
    """Clean ref_id by removing trailing characters like ')'."""
    if not ref_id:
        return ref_id
    # Remove trailing non-alphanumeric characters
    return ref_id.rstrip(")").strip()


def get_parent_ref_id(ref_id):
    """Get parent ref_id by dropping the last dotted part.

    Example: 'IV.2.1.m)' -> 'IV.2.1'
    """
    if not ref_id:
        return ""

    # Clean the ref_id first
    cleaned = clean_ref_id(ref_id)

    # Split by dots and take all but the last part
    parts = cleaned.split(".")
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return cleaned


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

        # Check if column C has multiple entries (line breaks)
        col_c_entries = (
            [entry.strip() for entry in str(col_c).split("\n") if entry.strip()]
            if col_c
            else []
        )

        # Check if column D has multiple entries separated by empty lines
        # Split by double line breaks and filter out empty entries
        col_d_str = str(col_d) if col_d else ""
        col_d_entries = [
            entry.strip() for entry in col_d_str.split("\n\n") if entry.strip()
        ]

        # If we don't have multiple entries separated by double newlines, try single newlines
        # but only if we have multiple ref_ids
        if len(col_d_entries) <= 1 and len(col_c_entries) > 1:
            col_d_entries = [
                entry.strip() for entry in col_d_str.split("\n") if entry.strip()
            ]

        # Calculate base depth: if column C is empty, put 1, otherwise count dots
        has_multiple_entries = len(col_c_entries) > 1

        if has_multiple_entries:
            # Get first ref_id to calculate base depth
            first_ref_id = clean_ref_id(col_c_entries[0]) if col_c_entries else ""

            # Create a parent row with the name, not assessable
            base_depth = 1 if not first_ref_id else count_dots(first_ref_id)

            parent_row = {
                "assessable": "",  # Parent is not assessable
                "depth": base_depth,
                "ref_id": "",  # Parent has empty ref_id
                "name": col_a,
                "implementation_groups": "",  # Not assessable = no implementation group
                "description": "",
                "annotation": "",  # No annotation on parent node
            }
            output_data.append(parent_row)

            # Create child rows for each ref_id/description pair
            for i, ref_id in enumerate(col_c_entries):
                # Clean the ref_id
                cleaned_ref_id = clean_ref_id(ref_id)

                # Get corresponding description if available
                description = col_d_entries[i] if i < len(col_d_entries) else ""

                # Calculate depth based on dots in ref_id, then increment
                child_depth = (
                    count_dots(cleaned_ref_id) if cleaned_ref_id else base_depth
                ) + 1

                # Calculate implementation_groups
                implementation_groups = (
                    "R" if str(col_e).strip().upper() == "RECOMMANDATION" else "E"
                )

                child_row = {
                    "assessable": "x"
                    if col_e != ""
                    else "",  # Assessable if annotation exists
                    "depth": child_depth,
                    "ref_id": cleaned_ref_id,
                    "name": "",  # Empty name for child rows
                    "implementation_groups": implementation_groups,
                    "description": description,
                    "annotation": col_e,  # Repeat annotation for each child
                }
                output_data.append(child_row)
        else:
            # Single entry - normal processing
            # Clean the ref_id
            cleaned_ref_id = clean_ref_id(col_c) if col_c else ""

            # Calculate assessable: 'x' if column E has content, empty otherwise
            assessable = "x" if col_e != "" else ""

            # Calculate depth: if column C is empty, put 1, otherwise count dots
            if cleaned_ref_id == "":
                depth = 1
            else:
                depth = count_dots(cleaned_ref_id)

            # Calculate implementation_groups: only if assessable
            # 'R' if column E equals 'RECOMMANDATION', otherwise 'E'
            if assessable:
                implementation_groups = (
                    "R" if str(col_e).strip().upper() == "RECOMMANDATION" else "E"
                )
            else:
                implementation_groups = ""  # Not assessable = no implementation group

            # Create output row
            output_row = {
                "assessable": assessable,
                "depth": depth,
                "ref_id": cleaned_ref_id,
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
