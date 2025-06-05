"""
Excel Framework Generator v0.3
--------------------------

This script reads a YAML configuration file and generates a structured Excel (.xlsx) file
based on a predefined template to create the base structure of a CISO Assistant framework in v2.
It ensures the integrity of required fields, supports optional implementation groups, and performs
validation with user-friendly error messages.

Usage:
    python generate_excel_from_yaml.py input.yaml [output.xlsx]

Dependencies:
    - PyYAML
    - openpyxl

Features:
    - Required field validation
    - URN format enforcement
    - Optional implementation groups with structure validation
    - Automatic Excel generation with multiple sheets
    - Informative logs and error handling
"""


import re
import sys
import os
import yaml
from openpyxl import Workbook
from datetime import date


# Validates that urn_root only contains allowed characters
def validate_urn_root(urn_root):
    if not re.fullmatch(r"[a-z0-9._-]+", urn_root):
        raise ValueError(
            "Invalid URN root : only lowercase alphanumeric characters, '-', '_', and '.' are allowed."
        )


# Checks for required non-empty field
def validate_required_field(field_name, value):
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing or empty required field: \"{field_name}\"")


# Centralized validation of YAML content
def validate_yaml_data(data):
    required_fields = [
        "urn_root", "locale", "ref_id", "framework_name", "description",
        "copyright", "provider", "framework_sheet_base_name"
    ]
    for field in required_fields:
        validate_required_field(field, data.get(field))

    validate_urn_root(data["urn_root"])

    impl_base = data.get("implementation_groups_sheet_base_name")
    impl_groups = data.get("implementation_groups")


    # Validate implementation_groups if base name is defined
    if impl_base:
        if not isinstance(impl_groups, list) or not impl_groups:
            raise ValueError("Field \"implementation_groups\" must be a non-empty list if \"implementation_groups_sheet_base_name\" is defined.")
        print(f"ℹ️  [INFO] Implementation groups will be added using base name: \"{impl_base}\"")
        for i, group in enumerate(impl_groups, start=1):
            if "ref_id" not in group or not str(group["ref_id"]).strip():
                raise ValueError(f"Missing or empty \"ref_id\" in implementation group #{i}")
            if "name" not in group or not str(group["name"]).strip():
                raise ValueError(f"Missing or empty \"name\" in implementation group #{i}")
            if "description" not in group or not str(group["description"]).strip():
                print(f"⚠️  [WARNING] Description is missing or empty in implementation group #{i}")


# Main logic to create Excel workbook from the YAML content
def create_excel_from_yaml(yaml_path, output_excel=None):
    if not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"YAML file not found: \"{yaml_path}\"")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    validate_yaml_data(data)
    
    
    # Determine output Excel file name based on YAML or CLI
    yaml_output_name = data.get("excel_file_name")
    if output_excel is None:
        if yaml_output_name and str(yaml_output_name).strip():
            output_excel = yaml_output_name.strip()
        else:
            output_excel = "output.xlsx"
    elif yaml_output_name and str(yaml_output_name).strip() and output_excel != yaml_output_name.strip():
        print(f"ℹ️  [INFO] Overriding YAML \"excel_file_name\" with command line argument.")
        
    # Ensure the filename ends with .xlsx
    if not output_excel.lower().endswith(".xlsx"):
        output_excel += ".xlsx"


    # Extract fields for easier reference
    urn_root = data["urn_root"]
    locale = data["locale"]
    ref_id = data["ref_id"]
    name = data["framework_name"]
    description = data["description"]
    copyright_ = data["copyright"]
    provider = data["provider"]
    framework_sheet_base = data["framework_sheet_base_name"]
    impl_group_base = data.get("implementation_groups_sheet_base_name")
    impl_groups = data.get("implementation_groups", [])

    wb = Workbook()

    # Sheet 1: library_meta
    ws1 = wb.active
    ws1.title = "library_meta"
    ws1.append(["type", "library"])
    ws1.append(["urn", f"urn:intuitem:risk:library:{urn_root}"])
    ws1.append(["version", "1"])
    ws1.append(["locale", locale])
    ws1.append(["ref_id", ref_id])
    ws1.append(["name", name])
    ws1.append(["description", description])
    ws1.append(["copyright", copyright_])
    ws1.append(["provider", provider])
    ws1.append(["packager", "intuitem"])
    ws1.append(["publication_date", str(date.today())])

    # Sheet 2: <framework>_meta
    framework_meta_sheet = wb.create_sheet(f"{framework_sheet_base}_meta")
    framework_meta_sheet.append(["type", "framework"])
    framework_meta_sheet.append(["base_urn", f"urn:intuitem:risk:req_node:{urn_root}"])
    framework_meta_sheet.append(["urn", f"urn:intuitem:risk:framework:{urn_root}"])
    framework_meta_sheet.append(["ref_id", ref_id])
    framework_meta_sheet.append(["name", name])
    framework_meta_sheet.append(["description", description])
    if impl_group_base:
        framework_meta_sheet.append(["implementation_groups_definition", impl_group_base])

    # Sheet 3: <framework>_content
    framework_content_sheet = wb.create_sheet(f"{framework_sheet_base}_content")
    framework_content_sheet.append(["assessable", "depth", "ref_id", "name", "description", "implementation_groups"])

    # Optional implementation group sheets
    if impl_group_base:
        impl_meta_sheet = wb.create_sheet(f"{impl_group_base}_meta")
        impl_meta_sheet.append(["type", "implementation_groups"])
        impl_meta_sheet.append(["name", impl_group_base])

        impl_content_sheet = wb.create_sheet(f"{impl_group_base}_content")
        impl_content_sheet.append(["ref_id", "name", "description"])
        for group in impl_groups:
            row = [group.get("ref_id", ""), group.get("name", ""), group.get("description", "")]
            impl_content_sheet.append(row)

    try:
        wb.save(output_excel)
        print(f"✅ [SUCCESS] Excel file saved successfully: \"{output_excel}\"")
    except Exception as e:
        print(f"❌ [ERROR] Failed to save Excel file: {e}")
        print("💡 Tip: Make sure the Excel file is not open in another program and that you have write permission.")
        sys.exit(1)


# CLI entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_excel_from_yaml.py input.yaml [output.xlsx]")
        sys.exit(1)

    yaml_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else None

    try:
        create_excel_from_yaml(yaml_file, output_file)
    except Exception as err:
        print(f"❌ [FATAL ERROR] {err}")
        sys.exit(1)
