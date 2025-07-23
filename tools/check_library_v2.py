import os
import re
import sys
import argparse
import pandas as pd
from openpyxl import load_workbook
from pydot import Any


# ─────────────────────────────────────────────────────────────
# VALIDATE UTILS
# ─────────────────────────────────────────────────────────────

def validate_urn(urn: str, context: str = None):
    pattern = r"^urn:([a-z0-9._-]+:)*[a-z0-9._-]+$"
    if not re.fullmatch(pattern, urn):
        raise ValueError(f"({context if context else 'validate_urn'}) Invalid URN \"{urn}\" : Only lowercase alphanumeric characters, '-', '_', and '.' are allowed")

def validate_ref_id(ref_id: str, context: str = None):
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", ref_id):
        raise ValueError(f"({context if context else 'validate_ref_id'}) Invalid Ref. ID \"{ref_id}\" : Only alphanumeric characters, '-', '_', and '.' are allowed")

def validate_sheet_name(sheet_name: str, context: str = None):
    if not (sheet_name.endswith("_meta") or sheet_name.endswith("_content")):
        raise ValueError(f"({context if context else 'validate_sheet_name'}) Invalid sheet name \"{sheet_name}\". Sheet names must end with '_meta' or '_content'")

def print_sheet_validation(sheet_name: str, warnings: Any = None):
    
    if not warnings:
        print(f"🟢 [CHECK] Valid sheet: \"{sheet_name}\"")
    else:
        print(f"🟡 [CHECK] Valid sheet with warnings: \"{sheet_name}\"")


# ─────────────────────────────────────────────────────────────
# VALIDATE META SHEETS
# ─────────────────────────────────────────────────────────────


# Global Checks
def validate_meta_sheet(df, sheet_name, expected_keys, expected_type, context):
    
    # Validate all required keys (excluding "type" which is handled separately)
    
    if expected_keys:
        for key in expected_keys:
            matches = df[df.iloc[:, 0] == key]
            if matches.empty:
                raise ValueError(f"({context}) [{sheet_name}] Missing required key \"{key}\" in meta sheet")
            
            row_index = matches.index[0]
            value = matches.iloc[0, 1] if matches.shape[1] > 1 else None

            if pd.isna(value) or str(value).strip() == "":
                raise ValueError(f"({context}) [{sheet_name}] Row #{row_index + 1}: Key \"{key}\" is present but has no value")

    # Validate presence and value of "type" key
    type_matches = df[df.iloc[:, 0] == "type"]
    if type_matches.empty:
        raise ValueError(f"({context}) {sheet_name}: Missing required key \"type\" in meta sheet")

    type_row_index = type_matches.index[0]
    type_value = type_matches.iloc[0, 1] if type_matches.shape[1] > 1 else None

    if pd.isna(type_value) or str(type_value).strip() == "":
        raise ValueError(f"({context}) [{sheet_name}] Row #{type_row_index + 1}: Key \"type\" is present but has no value")

    if str(type_value).strip() != expected_type:
        raise ValueError(f"({context}) [{sheet_name}] Row #{type_row_index + 1}: Invalid type \"{type_value}\". Expected \"{expected_type}\"")



# [META] Library
def validate_library_meta(df, sheet_name):
    
    expected_type = "library"
    fct_name = validate_library_meta.__name__
    expected_keys = [
        "urn", "version", "locale", "ref_id", "name",
        "description", "copyright", "provider", "packager"
    ]

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    validate_urn(urn_value, context="validate_library_meta")

    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    validate_ref_id(ref_id_value, context="validate_library_meta")
    
    print_sheet_validation(sheet_name)


# [META] Framework
def validate_framework_meta(df, sheet_name):
    
    expected_type = "framework"
    fct_name = validate_framework_meta.__name__
    expected_keys = [
        "urn", "ref_id", "name", "description", "base_urn"
    ]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    validate_urn(urn_value, context="validate_framework_meta")

    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    validate_ref_id(ref_id_value, context="validate_framework_meta")
    
    print_sheet_validation(sheet_name)


# [META] Threats
def validate_threats_meta(df, sheet_name):
    
    expected_type = "threats"
    fct_name = validate_framework_meta.__name__
    expected_keys = ["base_urn"]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name)


# [META] Reference Controls
def validate_reference_controls_meta(df, sheet_name):
    
    expected_type = "reference_controls"
    fct_name = validate_framework_meta.__name__
    expected_keys = ["base_urn"]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name)


# [META] Risk Matrix
def validate_risk_matrix_meta(df, sheet_name):
    
    expected_type = "risk_matrix"
    fct_name = validate_framework_meta.__name__
    expected_keys = ["urn", "ref_id", "name", "description"]

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    validate_urn(urn_value, context="validate_risk_matrix_meta")

    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    validate_ref_id(ref_id_value, context="validate_risk_matrix_meta")
    
    print_sheet_validation(sheet_name)


