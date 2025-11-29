#!/usr/bin/env python3
"""
Convert SCF mapping to node-relationship format.
Creates one row per source->target relationship.
"""

import pandas as pd
from pathlib import Path


def create_relationship_mapping(
    input_file: str, output_file: str, validation_file: str
):
    """
    Convert SCF mapping to relationship format.

    Args:
        input_file: Path to the input mapping file (scf_iso_mapping.xlsx)
        output_file: Path to the output relationship file
        validation_file: Path to the validation file (mapping-scf-2025.2.2-and-iso27001-2022.xlsx)
    """
    print(f"Reading {input_file}...")

    # Read the mapping file
    df = pd.read_excel(input_file)

    print(f"Total rows in input: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # Read validation file to get valid source_nodes
    print(f"\nReading validation file: {validation_file}...")
    validation_df = pd.read_excel(validation_file, sheet_name="mappings_content")

    print(f"Validation file columns: {list(validation_df.columns)}")
    print(f"Validation file has {len(validation_df)} rows")

    # Find the source_node column (might have different name)
    source_col = None
    for col in validation_df.columns:
        if "source" in col.lower() and "node" in col.lower():
            source_col = col
            break

    if source_col is None:
        # Try to find any column that might contain source references
        print("\nAvailable columns in validation file:")
        for i, col in enumerate(validation_df.columns):
            sample_val = (
                validation_df[col].dropna().iloc[0]
                if len(validation_df[col].dropna()) > 0
                else None
            )
            print(f"  {i}: {col} (sample: {sample_val})")
        raise ValueError("Could not find 'source_node' column in validation file")

    valid_source_nodes = set(validation_df[source_col].dropna().astype(str))
    print(f"Using column '{source_col}' for validation")
    print(f"Loaded {len(valid_source_nodes)} valid source nodes from validation file")

    # Create list to store relationships
    relationships = []
    skipped_nodes = []

    # Process each row
    for idx, row in df.iterrows():
        source_ref_id = row["source_ref_id"]
        iso27001_2022 = row["iso27001-2022"]

        # Convert source_ref_id to lowercase
        source_node = str(source_ref_id).lower() if pd.notna(source_ref_id) else None

        if pd.isna(iso27001_2022) or not str(iso27001_2022).strip():
            continue

        # Validate source_node exists in validation file
        if source_node not in valid_source_nodes:
            if source_node not in skipped_nodes:
                skipped_nodes.append(source_node)
                print(
                    f"⚠️  Skipping source_node '{source_node}' - not found in validation file"
                )
            continue

        # Split the iso27001-2022 column by lines
        target_nodes = str(iso27001_2022).split("\n")

        # Create a relationship for each target node
        for target in target_nodes:
            target = target.strip()
            if target:
                relationships.append(
                    {
                        "source_node": source_node,
                        "target_node": target,
                        "relationship": "intersect",
                    }
                )

    # Create DataFrame from relationships
    result_df = pd.DataFrame(relationships)

    print(f"\nRelationship mapping results:")
    print(f"  Total relationships created: {len(result_df)}")
    print(f"  Unique source nodes: {result_df['source_node'].nunique()}")
    print(f"  Unique target nodes: {result_df['target_node'].nunique()}")
    print(f"  Skipped source nodes: {len(skipped_nodes)}")

    if skipped_nodes:
        print(f"\n⚠️  Skipped source nodes (not found in validation file):")
        for node in sorted(skipped_nodes):
            print(f"    - {node}")

    # Save to Excel
    print(f"\nSaving to {output_file}...")
    result_df.to_excel(output_file, index=False)

    print(f"\n✓ Successfully created {output_file}")
    print(f"\nFirst 10 rows of output:")
    print(result_df.head(10))

    # Show some statistics
    if len(result_df) > 0:
        print(f"\nSample relationships:")
        print(result_df.sample(min(5, len(result_df))))


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_file = script_dir / "scf_iso_mapping.xlsx"
    output_file = script_dir / "scf_iso_relationships.xlsx"
    validation_file = script_dir / "mapping-scf-2025.2.2-and-iso27001-2022.xlsx"

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print(f"Please run extract_scf_mapping.py first to generate the input file.")
        exit(1)

    if not validation_file.exists():
        print(f"Error: Validation file not found: {validation_file}")
        print(f"Please ensure the validation file exists in the tools directory.")
        exit(1)

    create_relationship_mapping(str(input_file), str(output_file), str(validation_file))
