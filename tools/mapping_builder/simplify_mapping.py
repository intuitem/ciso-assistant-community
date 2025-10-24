#!/usr/bin/env python3
"""
Mapping CSV Simplifier

This script transforms a detailed mapping CSV into a simplified format with only:
- source_node_id (from source_ref_id)
- target_node_id (from target_ref_id)
- relationship
- strength_of_relationship (from score)
"""

import argparse
import pandas as pd
from pathlib import Path


def simplify_mapping(
    input_path: str,
    output_path: str = None,
    include_no_relationship: bool = False,
    favor_equals: bool = False,
) -> pd.DataFrame:
    """
    Simplify mapping CSV to core columns

    Args:
        input_path: Path to input mapping CSV
        output_path: Path to output simplified CSV (optional)
        include_no_relationship: If True, keep "no_relationship" rows (default: False)
        favor_equals: If True, for each source item, show only "equal" relationships if available (default: False)

    Returns:
        pandas DataFrame with simplified mapping
    """
    print(f"Reading mapping from: {input_path}")

    # Read CSV
    df = pd.read_csv(input_path)

    print(f"Total mappings: {len(df)}")

    # Check required columns
    required_columns = ["source_ref_id", "target_ref_id", "relationship", "score"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Filter out no_relationship if requested
    if not include_no_relationship:
        original_count = len(df)
        df = df[df["relationship"] != "no_relationship"]
        filtered_count = original_count - len(df)
        if filtered_count > 0:
            print(f"Filtered out {filtered_count} 'no_relationship' mappings")

    # Favor equals mode: for each source, keep only "equal" if available
    if favor_equals:
        original_count = len(df)
        filtered_rows = []

        for source_id in df["source_ref_id"].unique():
            source_matches = df[df["source_ref_id"] == source_id]
            equal_matches = source_matches[source_matches["relationship"] == "equal"]

            if len(equal_matches) > 0:
                # Has equal matches, keep only those
                filtered_rows.append(equal_matches)
            else:
                # No equal matches, keep all matches for this source
                filtered_rows.append(source_matches)

        df = pd.concat(filtered_rows, ignore_index=True)
        filtered_count = original_count - len(df)
        if filtered_count > 0:
            print(
                f"Favor-equals mode: kept only 'equal' relationships when available, filtered {filtered_count} rows"
            )

    # Select and rename columns
    simplified = df[required_columns].copy()
    simplified.columns = [
        "source_node_id",
        "target_node_id",
        "relationship",
        "strength_of_relationship",
    ]

    # Sort by strength descending
    simplified = simplified.sort_values("strength_of_relationship", ascending=False)

    print(f"\nSimplified mapping: {len(simplified)} rows")
    print(f"\nRelationship distribution:")
    print(simplified["relationship"].value_counts())
    print(f"\nStrength statistics:")
    print(simplified["strength_of_relationship"].describe())

    # Save if output path specified
    if output_path:
        output_file = Path(output_path)
        if output_file.suffix == ".xlsx":
            simplified.to_excel(output_path, index=False, engine="openpyxl")
        else:
            simplified.to_csv(output_path, index=False)
        print(f"\nSimplified mapping saved to: {output_path}")

    return simplified


def main():
    parser = argparse.ArgumentParser(
        description="Simplify mapping CSV to core columns (source_node_id, target_node_id, relationship, strength_of_relationship)"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input mapping CSV file",
    )
    parser.add_argument(
        "--output",
        help="Path to output simplified CSV file (default: input_simplified.csv)",
    )
    parser.add_argument(
        "--include-no-relationship",
        action="store_true",
        help="Include 'no_relationship' mappings in output (default: exclude them)",
    )
    parser.add_argument(
        "--favor-equals",
        action="store_true",
        help="For each source item, show only 'equal' relationships if available, otherwise show all matches",
    )

    args = parser.parse_args()

    # Set default output path if not specified
    output_path = args.output
    if not output_path:
        input_file = Path(args.input)
        output_path = input_file.parent / f"{input_file.stem}_simplified.csv"

    # Simplify mapping
    simplified = simplify_mapping(
        input_path=args.input,
        output_path=output_path,
        include_no_relationship=args.include_no_relationship,
        favor_equals=args.favor_equals,
    )

    # Show sample
    print("\n" + "=" * 80)
    print("SAMPLE OUTPUT (top 10 by strength):")
    print("=" * 80)
    print(simplified.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
