import os
import re
import sys
import inspect
import argparse
from enum import Enum
from collections import Counter
from typing import Dict, List, Tuple

import pandas as pd
from openpyxl import Workbook, load_workbook



# ─────────────────────────────────────────────────────────────
# CLASSES
# ─────────────────────────────────────────────────────────────

class ConsoleContext:
    
    def __init__(self):
        
        self.warning_messages: Dict[str, List] = {}
        self.verbose_messages: Dict[str, List] = {}


    # Getters 
    
    def get_sheet_warning_msg(self, sheet_name: str) -> List[str]:
        return self.warning_messages.get(sheet_name)
    
    def get_sheet_verbose_msg(self, sheet_name: str) -> List[str]:
        return self.verbose_messages.get(sheet_name)
    
    def get_all_warning_msg(self) -> Dict[str, List]:
        return self.warning_messages
    
    def get_all_verbose_msg(self) -> Dict[str, List]:
        return self.verbose_messages


    # Setters

    def add_sheet_warning_msg(self, sheet_name: str, msg: str):
        
        if sheet_name in self.warning_messages:
            self.warning_messages[sheet_name].append(msg)
        else:
            self.warning_messages[sheet_name] = [msg]
        return
    
    def add_sheet_verbose_msg(self, sheet_name: str, msg):
        
        if sheet_name in self.verbose_messages:
            self.verbose_messages[sheet_name].append(msg)
        else:
            self.verbose_messages[sheet_name] = [msg]
        return


    # Counters (Global)

    def count_all_warnings(self) -> int:
        """Return total number of warning messages."""
        return sum(len(msgs) for msgs in self.warning_messages.values())

    def count_all_verbose(self) -> int:
        """Return total number of verbose messages."""
        return sum(len(msgs) for msgs in self.verbose_messages.values())

    # Counters (Per sheet)

    def count_warnings_for_sheet(self, sheet_name: str) -> int:
        """Return number of warning messages for a sheet (0 if none exist)."""
        return len(self.warning_messages.get(sheet_name, []))

    def count_verbose_for_sheet(self, sheet_name: str) -> int:
        """Return number of verbose messages for a sheet (0 if none exist)."""
        return len(self.verbose_messages.get(sheet_name, []))

    # Aggregators by sheet

    def get_warning_count_by_sheet(self) -> Dict[str, int]:
        """Return dict {sheet_name: warning count}, including 0 where applicable."""
        return {fn: len(self.warning_messages.get(fn, [])) for fn in self._all_sheet_names}

    def get_verbose_count_by_sheet(self) -> Dict[str, int]:
        """Return dict {sheet_name: verbose count}, including 0 where applicable."""
        return {fn: len(self.verbose_messages.get(fn, [])) for fn in self._all_sheet_names}


class MetaTypes(Enum):
    LIBRARY                 = "library"
    FRAMEWORK               = "framework"
    THREATS                 = "threats"
    REFERENCE_CONTROLS      = "reference_controls"
    RISK_MATRIX             = "risk_matrix"
    REQUIREMENT_MAPPING_SET = "requirement_mapping_set"
    IMPLEMENTATION_GROUPS   = "implementation_groups"
    SCORES                  = "scores"
    ANSWERS                 = "answers"
    URN_PREFIX              = "urn_prefix"



# ─────────────────────────────────────────────────────────────
# MISC
# ─────────────────────────────────────────────────────────────

# Get the name of the calling function
def get_current_fct_name():
    return inspect.stack()[1][3]


def get_meta_sheets_with_type(wb: Workbook) -> Dict[str, str]:
    """
    Return a dictionary of all sheets ending with '_meta' and their corresponding type value.
    Format: {sheet_name: type_value}
    """
    
    meta_sheets_with_type = {}

    for sheet_name in wb.sheetnames:
        if not sheet_name.endswith("_meta"):
            continue

        ws = wb[sheet_name]
        df = pd.DataFrame(ws.values)

        if df.shape[1] < 2:
            continue  # not enough columns to contain key/value pairs

        # Find row where first column == 'type'
        type_rows = df[df.iloc[:, 0] == "type"]

        if not type_rows.empty:
            type_value = str(type_rows.iloc[0, 1]).strip()
            meta_sheets_with_type[sheet_name] = type_value

    return meta_sheets_with_type


def get_meta_sheets_names_from_type(wb: Workbook, sheet_type: MetaTypes) -> List[str]:

    meta_sheets = get_meta_sheets_with_type(wb)
    sheets = []

    for sheet, sht_type in meta_sheets.items():
        if sht_type != sheet_type.value:
            continue

        sheets.append(sheet)

    return sheets


# Retrieve the value associated with a given key in a meta sheet (2-column format).
def get_meta_value(df, key_name: str, sheet_name: str, required: bool = False):
    
    matches = df[df.iloc[:, 0] == key_name]

    if matches.empty:
        if required:
            raise ValueError(f"[{sheet_name}] Missing required key \"{key_name}\" in meta sheet.")
        return None

    value = matches.iloc[0, 1]
    if pd.isna(value) or str(value).strip() == "":
        if required:
            raise ValueError(f"[{sheet_name}] Key \"{key_name}\" is present but has an empty value.")
        return None

    return str(value).strip()


# Return a list of non-empty, stripped string values from a specified column in a DataFrame.
def get_non_empty_column_values(df: pd.DataFrame, column_name: str) -> List[str]:

    if column_name not in df.columns:
        raise ValueError(f"Column \"{column_name}\" not found in DataFrame")

    return [
        str(value).strip()
        for value in df[column_name]
        if pd.notna(value) and str(value).strip() != ""
    ]



# ─────────────────────────────────────────────────────────────
# VALIDATE UTILS
# ─────────────────────────────────────────────────────────────

def validate_urn(urn: str, context: str = None, row = None):
    pattern = r"^urn:([a-z0-9._-]+:)*[a-z0-9._-]+$"
    if not re.fullmatch(pattern, urn):
        raise ValueError(f"({context if context else 'validate_urn'}) {'Row #'+str(row)+':' if row else ""} Invalid URN \"{urn}\" : Only lowercase alphanumeric characters, '-', '_', and '.' are allowed")

def validate_ref_id(ref_id: str, context: str = None, row = None):
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", ref_id):
        raise ValueError(f"({context if context else 'validate_ref_id'}) {'Row #'+str(row)+':' if row else ""} Invalid Ref. ID \"{ref_id}\" : Only alphanumeric characters, '-', '_', and '.' are allowed")

def validate_ref_id_with_spaces(ref_id: str, context: str = None, row = None):
    if not re.fullmatch(r"[a-zA-Z0-9._\- ]+", ref_id):
        raise ValueError(f"({context if context else 'validate_ref_id'}) {'Row #'+str(row)+':' if row else ""} Invalid Ref. ID \"{ref_id}\" : Only alphanumeric characters, '-', '_', ' ', and '.' are allowed")

def validate_sheet_name(sheet_name: str, context: str = None):
    if not (sheet_name.endswith("_meta") or sheet_name.endswith("_content")):
        raise ValueError(f"({context if context else 'validate_sheet_name'}) Invalid sheet name \"{sheet_name}\". Sheet names must end with '_meta' or '_content'")

def is_valid_locale(locale_str):
    return bool(re.fullmatch(r"[a-z0-9]{2}", locale_str))

