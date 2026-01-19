#!/usr/bin/env python3
"""
Script to extract CIS Controls to CSF 2.0 mapping from Excel file.
Reads the mapping data and creates a simplified output with source_node_id, target_node_id, and relationship.
"""

import sys
import re
import pandas as pd
from pathlib import Path


def format_target_node_id(node_id: str) -> str:
    """
    Format target node ID to put them in lowercase
    """

    return node_id.lower()


def process_mapping(input_file: str, output_file: str = None):
    """
    Process CIS Controls to CSF 2.0 mapping Excel file.

    Args:
        input_file: Path to input Excel file
        output_file: Path to output Excel file (optional, defaults to input_file with _mapping suffix)
    """
    # Read the Excel file - using the 5th sheet (index 4) which is "All CIS Controls & Safeguards"
    df = pd.read_excel(input_file, sheet_name=3)

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

        # Format target_node_id to put it  in lowercase
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
            f"Usage: python {sys.argv[0]} <input_excel_file> [output_excel_file]"
        )
        print("\nExample:")
        print(
            f"  python {sys.argv[0]} CIS_Controls_v8_Mapping_to_CSF_2.0.xlsx"
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
