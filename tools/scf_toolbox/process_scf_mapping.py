#!/usr/bin/env python3
"""
Complete SCF to ISO 27001/27002 mapping processor.
This script:
1. Extracts SCF mapping from Excel file
2. Processes ISO 27001 and ISO 27002 columns
3. Creates combined iso27001-2022 column
4. Generates relationship mapping with validation
"""

import pandas as pd
from pathlib import Path


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


def extract_and_process_mapping(input_file: str, mapping_output_file: str):
    """
    Step 1: Extract and process SCF mapping from Excel file.
    """
    print("=" * 70)
    print("STEP 1: Extracting and Processing SCF Mapping")
    print("=" * 70)
    print(f"\nReading {input_file}...")

    # Read the Excel file from the 'SCF 2025.3.1' sheet
    df = pd.read_excel(input_file, sheet_name="SCF 2025.3.1")

    print(f"Total rows in file: {len(df)}")
    print(f"Columns in file: {len(df.columns)}")

    # Get column names by position (Excel columns B, C, AT, AV)
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
        print("\nProcessing ISO 27001 column...")
        result_df["target_iso27001"] = result_df["target_iso27001"].apply(
            process_iso27001
        )

        # Process ISO 27002 column
        print("Processing ISO 27002 column...")
        result_df["target_iso27002"] = result_df["target_iso27002"].apply(
            process_iso27002
        )

        # Create combined column 'iso27001-2022'
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
        print(f"\nSaving to {mapping_output_file}...")
        result_df.to_excel(mapping_output_file, index=False)

        print(f"\n✓ Successfully created {mapping_output_file}")
        print(f"\nFirst 5 rows:")
        print(result_df.head())

        return result_df

    else:
        print(f"Error: File has only {len(df.columns)} columns, expected at least 48")
        return None


def create_relationship_mapping(
    mapping_df: pd.DataFrame, validation_file: str, output_file: str
):
    """
    Step 2: Create relationship mapping with validation.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Creating Relationship Mapping")
    print("=" * 70)

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
    for idx, row in mapping_df.iterrows():
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

    return result_df


def main():
    """
    Main function to run the complete pipeline.
    """
    script_dir = Path(__file__).parent

    # Input files
    scf_input_file = script_dir / "secure-controls-framework-scf-2025-3-1.xlsx"
    validation_file = script_dir / "mapping-scf-2025.2.2-and-iso27001-2022.xlsx"

    # Output files
    mapping_output_file = script_dir / "scf_iso_mapping.xlsx"
    relationships_output_file = script_dir / "scf_iso_relationships.xlsx"

    # Check input files exist
    if not scf_input_file.exists():
        print(f"Error: Input file not found: {scf_input_file}")
        exit(1)

    if not validation_file.exists():
        print(f"Error: Validation file not found: {validation_file}")
        print(f"Please ensure the validation file exists in the tools directory.")
        exit(1)

    # Step 1: Extract and process mapping
    mapping_df = extract_and_process_mapping(
        str(scf_input_file), str(mapping_output_file)
    )

    if mapping_df is None:
        print("\nError: Failed to extract mapping")
        exit(1)

    # Step 2: Create relationship mapping
    relationships_df = create_relationship_mapping(
        mapping_df, str(validation_file), str(relationships_output_file)
    )

    # Final summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nGenerated files:")
    print(f"  1. {mapping_output_file}")
    print(f"  2. {relationships_output_file}")
    print("\n✓ All done!")


if __name__ == "__main__":
    main()