def validate_no_spaces(value: str, value_name: str, context: str = None, row: int = None):
    if " " in str(value):
        raise ValueError(f"({context if context else 'validate_no_spaces'}) {'Row #' + str(row) + ':' if row is not None else ''} Invalid value for \"{value_name}\": Spaces are not allowed (got \"{value}\")")

def print_sheet_validation(sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
        
    if not ctx:
        
        print(f"🟢 [CHECK] Valid sheet: \"{sheet_name}\"")
        
        if verbose:
            print(f"ℹ️   [INFO] Check for warning / verbose messages in the console, if any")
        else:
            print(f"ℹ️   [INFO] Check for warnings in the console, if any")
    else:
        
        sheet_warnings = ctx.get_sheet_warning_msg(sheet_name)
        sheet_verbose = ctx.get_sheet_verbose_msg(sheet_name)
        
        if verbose:
            if sheet_warnings:
                if sheet_verbose:
                    print(f"🟣 [CHECK] Valid sheet with warnings and verbose messages : \"{sheet_name}\" (Warn: {len(sheet_warnings)} / Verb: {len(sheet_verbose)})")
                else:
                    print(f"🟡 [CHECK] Valid sheet with warnings: \"{sheet_name}\" (Warn: {len(sheet_warnings)} / Verb: 0)")
            else:
                if sheet_verbose:
                    print(f"🔵 [CHECK] Valid sheet with verbose messages : \"{sheet_name}\" (Warn: 0 / Verb: {len(sheet_verbose)})")
                else:
                    print(f"🟢 [CHECK] Valid sheet: \"{sheet_name}\"")   
        else:
            if sheet_warnings:
                print(f"🟡 [CHECK] Valid sheet with warnings: \"{sheet_name}\" (Warn: {len(sheet_warnings)})")
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
                raise ValueError(f"({context}) [{sheet_name}] Row #{row_index + 1}: Optional key \"{key}\" is present but has no value"
                                  "\n> 💡 Tip: If you don't need this key, you can simply remove it from the sheet.")

        else:
            if verbose:
                msg = f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] Missing optional key \"{key}\" in meta sheet"
                
                if ctx:
                    ctx.add_sheet_verbose_msg(sheet_name, msg)
                print(msg)


def validate_extra_locales_in_meta(df, sheet_name: str, context: str):

    keys = df.iloc[:, 0].dropna().astype(str)

    for key in keys:
        match = re.fullmatch(r"(.+)\[(.+)\]", key)  # Match "value_name[locale]"
        if not match:
            continue
        
        base_key, locale = match.groups()
        row_index = df[df.iloc[:, 0] == key].index[0]  # Get the row index of the localized key

        # Validate locale format
        if not is_valid_locale(locale):
            raise ValueError(
                f"({context}) [{sheet_name}] Row #{row_index + 1}: Invalid locale \"{locale}\" in key \"{key}\""
                "\n> 💡 Tip: Locale setting must comply with ISO 639 Set 1 (e.g., \"en\", \"fr\"). See https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes"
            )

        # Check if base key exists in the meta sheet
        if base_key not in df.iloc[:, 0].values:
            raise ValueError(
                f"({context}) [{sheet_name}] Row #{row_index + 1}: Localized key \"{key}\" found, but base key \"{base_key}\" is missing"
                f"\n> 💡 Tip: Add the base key \"{base_key}\" or simply remove the key \"{key}\"."
            )

        # Check that the localized value is not empty
        row = df[df.iloc[:, 0] == key]
        value = row.iloc[0, 1] if row.shape[1] > 1 else None
        if pd.isna(value) or str(value).strip() == "":
            raise ValueError(
                f"({context}) [{sheet_name}] Row #{row_index + 1}: Localized key \"{key}\" is present but has no value"
                "\n> 💡 Tip: If you don't need this key, you can simply remove it from the sheet."
            )


# Check that if the "name" key exists and has a value, and if the corresponding "<name>_content" sheet exists.
def validate_related_content_sheet_from_name_key(wb: Workbook, df, sheet_name: str, context: str):

    key_row = df[df.iloc[:, 0] == "name"]
    if key_row.empty:
        return  # 'name' key is not present, skip check

    value = str(key_row.iloc[0, 1]).strip()
    row = key_row.index[0] + 1
    if not value:
        return  # value is empty, skip check

    expected_sheet = f"{value}_content"
    if expected_sheet not in wb.sheetnames:
        raise ValueError(
            f"({context}) [{sheet_name}] Row #{row}: Key \"name\" points to missing sheet starting with \"{value}\" (Missing \"{expected_sheet}\")"
            f"\n> 💡 Tip: Make sure the \"{expected_sheet}\" sheet exists or set the right value for key \"name\"."
        )



