import os
import re
import sys
import inspect
import argparse
from typing import Dict, List

import pandas as pd
from openpyxl import load_workbook



# ─────────────────────────────────────────────────────────────
# CLASSES
# ─────────────────────────────────────────────────────────────

class ConsoleContext:
    
    def __init__(self):
        
        self.warning_messages: Dict[str, List] = {}
        self.verbose_messages: Dict[str, List] = {}


    # Getters 
    
    def get_function_warning_msg(self, function_name: str) -> List[str]:
        return self.warning_messages.get(function_name)
    
    def get_function_verbose_msg(self, function_name: str) -> List[str]:
        return self.verbose_messages.get(function_name)
    
    def get_all_warning_msg(self) -> Dict[str, List]:
        return self.warning_messages
    
    def get_all_verbose_msg(self) -> Dict[str, List]:
        return self.verbose_messages


    # Setters

    def add_function_warning_msg(self, function_name: str, msg: str):
        
        if function_name in self.warning_messages:
            self.warning_messages[function_name].append(msg)
        else:
            self.warning_messages[function_name] = [msg]
        return
    
    def add_function_verbose_msg(self, function_name: str, msg):
        
        if function_name in self.verbose_messages:
            self.verbose_messages[function_name].append(msg)
        else:
            self.verbose_messages[function_name] = [msg]
        return


    # Counters (Global)

    def count_all_warnings(self) -> int:
        """Return total number of warning messages."""
        return sum(len(msgs) for msgs in self.warning_messages.values())

    def count_all_verbose(self) -> int:
        """Return total number of verbose messages."""
        return sum(len(msgs) for msgs in self.verbose_messages.values())

    # Counters (Per function)

    def count_warnings_for_function(self, function_name: str) -> int:
        """Return number of warning messages for a function (0 if none exist)."""
        return len(self.warning_messages.get(function_name, []))

    def count_verbose_for_function(self, function_name: str) -> int:
        """Return number of verbose messages for a function (0 if none exist)."""
        return len(self.verbose_messages.get(function_name, []))

    # Aggregators by function

    def get_warning_count_by_function(self) -> Dict[str, int]:
        """Return dict {function_name: warning count}, including 0 where applicable."""
        return {fn: len(self.warning_messages.get(fn, [])) for fn in self._all_function_names}

    def get_verbose_count_by_function(self) -> Dict[str, int]:
        """Return dict {function_name: verbose count}, including 0 where applicable."""
        return {fn: len(self.verbose_messages.get(fn, [])) for fn in self._all_function_names}



# ─────────────────────────────────────────────────────────────
# MISC
# ─────────────────────────────────────────────────────────────

def get_current_fct_name():
    return inspect.stack()[1][3]



# ─────────────────────────────────────────────────────────────
# VALIDATE UTILS
# ─────────────────────────────────────────────────────────────

def validate_urn(urn: str, context: str = None, row = None):
    pattern = r"^urn:([a-z0-9._-]+:)*[a-z0-9._-]+$"
    if not re.fullmatch(pattern, urn):
        raise ValueError(f"({context if context else 'validate_urn'}) {'Row #'+str(row+2)+':' if row else ""} Invalid URN \"{urn}\" : Only lowercase alphanumeric characters, '-', '_', and '.' are allowed")

def validate_ref_id(ref_id: str, context: str = None, row = None):
    if not re.fullmatch(r"[a-zA-Z0-9._\- ]+", ref_id):
        raise ValueError(f"({context if context else 'validate_ref_id'}) {'Row #'+str(row+2)+':' if row else ""} Invalid Ref. ID \"{ref_id}\" : Only alphanumeric characters, '-', '_', and '.' are allowed")

def validate_sheet_name(sheet_name: str, context: str = None):
    if not (sheet_name.endswith("_meta") or sheet_name.endswith("_content")):
        raise ValueError(f"({context if context else 'validate_sheet_name'}) Invalid sheet name \"{sheet_name}\". Sheet names must end with '_meta' or '_content'")

def is_valid_locale(locale_str):
    return bool(re.fullmatch(r"[a-z0-9]{2}", locale_str))

