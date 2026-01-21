"""
Script to extract CIS Controls to CSF 2.0 mapping from Excel file.

Creates an output Excel with:
1) library_meta
2) mappings_meta
3) mappings_content (source_node_id|target_node_id|relationship)

Then converts the Excel mapping into YAML (Step 2).
"""

import sys
import argparse
import pandas as pd
from pathlib import Path


# Import helper to create base Excel file from YAML (Step 2)
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Import Excel to YAML Converter (Step 3)
from convert_library_v2 import create_library as convert_excel_to_yaml


DEFAULT_OUTPUT_FILENAME_EXCEL = "mapping-cis-controls-v8-and-nist-csf-2.0.xlsx"


def format_target_node_id(node_id: str) -> str:
    """Format target node ID to lowercase."""
    return node_id.lower()


def build_library_meta(packager_name: str) -> pd.DataFrame:
    rows = [
        ("type", "library"),
        ("urn", f"urn:{packager_name}:risk:library:mapping-cis-controls-v8-and-nist-csf-2.0"),
        ("version", "1"),
        ("locale", "en"),
        ("ref_id", "mapping-cis-controls-v8-and-nist-csf-2.0"),
        ("name", "CIS-Controls-v8 <-> NIST-CSF-2.0"),
        ("description", "Mapping between CIS Controls v8 and NIST CSF v2.0"),
        (
            "copyright",
            "This work is licensed under a Creative Commons Attribution-NonCommercial-No Derivatives 4.0 International Public License "
            "(the link can be found at https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode). To further clarify the Creative Commons "
            "license related to the CIS Controls® content, you are authorized to copy and redistribute the content as a framework for use by you, "
            "within your organization and outside of your organization for non-commercial purposes only, provided that (i) appropriate credit is given "
            "to CIS, and (ii) a link to the license is provided. Additionally, if you remix, transform or build upon the CIS Controls, you may not distribute "
            "the modified materials. Users of the CIS Controls framework are also required to refer to (http://www.cisecurity.org/controls/) when referring "
            "to the CIS Controls in order to ensure that users are employing the most up-to-date guidance. Commercial use of the CIS Controls is subject to "
            "the prior approval of CIS® (Center for Internet Security, Inc.).",
        ),
        ("provider", "CIS"),
        ("packager", packager_name),
        (
            "dependencies",
            f"urn:{packager_name}:risk:library:cis-controls-v8, urn:intuitem:risk:library:nist-csf-2.0",
        ),
    ]
    return pd.DataFrame(rows)


def build_mappings_meta(packager_name: str) -> pd.DataFrame:
    rows = [
        ("type", "requirement_mapping_set"),
        ("urn", f"urn:{packager_name}:risk:req_mapping_set:mapping-cis-controls-v8-and-nist-csf-2.0"),
        ("ref_id", "mapping-cis-controls-v8-and-nist-csf-2.0"),
        ("name", "CIS-Controls-v8 <-> NIST-CSF-2.0"),
        ("description", "Mapping between CIS Controls v8 and NIST CSF v2.0"),
        ("source_framework_urn", f"urn:{packager_name}:risk:framework:cis-controls-v8"),
        ("target_framework_urn", "urn:intuitem:risk:framework:nist-csf-2.0"),
        ("source_node_base_urn", f"urn:{packager_name}:risk:req_node:cis-controls-v8"),
        ("target_node_base_urn", "urn:intuitem:risk:req_node:nist-csf-2.0"),
    ]
    return pd.DataFrame(rows)


def extract_mappings_content(input_file: str) -> pd.DataFrame:
    # Read the Excel file - using the 4th sheet (index 3) which is "All CIS Controls & Safeguards"
    df = pd.read_excel(input_file, sheet_name=3)

    mapping_data = []
    for _, row in df.iterrows():
        source_node_id = row.iloc[2]    # Column C (index 2)
        target_node_id = row.iloc[11]   # Column L (index 11)
        relationship = row.iloc[10]     # Column K (index 10)

        if pd.isna(source_node_id) or pd.isna(target_node_id) or pd.isna(relationship):
            continue

        source_node_id = str(source_node_id).strip().lower()
        target_node_id = str(target_node_id).strip().lower()
        relationship = str(relationship).strip().lower()

        target_node_id = format_target_node_id(target_node_id)

        if relationship == "equivalent":
            relationship = "equal"

        mapping_data.append(
            {
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "relationship": relationship,
            }
        )

    return pd.DataFrame(mapping_data)


def process_mapping(input_file: str, packager_name: str, output_file: str = None) -> pd.DataFrame:
    mapping_df = extract_mappings_content(input_file)
    library_meta_df = build_library_meta(packager_name)
    mappings_meta_df = build_mappings_meta(packager_name)

    if output_file is None:
        output_file = DEFAULT_OUTPUT_FILENAME_EXCEL

    # Sheet order:
    # 1) library_meta
    # 2) mappings_meta
    # 3) mappings_content
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        library_meta_df.to_excel(writer, index=False, header=False, sheet_name="library_meta")
        mappings_meta_df.to_excel(writer, index=False, header=False, sheet_name="mappings_meta")
        mapping_df.to_excel(writer, index=False, sheet_name="mappings_content")

    print(f"Processed {len(mapping_df)} mappings")
    print(f"Output written to: {output_file}")

    return mapping_df


def main():
    parser = argparse.ArgumentParser(
        description="Extract CIS Controls v8 to NIST CSF 2.0 mapping and generate a formatted Excel output."
    )
    parser.add_argument("input_excel_file", help="Path to input Excel mapping file")
    parser.add_argument(
        "packager_name_CIS",
        help="Packager name used in your CIS v8 Framework",
    )

    args = parser.parse_args()

    output_excel_file = DEFAULT_OUTPUT_FILENAME_EXCEL

    # Output YAML: same stem as Excel + .yaml
    output_path = Path(Path(DEFAULT_OUTPUT_FILENAME_EXCEL).stem + ".yaml")


    try:
        print("\n###########################################")
        print("##### [STEP 1] Creating Excel Mapping #####")
        print("###########################################\n")

        process_mapping(args.input_excel_file, args.packager_name_CIS, output_excel_file)

        print("\n##########################################")
        print("##### [STEP 2] Creating YAML Mapping #####")
        print("##########################################\n")

        convert_excel_to_yaml(output_excel_file, output_path)

    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
