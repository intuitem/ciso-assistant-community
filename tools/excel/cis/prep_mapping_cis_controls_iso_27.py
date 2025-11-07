#!/usr/bin/env python3
"""
Script to extract CIS Controls to ISO 27001 mapping from Excel file.
Reads the mapping data and creates a simplified output with source_node_id, target_node_id, and relationship.
"""

import sys
import re
import pandas as pd
from pathlib import Path


def format_target_node_id(node_id: str) -> str:
    """
    Format target node ID to include dot after letter prefix.
    Example: a5.9 -> a.5.9, a8.8 -> a.8.8
    """
    # Pattern to match letter(s) followed by digits (e.g., a5, a8)
    pattern = r"^([a-z]+)(\d)"
    match = re.match(pattern, node_id)

    if match:
        # Insert dot between letter prefix and first digit
        return f"{match.group(1)}.{node_id[len(match.group(1)) :]}"

    return node_id


def process_mapping(input_file: str, output_file: str = None):
    """
    Process CIS Controls to ISO 27001 mapping Excel file.

    Args:
        input_file: Path to input Excel file
        output_file: Path to output Excel file (optional, defaults to input_file with _mapping suffix)
    """
    # Read the Excel file - using the 5th sheet (index 4) which is "All CIS Controls & Safeguards"
    df = pd.read_excel(input_file, sheet_name=4)

    # Extract relevant columns
    # Column C = CIS Safeguard (source_node_id)
    # Column L = Control # (target_node_id)
    # Column K = Relationship
    mapping_data = []

    for _, row in df.iterrows():
        source_node_id = row.iloc[2]  # Column C (index 2)
        target_node_id = row.iloc[11]  # Column L (index 11)
        relationship = row.iloc[10]  # Column K (index 10)

        # Skip rows with missing data
        if pd.isna(source_node_id) or pd.isna(target_node_id) or pd.isna(relationship):
            continue

        # Convert to string and lowercase
        source_node_id = str(source_node_id).strip().lower()
        target_node_id = str(target_node_id).strip().lower()
        relationship = str(relationship).strip().lower()

        # Format target_node_id to include dot after letter prefix (e.g., a5.9 -> a.5.9)
        target_node_id = format_target_node_id(target_node_id)

        # Replace "equivalent" with "equal"
        if relationship == "equivalent":
            relationship = "equal"

        mapping_data.append(
            {
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "relationship": relationship,
            }
        )

    # Create output DataFrame
    output_df = pd.DataFrame(mapping_data)

    # Determine output file name
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.parent / f"{input_path.stem}_mapping.xlsx"

    # Write to Excel
    output_df.to_excel(output_file, index=False, sheet_name="Mapping")

    print(f"Processed {len(output_df)} mappings")
    print(f"Output written to: {output_file}")

    return output_df


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python prep_mapping_cis_controls_iso_27.py <input_excel_file> [output_excel_file]"
        )
        print("\nExample:")
        print(
            "  python prep_mapping_cis_controls_iso_27.py CIS_Controls_v8_NEW_MAPPING_to_ISO.IEC_27001.2022_2_2023.xlsx"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        process_mapping(input_file, output_file)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