# [META] Implementation Groups
def validate_implementation_groups_meta(df, sheet_name):
    
    expected_type = "implementation_groups"
    fct_name = validate_framework_meta.__name__
    expected_keys = ["name"]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name)


# [META] Mappings
def validate_requirement_mapping_set_meta(df, sheet_name):
    
    expected_type = "requirement_mapping_set"
    fct_name = validate_framework_meta.__name__
    expected_keys = [
        "source_framework_urn",
        "source_node_base_urn",
        "target_framework_base_urn",
        "target_node_base_urn"
    ]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name)


# [META] Scores
def validate_scores_meta(df, sheet_name):
    
    expected_type = "scores"
    fct_name = validate_scores_meta.__name__
    expected_keys = ["name"]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name)


# [META] Answers
def validate_answers_meta(df, sheet_name):
    
    expected_type = "answers"
    fct_name = validate_answers_meta.__name__
    expected_keys = ["name"]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name)


# [META] URN Prefix
def validate_urn_prefix_meta(df, sheet_name):
    
    expected_type = "urn_prefix"
    fct_name = validate_urn_prefix_meta.__name__
    # No "expected_keys" because only  "type" is required
    
    validate_meta_sheet(df, sheet_name, None, expected_type, fct_name)
    
    print_sheet_validation(sheet_name)



# ─────────────────────────────────────────────────────────────
# VALIDATE CONTENT SHEETS
# ─────────────────────────────────────────────────────────────


# Global Checks
def validate_content_sheet(df, sheet_name, required_columns, context):
    
    if required_columns:
        # Check that all required columns are present
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"({context}) [{sheet_name}] Missing required column \"{col}\" in content sheet")

        # Check that each non-empty row has a non-empty value (after strip) in every required column
        for col in required_columns:
            for idx, value in df[col].items():
                row_values = df.loc[idx]
                if not any(pd.notna(v) and str(v).strip() != "" for v in row_values):
                    continue  # Skip completely empty rows

                if pd.isna(value) or str(value).strip() == "":
                    raise ValueError(f"({context}) [{sheet_name}] Row #{idx + 2}: required value missing in column \"{col}\"")



# [CONTENT] Framework
def validate_framework_content(df, sheet_name):
    fct_name = validate_framework_content.__name__
    required_columns = ["depth"]  # "assessable" isn't there because it can be empty
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    
    # Enforce presence of "assessable" column (even if values can be empty)
    if "assessable" not in df.columns:
        raise ValueError(f"[{fct_name}] [{sheet_name}] Missing required column \"assessable\"")

    # Additional rule: for non-empty rows, at least one of "ref_id" or "name" must be filled
    for idx, row in df.iterrows():
        if row.dropna().empty:
            continue  # skip completely empty rows

        ref_id = str(row.get("ref_id", "")).strip()
        name = str(row.get("name", "")).strip()

        if not ref_id and not name:
            raise ValueError(
                f"({fct_name}) [{sheet_name}] Row #{idx + 2}: Invalid row: Both \"ref_id\" and \"name\" are empty"
                "\n💡 Tip: At least one of them must be filled."
            )

    print_sheet_validation(sheet_name)


# [CONTENT] Threats
def validate_threats_content(df, sheet_name):
    fct_name = validate_threats_content.__name__
    required_columns = ["ref_id"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)


# [CONTENT] Reference Controls
def validate_reference_controls_content(df, sheet_name):
    fct_name = validate_reference_controls_content.__name__
    required_columns = ["ref_id"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)


# [CONTENT] Risk Matrix
def validate_risk_matrix_content(df, sheet_name):
    fct_name = validate_risk_matrix_content.__name__
    required_columns = ["type", "id", "color", "abbreviation", "name", "description", "grid"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)


# [CONTENT] Implementation Groups
def validate_implementation_groups_content(df, sheet_name):
    fct_name = validate_implementation_groups_content.__name__
    required_columns = ["ref_id", "name"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)


# [CONTENT] Requirement Mapping Set
def validate_requirement_mapping_set_content(df, sheet_name):
    fct_name = validate_requirement_mapping_set_content.__name__
    required_columns = ["source_node_id", "target_node_id", "relationship"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)


# [CONTENT] Scores
def validate_scores_content(df, sheet_name):
    fct_name = validate_scores_content.__name__
    required_columns = ["score", "name", "description"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)


# [CONTENT] Answers
def validate_answers_content(df, sheet_name):
    fct_name = validate_answers_content.__name__
    required_columns = ["id", "question_type"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)


