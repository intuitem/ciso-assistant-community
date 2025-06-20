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
# from datetime import date


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


# Ajout validation extra_locales
def validate_extra_locales(data):
    extra_locales = data.get("extra_locales")
    if extra_locales is None:
        return

    if not isinstance(extra_locales, list) or not extra_locales:
        raise ValueError("Field \"extra_locales\" must be a non-empty list if defined.")

    for i, locale_entry in enumerate(extra_locales, start=1):
        if not isinstance(locale_entry, dict) or len(locale_entry) != 1:
            raise ValueError(f"Each entry in \"extra_locales\" must be a dict with exactly one locale code key (entry #{i})")

        for loc_code, loc_data in locale_entry.items():
            if not re.fullmatch(r"[a-z0-9-]{2,5}", loc_code):
                raise ValueError(f"Invalid locale code \"{loc_code}\" in extra_locales entry #{i}")

            if not isinstance(loc_data, dict) or not loc_data:
                raise ValueError(f"Locale data for \"{loc_code}\" must be a non-empty dict (entry #{i})")

            # Champs facultatifs, warning s’ils sont manquants ou vides
            for req_field in ["framework_name", "description", "copyright"]:
                if req_field not in loc_data or str(loc_data[req_field]).strip() == "":
                    print(f"⚠️  [WARNING] Missing or empty field \"{req_field}\" in extra_locales for locale \"{loc_code}\" (entry #{i})")

            # Validate implementation_groups in locale if present
            if "implementation_groups" in loc_data:
                groups = loc_data["implementation_groups"]
                if not isinstance(groups, list) or not groups:
                    raise ValueError(f"Field \"implementation_groups\" in extra_locales for locale \"{loc_code}\" must be a non-empty list")
                for j, group in enumerate(groups, start=1):
                    if "ref_id" not in group or not str(group["ref_id"]).strip():
                        raise ValueError(f"Missing or empty \"ref_id\" in implementation group #{j} for locale \"{loc_code}\"")
                    if "name" not in group or not str(group["name"]).strip():
                        raise ValueError(f"Missing or empty \"name\" in implementation group #{j} for locale \"{loc_code}\"")


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

    # Validate extra_locales if present
    validate_extra_locales(data)


# Modification dans create_excel_from_yaml :

def create_excel_from_yaml(yaml_path, output_excel=None):
    if not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"YAML file not found: \"{yaml_path}\"")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    validate_yaml_data(data)

    yaml_output_name = data.get("excel_file_name")
    if output_excel is None:
        if yaml_output_name and str(yaml_output_name).strip():
            output_excel = yaml_output_name.strip()
        else:
            output_excel = "output.xlsx"
    elif yaml_output_name and str(yaml_output_name).strip() and output_excel != yaml_output_name.strip():
        print(f"ℹ️  [INFO] Overriding YAML \"excel_file_name\" with command line argument.")

    if not output_excel.lower().endswith(".xlsx"):
        output_excel += ".xlsx"

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

    # Feuille principale library_meta
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

    # Ajout extra_locales dans library_meta
    extra_locales = data.get("extra_locales")
    if extra_locales:
        for locale_entry in extra_locales:
            for loc_code, loc_data in locale_entry.items():
                # Ajouter uniquement les champs présents et non vides
                if "framework_name" in loc_data and str(loc_data["framework_name"]).strip():
                    ws1.append([f"name[{loc_code}]", loc_data["framework_name"]])
                if "description" in loc_data and str(loc_data["description"]).strip():
                    ws1.append([f"description[{loc_code}]", loc_data["description"]])
                if "copyright" in loc_data and str(loc_data["copyright"]).strip():
                    ws1.append([f"copyright[{loc_code}]", loc_data["copyright"]])

    # Feuille principale framework_meta
    framework_meta_sheet = wb.create_sheet(f"{framework_sheet_base}_meta")
    framework_meta_sheet.append(["type", "framework"])
    framework_meta_sheet.append(["base_urn", f"urn:intuitem:risk:req_node:{urn_root}"])
    framework_meta_sheet.append(["urn", f"urn:intuitem:risk:framework:{urn_root}"])
    framework_meta_sheet.append(["ref_id", ref_id])
    framework_meta_sheet.append(["name", name])
    framework_meta_sheet.append(["description", description])
    if impl_group_base:
        framework_meta_sheet.append(["implementation_groups_definition", impl_group_base])

    # Ajout extra_locales dans framework_meta
    if extra_locales:
        for locale_entry in extra_locales:
            for loc_code, loc_data in locale_entry.items():
                if "framework_name" in loc_data and str(loc_data["framework_name"]).strip():
                    framework_meta_sheet.append([f"name[{loc_code}]", loc_data["framework_name"]])
                if "description" in loc_data and str(loc_data["description"]).strip():
                    framework_meta_sheet.append([f"description[{loc_code}]", loc_data["description"]])

    # Feuille principale framework_content
    framework_content_sheet = wb.create_sheet(f"{framework_sheet_base}_content")
    framework_content_sheet.append(["assessable", "depth", "ref_id", "name", "description", "annotation", "typical_evidence", ("implementation_groups" if impl_group_base else None)])

    # Feuilles implementation_groups (locale principale seulement)
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