def print_sheet_validation(sheet_name: str, function_name: str = None, verbose: bool = False, ctx: ConsoleContext = None):
        
    if not ctx:
        
        print(f"🟢 [CHECK] Valid sheet: \"{sheet_name}\"")
        
        if verbose:
            print(f"ℹ️   [INFO] Check for warning / verbose messages in the console, if any")
        else:
            print(f"ℹ️   [INFO] Check for warnings in the console, if any")
    else:
        
        if not function_name:
            raise ValueError(f"({print_sheet_validation.__name__}) \"function_name\" must be defined")
        
        function_warnings = ctx.get_function_warning_msg(function_name)
        function_verbose = ctx.get_function_verbose_msg(function_name)
        
        if verbose:
            if function_warnings:
                if function_verbose:
                    print(f"🟣 [CHECK] Valid sheet with warnings and verbose messages : \"{sheet_name}\" (Warn: {len(function_warnings)} / Verb: {len(function_verbose)})")
                else:
                    print(f"🟡 [CHECK] Valid sheet with warnings: \"{sheet_name}\" (Warn: {len(function_warnings)} / Verb: 0)")
            else:
                if function_verbose:
                    print(f"🔵 [CHECK] Valid sheet with verbose messages : \"{sheet_name}\" (Warn: 0 / Verb: {len(function_verbose)})")
                else:
                    print(f"🟢 [CHECK] Valid sheet: \"{sheet_name}\"")   
        else:
            if function_warnings:
                print(f"🟡 [CHECK] Valid sheet with warnings: \"{sheet_name}\" (Warn: {len(function_warnings)})")
            else:
                print(f"🟢 [CHECK] Valid sheet: \"{sheet_name}\"")


# ─────────────────────────────────────────────────────────────
# VALIDATE META SHEETS
# ─────────────────────────────────────────────────────────────


# Global Checks ("type" value is checked by default)
def validate_meta_sheet(df, sheet_name: str, expected_keys:List[str], expected_type: str, context: str):
    
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
    

def validate_optional_values_meta_sheet(df, sheet_name: str, optional_keys: List[str], context: str, verbose: bool = False, ctx: ConsoleContext = None):

    if not optional_keys:
        return
    
    for key in optional_keys:
        matches = df[df.iloc[:, 0] == key]
        
        if not matches.empty:
            row_index = matches.index[0]
            value = matches.iloc[0, 1] if matches.shape[1] > 1 else None

            if pd.isna(value) or str(value).strip() == "":
                msg = (f"⚠️  [WARNING] ({context}) [{sheet_name}] Row #{row_index + 1}: Optional key \"{key}\" is present but has no value"
                        "\n💡 Tip: If you don't need this key, you can simply remove it from the sheet.")
                if ctx:
                    ctx.add_function_warning_msg(context, msg)
                print(msg)

        else:
            if verbose:
                msg = f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] Missing optional key \"{key}\" in meta sheet"
                
                if ctx:
                    ctx.add_function_verbose_msg(context, msg)
                print(msg)