# [META] Library {OK}
def validate_library_meta(df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
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
    urn_row = df[df.iloc[:, 0] == "urn"].index[0] + 1 
    validate_urn(urn_value, fct_name, urn_row)

    # ref_id
    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    ref_id_row = df[df.iloc[:, 0] == "ref_id"].index[0] + 1
    validate_ref_id(ref_id_value, fct_name, ref_id_row)

    # version
    version_value = df[df.iloc[:, 0] == "version"].iloc[0, 1]
    version_row = df[df.iloc[:, 0] == "version"].index[0] + 1
    try:
        version_int = int(str(version_value).strip())
        if version_int <= 0:
            raise ValueError
    except Exception:
        raise ValueError(f"({fct_name}) [{sheet_name}] Row #{version_row}: Invalid \"version\": must be a positive non-zero integer, got \"{version_value}\"")

    # locale
    locale_value = str(df[df.iloc[:, 0] == "locale"].iloc[0, 1]).strip()
    locale_row = df[df.iloc[:, 0] == "locale"].index[0] + 1
    if not is_valid_locale(locale_value):
        raise ValueError(
            f"({fct_name}) [{sheet_name}] Row #{locale_row}: Invalid \"locale\" value: \"{locale_value}\""
            "\n> 💡 Tip: Locale setting must comply with ISO 639 Set 1 (e.g., \"en\", \"fr\"). See https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes")

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Framework {OK}
def validate_framework_meta(wb: Workbook, df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
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

    # URN
    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    urn_row = df[df.iloc[:, 0] == "urn"].index[0] + 1
    validate_urn(urn_value, fct_name, urn_row)

    # base_urn
    base_urn_value = df[df.iloc[:, 0] == "base_urn"].iloc[0, 1]
    base_urn_row = df[df.iloc[:, 0] == "base_urn"].index[0] + 1
    validate_urn(base_urn_value, fct_name, base_urn_row)

    # ref_id
    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    ref_id_row = df[df.iloc[:, 0] == "ref_id"].index[0] + 1
    validate_ref_id(ref_id_value, fct_name, ref_id_row)
    
    # Check that *_definition keys (if present) point to an existing *_meta sheet
    for def_key in ["implementation_groups_definition", "answers_definition", "scores_definition"]:
        matches = df[df.iloc[:, 0] == def_key]
        if matches.empty:
            continue

        value = str(matches.iloc[0, 1]).strip()
        if not value:
            continue

        expected_sheet = f"{value}_meta"
        if expected_sheet in wb.sheetnames:
            continue

        row = matches.index[0] + 1
        sheet_type = def_key.split('_')[0]
        raise ValueError(
            f"({fct_name}) [{sheet_name}] Row #{row}: Key \"{def_key}\" points to missing sheet starting with \"{value}\" (Missing \"{expected_sheet}\")"
            f"\n> 💡 Tip: Make sure \"{sheet_type}\" sheets start with \"{value}\", set the right value for key \"{def_key}\" or simply remove the key \"{def_key}\"."
        )
        
    # Validate min_score and max_score if present
    min_score = None
    max_score = None

    for key in ["min_score", "max_score"]:
        matches = df[df.iloc[:, 0] == key]
        if matches.empty:
            continue

        value_str = str(matches.iloc[0, 1]).strip()
        row = matches.index[0] + 1

        if not value_str.isdigit():
            raise ValueError(f"({fct_name}) [{sheet_name}] Row #{row}: Key \"{key}\" must be a non-negative integer, got \"{value_str}\"")

        value = int(value_str)
        if value < 0:
            raise ValueError(f"({fct_name}) [{sheet_name}] Row #{row}: Key \"{key}\" must be >= 0, got \"{value}\"")

        if key == "min_score":
            min_score = value
        else:
            max_score = value

    # Validate min <= max if both are present
    if min_score is not None and max_score is not None:
        if min_score > max_score:
            raise ValueError(f"({fct_name}) [{sheet_name}] Invalid score range: 'min_score' ({min_score}) must be less than or equal to 'max_score' ({max_score})")

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Threats {OK}
def validate_threats_meta(df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "threats"
    fct_name = get_current_fct_name()
    expected_keys = ["base_urn"]
    # No optional keys

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # base_urn
    base_urn_value = df[df.iloc[:, 0] == "base_urn"].iloc[0, 1]
    base_urn_row = df[df.iloc[:, 0] == "base_urn"].index[0] + 1
    validate_urn(base_urn_value, fct_name, base_urn_row)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Reference Controls {OK}
def validate_reference_controls_meta(df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "reference_controls"
    fct_name = get_current_fct_name()
    expected_keys = ["base_urn"]
    # No optional keys

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # base_urn
    base_urn_value = df[df.iloc[:, 0] == "base_urn"].iloc[0, 1]
    base_urn_row = df[df.iloc[:, 0] == "base_urn"].index[0] + 1
    validate_urn(base_urn_value, fct_name, base_urn_row)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Risk Matrix {OK}
def validate_risk_matrix_meta(df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "risk_matrix"
    fct_name = get_current_fct_name()
    expected_keys = ["urn", "ref_id", "name", "description"]
    # No optional keys

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # URN
    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    urn_row = df[df.iloc[:, 0] == "urn"].index[0] + 1 
    validate_urn(urn_value, fct_name, urn_row)

    # ref_id
    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    ref_id_row = df[df.iloc[:, 0] == "ref_id"].index[0] + 1
    validate_ref_id(ref_id_value, fct_name, ref_id_row)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Implementation Groups {OK}
def validate_implementation_groups_meta(wb: Workbook, df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "implementation_groups"
    fct_name = get_current_fct_name()
    expected_keys = ["name"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # name
    validate_related_content_sheet_from_name_key(wb, df, sheet_name, fct_name)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Mappings {OK}
def validate_requirement_mapping_set_meta(df, sheet_name: str, verbose, ctx: ConsoleContext = None):
    
    expected_type = "requirement_mapping_set"
    fct_name = get_current_fct_name()
    expected_keys = [
        "urn", "ref_id",
        "name", "description",
        "source_framework_urn",
        "source_node_base_urn",
        "target_framework_urn",
        "target_node_base_urn"
    ]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # URN
    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    urn_row = df[df.iloc[:, 0] == "urn"].index[0] + 1 
    validate_urn(urn_value, fct_name, urn_row)

    # ref_id
    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    ref_id_row = df[df.iloc[:, 0] == "ref_id"].index[0] + 1
    validate_ref_id(ref_id_value, fct_name, ref_id_row)

    # Duplicate the list to avoid future modifications of expected_keys affecting the validation
    keys_to_check_no_spaces = [
        "source_framework_urn",
        "source_node_base_urn",
        "target_framework_urn",
        "target_node_base_urn"
    ]

    # Validate that the values for specific keys do not contain spaces
    for key in keys_to_check_no_spaces:
        row_data = df[df.iloc[:, 0] == key]
        if row_data.empty:
            raise ValueError(f"({fct_name}) [{sheet_name}] Missing required key \"{key}\"")

        value = str(row_data.iloc[0, 1]).strip()
        row = row_data.index[0] + 1  # Excel-style row number (1-based index)
        validate_no_spaces(value, key, fct_name, row)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Scores {OK}
def validate_scores_meta(wb: Workbook, df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "scores"
    fct_name = get_current_fct_name()
    expected_keys = ["name"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # name
    validate_related_content_sheet_from_name_key(wb, df, sheet_name, fct_name)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Answers {OK}
def validate_answers_meta(wb: Workbook, df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "answers"
    fct_name = get_current_fct_name()
    expected_keys = ["name"]
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # name
    validate_related_content_sheet_from_name_key(wb, df, sheet_name, fct_name)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] URN Prefix {OK}
def validate_urn_prefix_meta(df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    expected_type = "urn_prefix"
    fct_name = get_current_fct_name()
    # No "expected_keys" because only  "type" is required
    # No optional keys
    
    validate_meta_sheet(df, sheet_name, None, expected_type, fct_name)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)



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
                    ctx.add_sheet_verbose_msg(sheet_name, msg)
                print(msg)
                
            continue

        # Check if the entire column is empty (i.e., all values are NaN or blank)
        is_entirely_empty = all(pd.isna(val) or str(val).strip() == "" for val in df[col])

        if is_entirely_empty:
            if verbose:
                msg = (f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] Optional column \"{col}\" is present but entirely empty")
                        # "\n> 💡 Tip: If you don't need this column, you can simply remove it from the sheet.")
                if ctx:
                    ctx.add_sheet_verbose_msg(sheet_name, msg)
                print(msg)


# Check that values in each column from the given list are unique. Raise error or emit warning if duplicates are found
def validate_unique_column_values(df, column_names: List[str], sheet_name: str, context: str = None, warn_only: bool = False, ctx: ConsoleContext = None):

    context = context or "validate_unique_column_values"

    for column_name in column_names:
        if column_name not in df.columns:
            raise ValueError(f"({context}) [{sheet_name}] Column \"{column_name}\" not found in sheet")

        # Drop rows with empty or whitespace-only values before checking duplicates
        column_series = df[column_name].dropna().astype(str).map(str.strip)
        column_series = column_series[column_series != ""]

        # Re-index the filtered series to map back to original DataFrame indices
        filtered_df = df.loc[column_series.index]
        duplicates = filtered_df[column_name][filtered_df[column_name].duplicated(keep=False)]

        if not duplicates.empty:
            duplicate_rows = duplicates.index + 2  # Excel-like row number (1-based + header)
            duplicate_values = duplicates.unique()
            quoted_values = ', '.join(f'"{str(val)}"' for val in duplicate_values)

            msg = (
                f"({context}) [{sheet_name}] Duplicate value(s) found in column \"{column_name}\": {quoted_values}"
                f"\n> Rows: {', '.join(map(str, duplicate_rows))}"
            )

            if warn_only:
                msg = f"⚠️  [WARNING] {msg}"
                print(msg)
                if ctx:
                    ctx.add_sheet_warning_msg(sheet_name, msg)
            else:
                raise ValueError(msg)


def validate_extra_locales_in_content(df, sheet_name: str, context: str, ctx: ConsoleContext = None, verbose: bool = False):

    for col in df.columns:
        match = re.fullmatch(r"(.+)\[(.+)\]", str(col))  # Match "column_name[locale]"
        if not match:
            continue
        
        base_col, locale = match.groups()

        # Validate locale format
        if not is_valid_locale(locale):
            raise ValueError(
                f"({context}) [{sheet_name}] Column \"{col}\": Invalid locale \"{locale}\""
                "\n> 💡 Tip: Locale setting must comply with ISO 639 Set 1 (e.g., \"en\", \"fr\"). See https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes"
            )

        # Check if base column exists
        if base_col not in df.columns:
            raise ValueError(
                f"({context}) [{sheet_name}] Column \"{col}\": Localized column found, but base column \"{base_col}\" is missing"
                f"\n> 💡 Tip: Add the base column \"{base_col}\" or simply remove the column \"{col}\"."
            )

        # If column exists but is entirely empty, emit a warning
        non_empty_found = any(pd.notna(val) and str(val).strip() != "" for val in df[col])
        if not non_empty_found:
            if verbose:
                msg = (
                    f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] Column \"{col}\": Localized column is present but entirely empty"
                    "\n> 💡 Tip: If you don't need this column, you can simply remove it from the sheet."
                )
                if ctx:
                    ctx.add_sheet_verbose_msg(sheet_name, msg)
                print(msg)


# Return the name of a "_content" sheet by removing the trailing "_content" in the given sheet name.
def get_content_sheet_base_name(content_sheet_name: str) -> str:
    if not content_sheet_name.endswith("_content"):
        raise ValueError(f"Invalid sheet name: \"{content_sheet_name}\" does not end with \"_content\"")

    base_name = re.sub(r'_content$', '', content_sheet_name)
    return base_name


# Return the name of a "_content" sheet by removing the trailing "_content" in the given sheet name.
def get_corresponding_content_sheet_name(meta_sheet_names: List[str]) -> str:

    content_sheet_names = []

    for sheet in meta_sheet_names:
        if not sheet.endswith("_meta"):
            raise ValueError(f"Invalid sheet name: \"{sheet}\" does not end with \"_meta\"")

        content_name = re.sub(r'_meta$', '_content', sheet)
        content_sheet_names.append(content_name)

    return content_sheet_names


# Check if a content sheet is referenced in any 'framework' meta sheet via a specific meta field (e.g., 'scores_definition')
def check_content_sheet_usage_in_frameworks(wb: Workbook, sheet_name: str, meta_field: str, fct_name: str, ctx: ConsoleContext = None) -> List[str]:
    """
    Args:
        wb (Workbook): The Excel workbook.
        sheet_name (str): Name of the current content sheet.
        meta_field (str): The meta key in framework sheets that should reference this sheet.
        fct_name (str): Name of the calling function (used in messages).
        ctx (ConsoleContext, optional): Context object for collecting warnings.
    """

    sheet_base_name = get_content_sheet_base_name(sheet_name)
    meta_sheets = get_meta_sheets_with_type(wb)
    frameworks_with_reference = []

    for sheet, sheet_type in meta_sheets.items():
        if sheet_type != MetaTypes.FRAMEWORK.value:
            continue

        sheet_df = pd.DataFrame(wb[sheet].values)
        meta_value = get_meta_value(sheet_df, meta_field, sheet)

        if meta_value == sheet_base_name:
            frameworks_with_reference.append(sheet)

    if frameworks_with_reference:
        print(f"ℹ️  [INFO] ({fct_name}) [{sheet_name}] Sheet referenced by the sheet(s): {', '.join(f'\"{s}\"' for s in frameworks_with_reference)}")
    else:
        warn_msg = (
            f"⚠️  [WARNING] ({fct_name}) [{sheet_name}] This sheet is not referenced in any \"framework\" sheet via the field \"{meta_field}\""
            f"\n> 💡 Tip: Set \"{meta_field}\" in your framework meta sheet to \"{sheet_base_name}\" if needed."
        )
        print(warn_msg)
        if ctx:
            ctx.add_sheet_warning_msg(sheet_name, warn_msg)

    return frameworks_with_reference


# Check whether each ID is used in at least one framework sheet. Emit a warning if any IDs are unused.
def check_unused_ids_in_frameworks(wb: Workbook, df_ids: pd.DataFrame, id_column: str, target_column: str, frameworks_sheet_names: List[str], sheet_name: str, context: str, ctx: ConsoleContext = None, verbose: bool = False):

    ids_to_check = get_non_empty_column_values(df_ids, id_column)
    unused_ids = []

    for _id in ids_to_check:
        found = False
        for fw_sheet in frameworks_sheet_names:
            values = list(wb[fw_sheet].values)
            if not values:
                continue  # skip empty sheets

            df_fw = pd.DataFrame(values[1:], columns=values[0])  # use header

            if target_column not in df_fw.columns:
                continue

            for cell in df_fw[target_column]:
                if pd.isna(cell):
                    continue

                entries = [entry.strip() for entry in str(cell).split("\n") if entry.strip()]
                if _id in entries:
                    found = True
                    break  # No need to keep looking in this sheet

            if found:
                break  # Found in one sheet : Stop checking this ID

        if not found:
            unused_ids.append(_id)

    if unused_ids:
        msg = (
            f"⚠️  [WARNING] ({context}) [{sheet_name}] The following ID(s) from column \"{id_column}\" are not used in any framework sheet: "
            f"{', '.join(f'\"{x}\"' for x in unused_ids)}"
        )
        print(msg)
        if ctx:
            ctx.add_sheet_warning_msg(sheet_name, msg)
    else:
        if verbose:
            msg = (f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] All ID(s) from column \"{id_column}\" are used in framework sheets")
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)


# Validate that all non-empty values in a specific column are in the allowed list. Ignores blank or whitespace-only cells.
def validate_allowed_column_values(df: pd.DataFrame, column_name: str, allowed_values: List[str], sheet_name: str, context: str = None, warn_only: bool = False, ctx: ConsoleContext = None):
    """
    Args:
        df: The DataFrame to validate.
        column_name: The name of the column to check.
        allowed_values: A list of allowed string values.
        sheet_name: Name of the Excel sheet.
        context: Optional context string (e.g., function name).
        warn_only: If True, warnings are printed instead of raising errors.
        ctx: Optional ConsoleContext to collect warning messages.
    """

    context = context or "validate_allowed_column_values"

    if column_name not in df.columns:
        return
        # raise ValueError(f"({context}) [{sheet_name}] Column \"{column_name}\" not found in sheet")

    # Drop NA and strip values
    cleaned_series = df[column_name].dropna().map(lambda x: str(x).strip())
    cleaned_series = cleaned_series[cleaned_series != ""]

    # Find invalid values
    invalid_mask = ~cleaned_series.isin(allowed_values)

    if invalid_mask.any():
        invalid_values = cleaned_series[invalid_mask]
        invalid_entries = invalid_values.unique()
        invalid_rows = invalid_values.index + 2  # Excel-style row numbers

        quoted_values = ', '.join(f'"{v}"' for v in invalid_entries)
        msg = (
            f"({context}) [{sheet_name}] Invalid value(s) found in column \"{column_name}\": {quoted_values}"
            f"\n> Rows: {', '.join(map(str, invalid_rows))}"
            f"\n> Allowed values are: {', '.join(f'\"{v}\"' for v in allowed_values)}"
        )

        if warn_only:
            msg = f"⚠️  [WARNING] {msg}"
            print(msg)
            if ctx:
                ctx.add_sheet_warning_msg(sheet_name, msg)
        else:
            raise ValueError(msg)


# Check whether each Prefix URN ID is used in at least one framework sheet. Emit a warning if any IDs are unused.
def _URN_prefix_check_unused_ids_in_frameworks(wb: Workbook, df_ids: pd.DataFrame, frameworks_sheet_names: List[str], sheet_name: str, context: str, ctx: ConsoleContext = None, verbose: bool = False):

    target_columns = ["threats", "reference_controls"]
    id_column = "prefix_id"
    ids_to_check = get_non_empty_column_values(df_ids, id_column)
    unused_ids = []

    for _id in ids_to_check:
        found = False

        for fw_sheet in frameworks_sheet_names:
            values = list(wb[fw_sheet].values)
            if not values:
                continue  # skip empty sheet

            df_fw = pd.DataFrame(values[1:], columns=values[0])  # headers

            for target_column in target_columns:
                if target_column not in df_fw.columns:
                    continue

                for cell in df_fw[target_column]:
                    if pd.isna(cell):
                        continue
                    entries = [entry.strip() for entry in str(cell).split(",") if entry.strip()]
                    prefix_parts = [entry.split(":", 1)[0].strip() for entry in entries if ":" in entry]

                    if _id in prefix_parts:
                        found = True
                        break  # Found : No need to continue on this column

                if found:
                    break  # Found : No need to continue on this sheet

            if found:
                break  # Found : Skip to next ID

        if not found:
            unused_ids.append(_id)

    if unused_ids:
        msg = (
            f"⚠️  [WARNING] ({context}) [{sheet_name}] The following Prefix ID(s) from column \"{id_column}\" are not used in any framework sheet: "
            f"{', '.join(f'\"{x}\"' for x in unused_ids)}"
        )
        print(msg)
        if ctx:
            ctx.add_sheet_warning_msg(sheet_name, msg)
    elif verbose:
        msg = (
            f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] All Prefix ID(s) from column \"{id_column}\" are used in framework sheets"
        )
        print(msg)
        if ctx:
            ctx.add_sheet_verbose_msg(sheet_name, msg)


#  Classify each prefix_value as 'internal' or 'external' depending on whether it's used in the base_urn field of the corresponding *_meta sheets.
def _URN_prefix_classify_prefix_usage(wb: Workbook, df_urn_prefix: pd.DataFrame, meta_sheets: List[str], meta_type: MetaTypes, sheet_name: str, fct_name: str, ctx: ConsoleContext = None) -> Tuple[List[str], List[str]]:
    """
    Args:
        wb: Workbook object.
        df_urn_prefix: DataFrame of the URN Prefix content sheet.
        meta_sheets: List of *_meta sheet names to check.
        meta_type: One of MetaTypes.THREATS or MetaTypes.REFERENCE_CONTROLS.
        sheet_name: Name of the sheet currently being validated (URN Prefix).
        fct_name: Name of the calling validation function (for error formatting).
        ctx: Optional ConsoleContext to store warnings/info messages.
    Returns:
        Tuple of (internal_prefixes, external_prefixes)
    """

    # Define expected type_object depending on the meta_type
    if meta_type == MetaTypes.THREATS:
        expected_type_object = "threat"
    elif meta_type == MetaTypes.REFERENCE_CONTROLS:
        expected_type_object = "function"
    else:
        raise ValueError(f"({fct_name}) [{sheet_name}] Unsupported meta_type: {meta_type}")

    prefix_values = df_urn_prefix["prefix_value"].dropna().astype(str).str.strip().unique()
    internal_prefixes = []
    external_prefixes = []

    # Filter prefix_values by expected type_object (based on the 4th segment of the URN)
    filtered_prefix_values = []
    for prefix in prefix_values:
        parts = prefix.split(":")
        if len(parts) > 3 and parts[3].strip() == expected_type_object:
            filtered_prefix_values.append(prefix)


    for prefix in filtered_prefix_values:
        found = False

        for sheet in meta_sheets:
            try:
                rows = list(wb[sheet].values)

                # Convert the meta sheet into a key-value dictionary
                meta_dict = {
                    str(row[0]).strip(): str(row[1]).strip()
                    for row in rows if row and len(row) >= 2 and row[0] and row[1]
                }

                base_urn = meta_dict.get("base_urn")
                if not base_urn:
                    continue

                parts = base_urn.split(":")
                
                # Make sure the 4th element in base_urn matches the expected type
                if len(parts) > 3 and parts[3].strip() == expected_type_object:
                    if base_urn.strip() == prefix.strip():
                        found = True
                        # print("GOOD !")
                        break  # No need to keep checking other sheets

            except Exception as e:
                msg = f"⚠️  [WARNING] ({fct_name}) [{sheet_name}] Could not process sheet \"{sheet}\": {e}"
                print(msg)
                if ctx:
                    ctx.add_sheet_warning_msg(sheet_name, msg)
                continue

        if found:
            internal_prefixes.append(prefix)
        else:
            external_prefixes.append(prefix)

    return internal_prefixes, external_prefixes


# Check that each (source_node_id, target_node_id) pair is unique. Emits a warning or raises an error depending on "warn_only".
def _req_map_set_validate_unique_mappings(df, sheet_name: str, context: str = None, warn_only: bool = False, ctx: ConsoleContext = None):

    context = context or "validate_unique_mappings"

    if "source_node_id" not in df.columns or "target_node_id" not in df.columns:
        raise ValueError(f"({context}) [{sheet_name}] Columns \"source_node_id\" and/or \"target_node_id\" not found")

    df_clean = df[["source_node_id", "target_node_id"]].dropna()

    df_clean["source_node_id"] = df_clean["source_node_id"].map(lambda x: str(x).strip())
    df_clean["target_node_id"] = df_clean["target_node_id"].map(lambda x: str(x).strip())

    # Remove rows with empty values
    df_clean = df_clean[(df_clean["source_node_id"] != "") & (df_clean["target_node_id"] != "")]

    duplicates = df_clean[df_clean.duplicated(subset=["source_node_id", "target_node_id"], keep=False)]


    if not duplicates.empty:
        duplicate_rows = duplicates.index + 2  # 1-based row index (+ header)
        duplicate_pairs = duplicates.drop_duplicates().values.tolist()
        quoted_pairs = ' ; '.join(f'["{s}", "{t}"]' for s, t in duplicate_pairs)

        msg = (
            f"({context}) [{sheet_name}] Duplicate mapping(s) found for [source_node_id + target_node_id] pair(s): {quoted_pairs}"
            f"\n> Rows: {', '.join(map(str, duplicate_rows))}"
        )

        if warn_only:
            msg = f"⚠️  [WARNING] {msg}"
            print(msg)
            if ctx:
                ctx.add_sheet_warning_msg(sheet_name, msg)
        else:
            raise ValueError(msg)


# Validate if the "source_node_id" and "target_node_id" used in the mapping exist in the corresponding 'source' and 'target' sheets.
def _req_map_set_validate_mapping_node_ids_against_sheets(wb: Workbook, df: pd.DataFrame, sheet_name: str, fct_name: str, ctx: ConsoleContext = None, verbose: bool = False):

    sheets = wb.sheetnames
    source_ids = set()
    target_ids = set()
    source_sheet_available = "source" in sheets
    target_sheet_available = "target" in sheets

    # Load source node IDs
    if source_sheet_available:
        source_sheet = wb["source"]
        source_header = [cell.value for cell in source_sheet[1]]
        if "node_id" in source_header:
            idx = source_header.index("node_id")
            for row in source_sheet.iter_rows(min_row=2):
                if idx < len(row) and row[idx].value:
                    source_ids.add(str(row[idx].value).strip())
        else:
            source_sheet_available = False
            if verbose:
                msg = f'💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] Column "node_id" not found in sheet "source"'
                print(msg)
                if ctx:
                    ctx.add_sheet_verbose_msg(sheet_name, msg)
    else:
        if verbose:
            msg = f'💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] Sheet "source" not found'
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)

    # Load target node IDs
    if target_sheet_available:
        target_sheet = wb["target"]
        target_header = [cell.value for cell in target_sheet[1]]
        if "node_id" in target_header:
            idx = target_header.index("node_id")
            for row in target_sheet.iter_rows(min_row=2):
                if idx < len(row) and row[idx].value:
                    target_ids.add(str(row[idx].value).strip())
        else:
            target_sheet_available = False
            if verbose:
                msg = f'💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] Column "node_id" not found in sheet "target"'
                print(msg)
                if ctx:
                    ctx.add_sheet_verbose_msg(sheet_name, msg)
    else:
        if verbose:
            msg = f'💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] Sheet "target" not found'
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)


    if not source_sheet_available:
        msg = f'⚠️  [WARNING] ({fct_name}) [{sheet_name}] Invalid or missing "source" sheet. The "source_node_id" column cannot be checked.'
        print(msg)
        if ctx:
            ctx.add_sheet_warning_msg(sheet_name, msg)

    if not target_sheet_available:
        msg = f'⚠️  [WARNING] ({fct_name}) [{sheet_name}] Invalid or missing "target" sheet. The "target_node_id" column cannot be checked.'
        print(msg)
        if ctx:
            ctx.add_sheet_warning_msg(sheet_name, msg)


    # Used IDs
    used_source_ids = [
        str(val).split(":")[-1] for val in df["source_node_id"].dropna()
    ]
    used_target_ids = [
        str(val).split(":")[-1] for val in df["target_node_id"].dropna()
    ]

    source_missing_counts = Counter(
        node_id for node_id in used_source_ids
        if source_sheet_available and node_id not in source_ids
    )
    target_missing_counts = Counter(
        node_id for node_id in used_target_ids
        if target_sheet_available and node_id not in target_ids
    )

    # Warnings: Missing IDs
    if source_sheet_available:
        for sid in source_missing_counts:
            msg = f'⚠️  [WARNING] ({fct_name}) [{sheet_name}] source_node_id "{sid}" not found in sheet "source"'
            print(msg)
            if ctx:
                ctx.add_sheet_warning_msg(sheet_name, msg)

    if target_sheet_available:
        for tid in target_missing_counts:
            msg = f'⚠️  [WARNING] ({fct_name}) [{sheet_name}] target_node_id "{tid}" not found in sheet "target"'
            print(msg)
            if ctx:
                ctx.add_sheet_warning_msg(sheet_name, msg)

    # Duplicates
    if source_sheet_available:
        for sid, count in source_missing_counts.items():
            if count > 1:
                msg = f'🔁 [DUPLICATE] ({fct_name}) [{sheet_name}] source_node_id "{sid}" appears {count} times in mappings'
                print(msg)

    if target_sheet_available:
        for tid, count in target_missing_counts.items():
            if count > 1:
                msg = f'🔁 [DUPLICATE] ({fct_name}) [{sheet_name}] target_node_id "{tid}" appears {count} times in mappings'
                print(msg)

    # Final summary
    total_missing_sources = '???' if not source_sheet_available else sum(source_missing_counts.values())
    total_missing_targets = '???' if not target_sheet_available else sum(target_missing_counts.values())
    if total_missing_sources or total_missing_targets:
        msg = f"⚠️  [MAPPING CHECK SUMMARY] ({fct_name}) [{sheet_name}] Missing usage count - Source: {total_missing_sources}, Target: {total_missing_targets}"
        print(msg)
        if ctx:
            ctx.add_sheet_warning_msg(sheet_name, msg)

        if source_sheet_available or target_sheet_available:
            msg2 = (
                "ℹ️  [INFO] Please note that these incorrect node IDs have been added to the mapping anyway."
                "\n> 💡 Tip: If you want to correct them, please do so in your Excel file."
            )
            print(msg2)



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

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["ref_id"], sheet_name, fct_name, ctx=ctx)
    
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
                "\n> 💡 Tip: At least one of them must be filled."
            )

        if ref_id:
            validate_ref_id_with_spaces(ref_id, fct_name, idx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Threats {OK}
def validate_threats_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["ref_id"]
    optional_columns = ["description", "annotation"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["ref_id"], sheet_name, fct_name, ctx=ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Reference Controls {OK}
def validate_reference_controls_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["ref_id"]
    optional_columns = ["description", "category", "csf_function", "annotation"]

    # Special values
    category_values = ["policy", "process", "technical", "physical", "procedure"]
    csf_function_values = ["govern", "identify", "protect", "detect", "respond", "recover"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["ref_id"], sheet_name, fct_name, ctx=ctx)

    # Check if values in "category" and "csf_function" columns are valid
    validate_allowed_column_values(df, "category", category_values, sheet_name, fct_name,ctx=ctx)
    validate_allowed_column_values(df, "csf_function", csf_function_values, sheet_name, fct_name,ctx=ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Risk Matrix
def validate_risk_matrix_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["type", "id", "color", "abbreviation", "name", "description", "grid"]
    # No optional columns

    # Special values
    type_values = ["probability", "impact", "risk"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)

    # Check if values in "type" column are valid
    validate_allowed_column_values(df, "type", type_values, sheet_name, fct_name,ctx=ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Implementation Groups {OK}
def validate_implementation_groups_content(wb: Workbook, df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["ref_id", "name"]
    optional_columns = ["description"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["ref_id"], sheet_name, fct_name, ctx=ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    # Check if the "implementation_groups" sheet is actually used in a "framework" sheet
    frameworks_with_imp_grp = check_content_sheet_usage_in_frameworks(wb, sheet_name, "implementation_groups_definition", fct_name, ctx)
    frameworks_with_imp_grp = get_corresponding_content_sheet_name(frameworks_with_imp_grp)

    # Check if every implementation groups are actually used in "framework" sheets
    if frameworks_with_imp_grp:
        check_unused_ids_in_frameworks(wb, df, "ref_id", "implementation_groups", frameworks_with_imp_grp, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Requirement Mapping Set {OK}
def validate_requirement_mapping_set_content(wb: Workbook, df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["source_node_id", "target_node_id", "relationship"]
    optional_columns = ["rationale", "strength_of_relationship"]
    
    # Special values
    relationship_values = ["subset", "intersect", "equal", "superset", "not_related"]
    rationale_values = ["syntactic", "semantic", "functional"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    # Extra locales (Not needed for mappings, but added just in case)
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    # Check if there are duplicated mappings
    _req_map_set_validate_unique_mappings(df, sheet_name, fct_name, ctx=ctx)

    # Check if values in "relationship" and "rationale" columns are valid
    validate_allowed_column_values(df, "relationship", relationship_values, sheet_name, fct_name,ctx=ctx)
    validate_allowed_column_values(df, "rationale", rationale_values, sheet_name, fct_name,ctx=ctx)

    # Check mapping validity using the "source" and "target" sheets
    _req_map_set_validate_mapping_node_ids_against_sheets(wb, df, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Scores {OK}
def validate_scores_content(wb: Workbook, df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["score", "name", "description"]
    optional_columns = ["description_doc"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    # Validate each "score" value is a non-negative integer
    for idx, value in enumerate(df["score"], start=2):  # Row number starts at 2
        value_str = str(value).strip()
        if not value_str.isdigit():
            raise ValueError(f"({fct_name}) [{sheet_name}] Row #{idx}: Key \"score\" must be a non-negative integer, got \"{value_str}\"")
        
        value_int = int(value_str)
        if value_int < 0:
            raise ValueError(f"({fct_name}) [{sheet_name}] Row #{idx}: Key \"score\" must be >= 0, got \"{value_int}\"")

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["score"], sheet_name, fct_name, ctx=ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    # Check if the "score" sheet is actually used in a "framework" sheet
    check_content_sheet_usage_in_frameworks(wb, sheet_name, "scores_definition", fct_name, ctx)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Answers {OK}
def validate_answers_content(wb: Workbook, df: pd.DataFrame, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["id", "question_type"]
    optional_columns = ["question_choices"]

    # Special values
    question_type_values = ["unique_choice", "multiple_choice", "text", "date"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["id"], sheet_name, fct_name, ctx=ctx)

    # Check if values in "question_type" column are valid
    validate_allowed_column_values(df, "question_type", question_type_values, sheet_name, fct_name,ctx=ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    # Check that "question_choices" is filled for relevant question types ("unique_choice" & "multiple_choice")
    for row_idx, row in df.iterrows():
        question_type_raw = row.get("question_type", "")
        if pd.isna(question_type_raw):
            continue

        question_type = str(question_type_raw).strip().lower()
        if question_type in {"unique_choice", "multiple_choice"}:
            question_choices = row.get("question_choices", "")
            if pd.isna(question_choices) or str(question_choices).strip() == "":
                raise ValueError(f"({fct_name}) [{sheet_name}] Row #{row_idx + 2}: For question_type \"{question_type}\", the field \"question_choices\" must not be empty")

    # Check if the "answers" sheet is actually used in a "framework" sheet
    frameworks_with_answers = check_content_sheet_usage_in_frameworks(wb, sheet_name, "answers_definition", fct_name, ctx)
    frameworks_with_answers = get_corresponding_content_sheet_name(frameworks_with_answers)

    # Check if every answers are actually used in "framework" sheets
    if frameworks_with_answers:
        check_unused_ids_in_frameworks(wb, df, "id", "answer", frameworks_with_answers, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] URN Prefix {OK}
def validate_urn_prefix_content(wb: Workbook, df: pd.DataFrame, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["prefix_id", "prefix_value"]
    # No optional columns

    validate_content_sheet(df, sheet_name, required_columns, fct_name)

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["prefix_id", "prefix_value"], sheet_name, fct_name, ctx=ctx)

    ### Check if URN Prefix IDs are used in "framework" sheets ###
    
    # 1. Get "framework" content sheets
    framework_sheets = get_meta_sheets_names_from_type(wb, MetaTypes.FRAMEWORK)
    framework_sheets = get_corresponding_content_sheet_name(framework_sheets)

    # 2. Check if every Prefix IDs are actually used in "framework" sheets
    if framework_sheets:
        _URN_prefix_check_unused_ids_in_frameworks(wb, df, framework_sheets, sheet_name, fct_name, ctx, verbose)
    else:
        msg = (
            f"⚠️  [WARNING] ({fct_name}) [{sheet_name}] This sheet is not used in any framework sheet"
            f"\n> 💡 Tip: You can remove this sheet and its meta sheet if you are not using it"
        )
        print(msg)
        if ctx:
            ctx.add_sheet_warning_msg(sheet_name, msg)


    ### Check if "prefix_value" come from internal sheets or external framework ###

    # 1. Get "threats" meta sheets
    threats_sheets = get_meta_sheets_names_from_type(wb, MetaTypes.THREATS)

    # 2. Get "reference_controls" sheets
    ref_ctrl_sheets = get_meta_sheets_names_from_type(wb, MetaTypes.REFERENCE_CONTROLS)
    
    # 3. Check whether the values for each "prefix_value" come from internal sheets or external framework
    internal_threats = []; external_threats = []
    internal_ref_ctrl = []; external_ref_ctrl = []
    
    if threats_sheets:
        internal_threats, external_threats = _URN_prefix_classify_prefix_usage(wb, df, threats_sheets, MetaTypes.THREATS, sheet_name, fct_name, ctx)
    if ref_ctrl_sheets:
        internal_ref_ctrl, external_ref_ctrl = _URN_prefix_classify_prefix_usage(wb, df, ref_ctrl_sheets, MetaTypes.REFERENCE_CONTROLS, sheet_name, fct_name, ctx)

    # Info messages for "threats"
    if internal_threats:
        print(f"ℹ️  [INFO] ({fct_name}) [{sheet_name}] Internal \"threats\" prefixes found: {', '.join(f'\"{x}\"' for x in internal_threats)}")
    else:
        if verbose:
            print(f"💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] No internal \"threats\" prefixes found")

    if external_threats:
        print(f"ℹ️  [INFO] ({fct_name}) [{sheet_name}] External \"threats\" prefixes found: {', '.join(f'\"{x}\"' for x in external_threats)}")
    else:
        if verbose:
            print(f"💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] No external \"threats\" prefixes found")

    # Info messages for "reference_controls"
    if internal_ref_ctrl:
        print(f"ℹ️  [INFO] ({fct_name}) [{sheet_name}] Internal \"reference_controls\" prefixes found: {', '.join(f'\"{x}\"' for x in internal_ref_ctrl)}")
    else:
        if verbose:
            print(f"💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] No internal \"reference_controls\" prefixes found")

    if external_ref_ctrl:
        print(f"ℹ️  [INFO] ({fct_name}) [{sheet_name}] External \"reference_controls\" prefixes found: {', '.join(f'\"{x}\"' for x in external_ref_ctrl)}")
    else:
        if verbose:
            print(f"💬 ℹ️  [INFO] ({fct_name}) [{sheet_name}] No external \"reference_controls\" prefixes found")

    ### 4. Check if external prefixes are declared in "dependencies" from "library_meta" ###

    # 1. Normalize external URNs by replacing the object type (4th element) with "library"
    def normalize_to_library(urn_list: List[str], target_type: str) -> List[str]:
        normalized = []
        for urn in urn_list:
            parts = urn.split(":")
            if len(parts) > 3 and parts[3].strip() == target_type:
                parts[3] = "library"
                normalized.append(":".join(parts))
        return normalized

    normalized_ext_threats = normalize_to_library(external_threats, "threat")
    normalized_ext_ref_ctrl = normalize_to_library(external_ref_ctrl, "function")

    # 2. Merge and deduplicate normalized external URNs
    required_dependencies = sorted(set(normalized_ext_threats + normalized_ext_ref_ctrl))

    if required_dependencies:

        # 3. Load "library_meta" sheet as a key-value dictionary
        try:
            rows = list(wb["library_meta"].values)
            meta_dict = {
                str(row[0]).strip(): str(row[1]).strip()
                for row in rows if row and len(row) >= 2 and row[0] and row[1]
            }
        except Exception as e:
            raise ValueError(f"({fct_name}) [{sheet_name}] Could not read \"library_meta\" sheet: {e}")

        # 4. Ensure "dependencies" field exists and is non-empty
        if "dependencies" not in meta_dict or not meta_dict["dependencies"].strip():
            raise ValueError(
                f"({fct_name}) [{sheet_name}] \"library_meta\" is missing a non-empty \"dependencies\" field, "
                f"required to declare external libraries: {', '.join(f'\"{d}\"' for d in required_dependencies)}"
            )

        # 5. Parse declared dependencies
        declared_dependencies = [
            dep.strip() for dep in meta_dict.get("dependencies", "").split(",") if dep.strip()
        ]

        # 6. Compare with required dependencies
        missing_dependencies = [dep for dep in required_dependencies if dep not in declared_dependencies]

        if missing_dependencies:
            missing_list = ", ".join(f'"{d}"' for d in missing_dependencies)
            threat_list = ", ".join(f'"{t}"' for t in external_threats)
            ref_ctrl_list = ", ".join(f'"{r}"' for r in external_ref_ctrl)

            raise ValueError(
                f"({fct_name}) [{sheet_name}] Missing required dependencies in \"library_meta\": {missing_list}\n"
                f"> 💡 Tip: These are required due to the following external prefixes:\n"
                f"   - External \"threats\": {threat_list or 'None'}\n"
                f"   - External \"reference_controls\": {ref_ctrl_list or 'None'}"
            )

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)



# ─────────────────────────────────────────────────────────────
# DISPATCHING
# ─────────────────────────────────────────────────────────────

def dispatch_meta_validation(wb: Workbook, df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    
    type_row = df[df.iloc[:, 0] == "type"]
    if type_row.empty:
        raise ValueError(f"({fct_name}) [{sheet_name}] Missing or empty \"type\" field in meta sheet")
    type_value = type_row.iloc[0, 1]
    if type_value == MetaTypes.LIBRARY.value:
        validate_library_meta(df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.FRAMEWORK.value:
        validate_framework_meta(wb, df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.THREATS.value:
        validate_threats_meta(df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.REFERENCE_CONTROLS.value:
        validate_reference_controls_meta(df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.RISK_MATRIX.value:
        validate_risk_matrix_meta(df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.REQUIREMENT_MAPPING_SET.value:
        validate_requirement_mapping_set_meta(df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.IMPLEMENTATION_GROUPS.value:
        validate_implementation_groups_meta(wb, df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.SCORES.value:
        validate_scores_meta(wb, df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.ANSWERS.value:
        validate_answers_meta(wb, df, sheet_name, verbose, ctx)
    elif type_value == MetaTypes.URN_PREFIX.value:
        validate_urn_prefix_meta(df, sheet_name, verbose, ctx)
    else:
        raise ValueError(f"({fct_name}) [{sheet_name}] Unknown meta type \"{type_value}\"")


def dispatch_content_validation(wb: Workbook, df, sheet_name: str, corresponding_meta_type: str, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    
    if corresponding_meta_type == MetaTypes.FRAMEWORK.value:
        validate_framework_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.THREATS.value:
        validate_threats_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.REFERENCE_CONTROLS.value:
        validate_reference_controls_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.RISK_MATRIX.value:
        validate_risk_matrix_content(df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.REQUIREMENT_MAPPING_SET.value:
        validate_requirement_mapping_set_content(wb, df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.IMPLEMENTATION_GROUPS.value:
        validate_implementation_groups_content(wb, df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.SCORES.value:
        validate_scores_content(wb, df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.ANSWERS.value:
        validate_answers_content(wb, df, sheet_name, verbose, ctx)
    elif corresponding_meta_type == MetaTypes.URN_PREFIX.value:
        validate_urn_prefix_content(wb, df, sheet_name, verbose, ctx)
    else:
        raise ValueError(f"({fct_name}) [{sheet_name}] Cannot determine validation for content of type \"{corresponding_meta_type}\"")


# ─────────────────────────────────────────────────────────────
# MAIN VALIDATION FUNCTION
# ─────────────────────────────────────────────────────────────

def validate_excel_structure(filepath, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    print(f"⌛ Parsing \"{os.path.basename(filepath)}\"...")
    
    if not ctx:
        ctx = ConsoleContext()
    
    wb = load_workbook(filepath, data_only=True)
    fct_name = get_current_fct_name()
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

        base_name = re.sub(r'_meta$', '', sheet_name)
        
        expected_content_sheet = base_name + "_content"
        if sheet_name != "library_meta" and expected_content_sheet not in content_sheets:
            raise ValueError(f"({fct_name}) [{sheet_name}] No corresponding content sheet found for this meta"
                            f"\n> 💡 Tip: Make sure the corresponding content sheet for \"{sheet_name}\" is named \"{expected_content_sheet}\"")

        dispatch_meta_validation(wb, df, sheet_name, verbose, ctx)
        type_row = df[df.iloc[:, 0] == "type"]
        meta_types[base_name] = str(type_row.iloc[0, 1]).strip()

    # Check "_content" sheets
    # As some checks in "_content" sheets need to check the contents of other "_content" sheets, we make sure that all such sheets first have a "_meta" sheet
    for sheet_name, df in content_sheets.items():
        base_name = re.sub(r'_content$', '', sheet_name)

        if base_name not in meta_types:
            raise ValueError(f"({fct_name}) [{sheet_name}] No corresponding meta sheet found for this content"
                             f"\n> 💡 Tip: Make sure the corresponding meta sheet for \"{sheet_name}\" is named \"{re.sub(r'_content$', '_meta', sheet_name)}\"")

    # Handle "_content" sheets
    for sheet_name, df in content_sheets.items():
        base_name = re.sub(r'_content$', '', sheet_name)
        dispatch_content_validation(wb, df, sheet_name, meta_types[base_name], verbose, ctx)

    # Warn about ignored sheets
    for sheet_name in ignored_sheets:
        msg = f"⏩ [SKIP] Ignored sheet \"{sheet_name}\" (does not end with \"_meta\" or \"_content\")"
        print(msg)

    print("")
    print(f"✅ [SUCCESS] Excel structure is valid for \"{file_name}\"")
    
    if ctx.count_all_warnings() > 0:
        print(f"📜 [SUMMARY] ⚠️  Total [WARNING] for \"{file_name}\": {ctx.count_all_warnings()}")
    
    if verbose and ctx.count_all_verbose() > 0:
        print(f"📜 [SUMMARY] 💬 Total [Verbose Messages] for \"{file_name}\": {ctx.count_all_verbose()}")
    
    


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