# [CONTENT] URN Prefix
def validate_urn_prefix_content(df, sheet_name):
    fct_name = validate_urn_prefix_content.__name__
    required_columns = ["prefix_id", "prefix_value"]
    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    print_sheet_validation(sheet_name)



# ─────────────────────────────────────────────────────────────
# DISPATCHING
# ─────────────────────────────────────────────────────────────

def dispatch_meta_validation(df, sheet_name):
    
    fct_name = dispatch_meta_validation.__name__
    
    type_row = df[df.iloc[:, 0] == "type"]
    if type_row.empty:
        raise ValueError(f"({fct_name}) [{sheet_name}] Missing or empty \"type\" field in meta sheet")
    type_value = type_row.iloc[0, 1]
    if type_value == "library":
        validate_library_meta(df, sheet_name)
    elif type_value == "framework":
        validate_framework_meta(df, sheet_name)
    elif type_value == "threats":
        validate_threats_meta(df, sheet_name)
    elif type_value == "reference_controls":
        validate_reference_controls_meta(df, sheet_name)
    elif type_value == "risk_matrix":
        validate_risk_matrix_meta(df, sheet_name)
    elif type_value == "requirement_mapping_set":
        validate_requirement_mapping_set_meta(df, sheet_name)
    elif type_value == "implementation_groups":
        validate_implementation_groups_meta(df, sheet_name)
    elif type_value == "scores":
        validate_scores_meta(df, sheet_name)
    elif type_value == "answers":
        validate_answers_meta(df, sheet_name)
    elif type_value == "urn_prefix":
        validate_urn_prefix_meta(df, sheet_name)
    else:
        raise ValueError(f"({fct_name}) [{sheet_name}] Unknown meta type \"{type_value}\"")


def dispatch_content_validation(df, sheet_name, corresponding_meta_type):
    
    fct_name = dispatch_content_validation.__name__
    
    if corresponding_meta_type == "framework":
        validate_framework_content(df, sheet_name)
    elif corresponding_meta_type == "threats":
        validate_threats_content(df, sheet_name)
    elif corresponding_meta_type == "reference_controls":
        validate_reference_controls_content(df, sheet_name)
    elif corresponding_meta_type == "risk_matrix":
        validate_risk_matrix_content(df, sheet_name)
    elif corresponding_meta_type == "requirement_mapping_set":
        validate_requirement_mapping_set_content(df, sheet_name)
    elif corresponding_meta_type == "implementation_groups":
        validate_implementation_groups_content(df, sheet_name)
    elif corresponding_meta_type == "scores":
        validate_scores_content(df, sheet_name)
    elif corresponding_meta_type == "answers":
        validate_answers_content(df, sheet_name)
    elif corresponding_meta_type == "urn_prefix":
        validate_urn_prefix_content(df, sheet_name)
    else:
        raise ValueError(f"({fct_name}) [{sheet_name}] Cannot determine validation for content of type \"{corresponding_meta_type}\"")


# ─────────────────────────────────────────────────────────────
# MAIN VALIDATION FUNCTION
# ─────────────────────────────────────────────────────────────

def validate_excel_structure(filepath):
    
    wb = load_workbook(filepath, data_only=True)
    fct_name = validate_excel_structure.__name__
    file_name = os.path.basename(filepath)

    meta_sheets = {}
    content_sheets = {}
    ignored_sheets = []
    meta_types = {}

    # Sort sheets
    for sheet_name in wb.sheetnames:
        if sheet_name.endswith("_meta"):
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
            meta_sheets[sheet_name] = df
        elif sheet_name.endswith("_content"):
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=0)
            content_sheets[sheet_name] = df
        else:
            ignored_sheets.append(sheet_name)

    # Handle "_meta" sheets
    for sheet_name, df in meta_sheets.items():
        dispatch_meta_validation(df, sheet_name)
        type_row = df[df.iloc[:, 0] == "type"]
        meta_types[sheet_name.replace("_meta", "")] = str(type_row.iloc[0, 1]).strip()

    # Handle "_content" sheets
    for sheet_name, df in content_sheets.items():
        base_name = sheet_name.replace("_content", "")
        if base_name not in meta_types:
            raise ValueError(f"({fct_name}) [{sheet_name}] No corresponding meta sheet found for this content")
        dispatch_content_validation(df, sheet_name, meta_types[base_name])

    # Warn about ignored sheets
    for sheet_name in ignored_sheets:
        print(f"⚠️  [WARNING] Ignored sheet \"{sheet_name}\" (does not end with \"_meta\" or \"_content\")")

    print(f"✅ Excel structure is valid for \"{file_name}\"")


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate Excel file structure (v2 format)")
    parser.add_argument("filepath", help="Path to Excel file to validate")
    args = parser.parse_args()
    
    try:
        validate_excel_structure(args.filepath)
    except Exception as e:
        print(f"❌ [FATAL ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