# [META] Library
def validate_library_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "library"
    fct_name = get_current_fct_name()
    
    expected_keys = [
        "urn", "version", "locale", "ref_id", "name",
        "description", "copyright", "provider", "packager"
    ]
    optional_keys = ["dependencies"]

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    validate_optional_values_meta_sheet(df, sheet_name, optional_keys, fct_name, verbose, ctx)

    # URN
    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    validate_urn(urn_value, fct_name)

    # ref_id
    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    validate_ref_id(ref_id_value, context=fct_name)

    # version
    version_value = df[df.iloc[:, 0] == "version"].iloc[0, 1]
    try:
        version_int = int(str(version_value).strip())
        if version_int <= 0:
            raise ValueError
    except Exception:
        raise ValueError(f"({fct_name}) [{sheet_name}] Invalid \"version\": must be a positive non-zero integer, got \"{version_value}\"")

    # locale
    locale_value = str(df[df.iloc[:, 0] == "locale"].iloc[0, 1]).strip()
    if not is_valid_locale(locale_value):
        raise ValueError(
            f"({fct_name}) [{sheet_name}] Invalid \"locale\" value: \"{locale_value}\""
            "\n💡 Tip: Locale setting must comply with ISO 639 Set 1 (e.g., \"en\", \"fr\"). See https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes")

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Framework
def validate_framework_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "framework"
    fct_name = get_current_fct_name()
    expected_keys = [
        "urn", "ref_id", "name", "description", "base_urn"
    ]
    optional_keys = [
        "min_score", "max_score", "scores_definition",
        "implementation_groups_definition", "answers_definition"
    ]
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    validate_optional_values_meta_sheet(df, sheet_name, optional_keys, fct_name, verbose, ctx)

    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    validate_urn(urn_value, fct_name)

    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    validate_ref_id(ref_id_value, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Threats
def validate_threats_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "threats"
    fct_name = get_current_fct_name()
    expected_keys = ["base_urn"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Reference Controls
def validate_reference_controls_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "reference_controls"
    fct_name = get_current_fct_name()
    expected_keys = ["base_urn"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Risk Matrix
def validate_risk_matrix_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "risk_matrix"
    fct_name = get_current_fct_name()
    expected_keys = ["urn", "ref_id", "name", "description"]
    # No optional keys

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    validate_urn(urn_value, fct_name)

    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    validate_ref_id(ref_id_value, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Implementation Groups
def validate_implementation_groups_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "implementation_groups"
    fct_name = get_current_fct_name()
    expected_keys = ["name"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Mappings
def validate_requirement_mapping_set_meta(df, sheet_name, verbose, ctx: ConsoleContext = None):
    
    expected_type = "requirement_mapping_set"
    fct_name = get_current_fct_name()
    expected_keys = [
        "source_framework_urn",
        "source_node_base_urn",
        "target_framework_urn",
        "target_node_base_urn"
    ]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Scores
def validate_scores_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "scores"
    fct_name = get_current_fct_name()
    expected_keys = ["name"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] Answers
def validate_answers_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "answers"
    fct_name = get_current_fct_name()
    expected_keys = ["name"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [META] URN Prefix
def validate_urn_prefix_meta(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "urn_prefix"
    fct_name = get_current_fct_name()
    # No "expected_keys" because only  "type" is required
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, None, expected_type, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)



# ─────────────────────────────────────────────────────────────
# VALIDATE CONTENT SHEETS
# ─────────────────────────────────────────────────────────────


# Global Checks
def validate_content_sheet(df, sheet_name: str, required_columns: List[str], context: str):
    
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

                if col in ["ref_id", "id"]:
                    validate_ref_id(value, context, idx)


def validate_optional_columns_content_sheet(df, sheet_name: str, optional_columns: List[str], context: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    for col in optional_columns:
        
        # If optional column missing
        if col not in df.columns:
            if verbose:
                msg = f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] Missing optional column \"{col}\" in meta sheet"
                
                if ctx:
                    ctx.add_function_verbose_msg(context, msg)
                print(msg)
                
            continue

        # Check if the entire column is empty (i.e., all values are NaN or blank)
        is_entirely_empty = all(pd.isna(val) or str(val).strip() == "" for val in df[col])

        if is_entirely_empty:
            msg = (f"⚠️  [WARNING] ({context}) [{sheet_name}] Optional column \"{col}\" is present but entirely empty"
                    "\n💡 Tip: If you don't need this column, you can simply remove it from the sheet.")
            if ctx:
                ctx.add_function_warning_msg(context, msg)
            print(msg)



# [CONTENT] Framework
def validate_framework_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):

    fct_name = get_current_fct_name()
    required_columns = ["depth"]  # "assessable" isn't there because it can be empty
    optional_columns = [
        "implementation_groups", "description", "threats",
        "reference_controls", "typical_evidence", "annotation",
        "questions", "answer", "urn_id"
    ]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)
    
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

        if ref_id:
            validate_ref_id(ref_id, fct_name, idx)

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] Threats
def validate_threats_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["ref_id"]
    optional_columns = ["description", "annotation"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] Reference Controls
def validate_reference_controls_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["ref_id"]
    optional_columns = ["description", "category", "csf_function", "annotation"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] Risk Matrix
def validate_risk_matrix_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["type", "id", "color", "abbreviation", "name", "description", "grid"]
    # No optional columns

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] Implementation Groups
def validate_implementation_groups_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["ref_id", "name"]
    optional_columns = ["description"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] Requirement Mapping Set
def validate_requirement_mapping_set_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["source_node_id", "target_node_id", "relationship"]
    optional_columns = ["rationale", "strength_of_relationship"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] Scores
def validate_scores_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["score", "name", "description"]
    optional_columns = ["description_doc"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] Answers
def validate_answers_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["id", "question_type"]
    optional_columns = ["question_choices"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    print_sheet_validation(sheet_name, fct_name, verbose, ctx)


# [CONTENT] URN Prefix
def validate_urn_prefix_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["prefix_id", "prefix_value"]
    # No optional columns

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    
    print_sheet_validation(sheet_name, fct_name, verbose, ctx)



# ─────────────────────────────────────────────────────────────
# DISPATCHING
# ─────────────────────────────────────────────────────────────

def dispatch_meta_validation(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = dispatch_meta_validation.__name__
    
    type_row = df[df.iloc[:, 0] == "type"]
    if type_row.empty:
        raise ValueError(f"({fct_name}) [{sheet_name}] Missing or empty \"type\" field in meta sheet")
    type_value = type_row.iloc[0, 1]
    if type_value == "library":
        validate_library_meta(df, sheet_name, verbose, ctx)
    elif type_value == "framework":
        validate_framework_meta(df, sheet_name, verbose, ctx)
    elif type_value == "threats":
        validate_threats_meta(df, sheet_name, verbose, ctx)
    elif type_value == "reference_controls":
        validate_reference_controls_meta(df, sheet_name, verbose, ctx)
    elif type_value == "risk_matrix":
        validate_risk_matrix_meta(df, sheet_name, verbose, ctx)
    elif type_value == "requirement_mapping_set":
        validate_requirement_mapping_set_meta(df, sheet_name, verbose, ctx)
    elif type_value == "implementation_groups":
        validate_implementation_groups_meta(df, sheet_name, verbose, ctx)
    elif type_value == "scores":
        validate_scores_meta(df, sheet_name, verbose, ctx)
    elif type_value == "answers":
        validate_answers_meta(df, sheet_name, verbose, ctx)
    elif type_value == "urn_prefix":
        validate_urn_prefix_meta(df, sheet_name, verbose, ctx)
    else:
        raise ValueError(f"({fct_name}) [{sheet_name}] Unknown meta type \"{type_value}\"")


def dispatch_content_validation(df, sheet_name, corresponding_meta_type, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = dispatch_content_validation.__name__
    
    if corresponding_meta_type == "framework":
        validate_framework_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "threats":
        validate_threats_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "reference_controls":
        validate_reference_controls_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "risk_matrix":
        validate_risk_matrix_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "requirement_mapping_set":
        validate_requirement_mapping_set_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "implementation_groups":
        validate_implementation_groups_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "scores":
        validate_scores_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "answers":
        validate_answers_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == "urn_prefix":
        validate_urn_prefix_content(df, sheet_name, verbose, ctx)
    else:
        raise ValueError(f"({fct_name}) [{sheet_name}] Cannot determine validation for content of type \"{corresponding_meta_type}\"")


# ─────────────────────────────────────────────────────────────
# MAIN VALIDATION FUNCTION
# ─────────────────────────────────────────────────────────────

def validate_excel_structure(filepath, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    
    if not ctx:
        ctx = ConsoleContext()
    
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
        dispatch_meta_validation(df, sheet_name, verbose, ctx)
        type_row = df[df.iloc[:, 0] == "type"]
        meta_types[sheet_name.replace("_meta", "")] = str(type_row.iloc[0, 1]).strip()

    # Handle "_content" sheets
    for sheet_name, df in content_sheets.items():
        base_name = sheet_name.replace("_content", "")
        if base_name not in meta_types:
            raise ValueError(f"({fct_name}) [{sheet_name}] No corresponding meta sheet found for this content")
        dispatch_content_validation(df, sheet_name, meta_types[base_name], verbose, ctx)

    # Warn about ignored sheets
    for sheet_name in ignored_sheets:
        warn_msg = f"⚠️  [WARNING] Ignored sheet \"{sheet_name}\" (does not end with \"_meta\" or \"_content\")"
        print(warn_msg)
        ctx.add_function_warning_msg(fct_name, warn_msg)

    print("")
    print(f"✅ [SUCCESS] Excel structure is valid for \"{file_name}\"")
    
    if ctx.count_all_warnings() > 0:
        print(f"📜 [SUMMARY] ⚠️  Total [WARNING] for \"{file_name}\": {ctx.count_all_warnings()}")
    
    if verbose and ctx.count_all_verbose() > 0:
        print(f"💬📜 [SUMMARY] ℹ️  Total [Verbose Messages] for \"{file_name}\": {ctx.count_all_verbose()}")
    
    


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate Excel file structure (v2 format)")
    parser.add_argument("filepath", help="Path to Excel file to validate")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output. Verbose messages start with a 💬 (speech bubble) emoji.")
    args = parser.parse_args()
    
    ctx = ConsoleContext()
    
    try:
        validate_excel_structure(args.filepath, args.verbose, ctx)
    except Exception as e:
        print(f"❌ [FATAL ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
