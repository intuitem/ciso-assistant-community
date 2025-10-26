"""
v2 Excel Structure Validator

This script validates the structure and consistency of an Excel file following the expected v2 format. It checks:
- The presence and format of *_meta and *_content sheets.
- Required keys and values in meta sheets.
- Structural correctness and references in content sheets.
- Column-level validation against other sheets (e.g. implementation_groups, answers, threats, reference_controls).
- Validity of URNs using prefix definitions and corresponding content sheets.

Usage:
    python check_library_v2.py file.xlsx [--verbose]

Arguments:
    file.xlsx               Path to the Excel file to validate.

    -e, --external-refs     YAML files containing external references mentioned in the library.
                            Use it to check the following columns if necessary : "threats", "reference_controls".
                            Separate external references with commas (e.g., ./threats1.yaml,./refs/ref_ctrl.yaml,../test.yaml)
    -b, --bulk              Enable bulk mode to process all Excel files in a directory.
    --verbose               Display additional information and validation feedback.

The script exits with code 1 and displays an error message if validation fails.
"""



import os
import re
import sys
import yaml
import inspect
import argparse
from enum import Enum
from pathlib import Path
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
    LIBRARY = "library"
    FRAMEWORK = "framework"
    THREATS = "threats"
    REFERENCE_CONTROLS = "reference_controls"
    RISK_MATRIX = "risk_matrix"
    REQUIREMENT_MAPPING_SET = "requirement_mapping_set"
    IMPLEMENTATION_GROUPS = "implementation_groups"
    SCORES = "scores"
    ANSWERS = "answers"
    URN_PREFIX = "urn_prefix"

class SheetTypes(Enum):
    META = "_meta"
    CONTENT = "_content"

class YAMLSectionTypes(Enum):
    THREATS = "threats"
    REFERENCE_CONTROLS = "reference_controls"

# URN Format : urn:<packager>:risk:<object>:<ref_id>
class URNObjects(Enum):
    URN_BEGGINING = "urn"
    URN_3RD_WORD = "risk"   # Because the format is urn:<packager>:risk:<object>:<ref_id>

    LIBRARY = "library"
    FRAMEWORK = "framework"
    THREAT = "threat"
    REFERENCE_CONTROL = "function"
    MATRIX = "matrix"
    REQ_MAPPING_SET = "req_mapping_set"
    REQ_NODE = "req_node"

# CAREFULL : "ANY_VALUE_INDICATOR", "PACKAGER_INDICATOR" and "ID_INDICATOR" are only used in the code to indicate that the user can put any value in a specific location
class URNMetadataFormat(Enum):
    ANY_VALUE_INDICATOR = "<any>"
    PACKAGER_INDICATOR = "<packager>"
    ID_INDICATOR = "<ref_id_or_something_else>"

    LIBRARY_URN = f"{URNObjects.URN_BEGGINING.value}:{PACKAGER_INDICATOR}:{URNObjects.URN_3RD_WORD.value}:{URNObjects.LIBRARY.value}:{ID_INDICATOR}"

    FRAMEWORK_URN = f"{URNObjects.URN_BEGGINING.value}:{PACKAGER_INDICATOR}:{URNObjects.URN_3RD_WORD.value}:{URNObjects.FRAMEWORK.value}:{ID_INDICATOR}"
    FRAMEWORK_BASE_URN = f"{URNObjects.URN_BEGGINING.value}:{PACKAGER_INDICATOR}:{URNObjects.URN_3RD_WORD.value}:{URNObjects.REQ_NODE.value}:{ID_INDICATOR}"

    MAPPING_URN = f"{URNObjects.URN_BEGGINING.value}:{PACKAGER_INDICATOR}:{URNObjects.URN_3RD_WORD.value}:{URNObjects.REQ_MAPPING_SET.value}:{ID_INDICATOR}"
    MAPPING_SOURCE_AND_TARGET_FRAMEWORK_URN = FRAMEWORK_URN
    MAPPING_SOURCE_AND_TARGET_NODE_BASE_URN = FRAMEWORK_BASE_URN

    THREATS_BASE_URN = f"{URNObjects.URN_BEGGINING.value}:{PACKAGER_INDICATOR}:{URNObjects.URN_3RD_WORD.value}:{URNObjects.THREAT.value}:{ID_INDICATOR}"

    REFERENCE_CONTROLS_BASE_URN = f"{URNObjects.URN_BEGGINING.value}:{PACKAGER_INDICATOR}:{URNObjects.URN_3RD_WORD.value}:{URNObjects.REFERENCE_CONTROL.value}:{ID_INDICATOR}"

    MATRIX_URN = f"{URNObjects.URN_BEGGINING.value}:{PACKAGER_INDICATOR}:{URNObjects.URN_3RD_WORD.value}:{URNObjects.MATRIX.value}:{ID_INDICATOR}"

# ─────────────────────────────────────────────────────────────
# MISC
# ─────────────────────────────────────────────────────────────

def check_file_validity(files: List[str] | str, filetype_name: str, valid_file_extensions: Tuple[str] = None, file_context: str = None):
    
    fct_name = get_current_fct_name()
    
    if type(files) == str:
        files = [files]

    for f in files:
        if not os.path.exists(f):
            raise ValueError(f"({fct_name}) {(f'[{file_context}] ' if file_context else "")}\"{f}\" doesn't exist")

        if not os.path.isfile(f):
            raise ValueError(f"({fct_name}) {(f'[{file_context}] ' if file_context else "")}\"{f}\" isn't a file")

        if valid_file_extensions and not os.path.basename(f).endswith(valid_file_extensions):
            raise ValueError(
                f"({fct_name}) {(f'[{file_context}] ' if file_context else "")}\"{f}\" isn't a valid {filetype_name} file"
                f"\n> 💡 Valid {filetype_name} file formats : " + ", ".join(f"{f}" for f in valid_file_extensions)
            )


# > Useful for "get_yaml_section_from_files()".
# As the base_urn of "threats" and "reference_controls" isn't written directly in the YAML file,
# it'll be deduced by comparing 2 "threats" (or "reference_controls") URNs.
# If there's only 1 element in the "threats" (or "reference_controls") list, it'll return "None".
# It'll also return "None" if nothing matches between the first 2 elements in the list.
def __calculate_base_urn(items):
    if len(items) < 2:
        return None

    urn1 = items[0].get("urn", "")
    urn2 = items[1].get("urn", "")

    # Find common prefix by parts (split by ':')
    parts1 = urn1.split(":")
    parts2 = urn2.split(":")

    common_parts = []
    for p1, p2 in zip(parts1, parts2):
        if p1 == p2:
            common_parts.append(p1)
        else:
            break

    return ":".join(common_parts) if common_parts else None


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

# Check URN format in a [META] sheet
def validate_urn_type(urn: str, urn_type: URNMetadataFormat, context: str, row: str | int = None):

    split_urn = urn.split(":")
    split_urn_type = urn_type.value.split(":")
    
    INDICATORS = [
        URNMetadataFormat.ANY_VALUE_INDICATOR.value,
        URNMetadataFormat.PACKAGER_INDICATOR.value,
        URNMetadataFormat.ID_INDICATOR.value
    ]

    for idx, urn_type_part in enumerate(split_urn_type):
        
        # If we can put anything, skip
        if urn_type_part in INDICATORS:
            continue
        
        if urn_type_part != split_urn[idx]:
            raise ValueError(
                f"({context if context else 'validate_urn'}){' Row #'+str(row)+':' if row else ""} Invalid URN format \"{urn}\" (Invalid element #{idx+1})"
                f"\n> 💡 Tip: Make sure the URN follows this format: {urn_type.value}"
            )
    

def validate_urn(urn: str, context: str = None, row: str | int = None):
    pattern = r"^urn:([a-z0-9._-]+:)*[a-z0-9._-]+$"
    if not re.fullmatch(pattern, urn):
        raise ValueError(f"({context if context else 'validate_urn'}){' Row #'+str(row)+':' if row else ""} Invalid URN \"{urn}\" : Only lowercase alphanumeric characters, '-', '_', and '.' are allowed. URNs must begin with \"urn:\"")

def validate_ref_id(ref_id: str, context: str = None, row = None):
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", ref_id):
        raise ValueError(f"({context if context else 'validate_ref_id'}){' Row #'+str(row)+':' if row else ""} Invalid Ref. ID \"{ref_id}\" : Only alphanumeric characters, '-', '_', and '.' are allowed")

def validate_ref_id_with_spaces(ref_id: str, context: str = None, row = None):
    if not re.fullmatch(r"[a-zA-Z0-9._\- ]+", ref_id):
        raise ValueError(f"({context if context else 'validate_ref_id'}){' Row #'+str(row)+':' if row else ""} Invalid Ref. ID \"{ref_id}\" : Only alphanumeric characters, '-', '_', ' ', and '.' are allowed")

def validate_sheet_name(sheet_name: str, context: str = None):
    if not (sheet_name.endswith("_meta") or sheet_name.endswith("_content")):
        raise ValueError(f"({context if context else 'validate_sheet_name'}) Invalid sheet name \"{sheet_name}\". Sheet names must end with '_meta' or '_content'")

def is_valid_locale(locale_str):
    return bool(re.fullmatch(r"[a-z0-9]{2}", locale_str))

def validate_no_spaces(value: str, value_name: str, context: str = None, row: int = None):
    if " " in str(value):
        raise ValueError(f"({context if context else 'validate_no_spaces'}){' Row #' + str(row) + ':' if row is not None else ''} Invalid value for \"{value_name}\": Spaces are not allowed (got \"{value}\")")

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
def validate_meta_sheet(df, sheet_name: str, expected_keys:List[str], expected_type: MetaTypes, context: str):
    
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

    if str(type_value).strip() != expected_type.value:
        raise ValueError(f"({context}) [{sheet_name}] Row #{type_row_index + 1}: Invalid type \"{type_value}\". Expected \"{expected_type.value}\"")
    

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

    fct_name = get_current_fct_name()
    
    expected_type = MetaTypes.LIBRARY
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
    validate_urn_type(urn_value, URNMetadataFormat.LIBRARY_URN, fct_name, urn_row)

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

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.FRAMEWORK
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
    validate_urn_type(urn_value, URNMetadataFormat.FRAMEWORK_URN, fct_name, urn_row)

    # base_urn
    base_urn_value = df[df.iloc[:, 0] == "base_urn"].iloc[0, 1]
    base_urn_row = df[df.iloc[:, 0] == "base_urn"].index[0] + 1
    validate_urn(base_urn_value, fct_name, base_urn_row)
    validate_urn_type(base_urn_value, URNMetadataFormat.FRAMEWORK_BASE_URN, fct_name, base_urn_row)

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

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.THREATS
    expected_keys = ["base_urn"]
    # No optional keys

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # base_urn
    base_urn_value = df[df.iloc[:, 0] == "base_urn"].iloc[0, 1]
    base_urn_row = df[df.iloc[:, 0] == "base_urn"].index[0] + 1
    validate_urn(base_urn_value, fct_name, base_urn_row)
    validate_urn_type(base_urn_value, URNMetadataFormat.THREATS_BASE_URN, fct_name, base_urn_row)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Reference Controls {OK}
def validate_reference_controls_meta(df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.REFERENCE_CONTROLS
    expected_keys = ["base_urn"]
    # No optional keys

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # base_urn
    base_urn_value = df[df.iloc[:, 0] == "base_urn"].iloc[0, 1]
    base_urn_row = df[df.iloc[:, 0] == "base_urn"].index[0] + 1
    validate_urn(base_urn_value, fct_name, base_urn_row)
    validate_urn_type(base_urn_value, URNMetadataFormat.REFERENCE_CONTROLS_BASE_URN, fct_name, base_urn_row)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Risk Matrix {OK}
def validate_risk_matrix_meta(df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.RISK_MATRIX
    expected_keys = ["urn", "ref_id", "name", "description"]
    # No optional keys

    validate_meta_sheet(df, sheet_name, expected_keys, expected_type, fct_name)

    # URN
    urn_value = df[df.iloc[:, 0] == "urn"].iloc[0, 1]
    urn_row = df[df.iloc[:, 0] == "urn"].index[0] + 1 
    validate_urn(urn_value, fct_name, urn_row)
    validate_urn_type(urn_value, URNMetadataFormat.MATRIX_URN, fct_name, urn_row)

    # ref_id
    ref_id_value = df[df.iloc[:, 0] == "ref_id"].iloc[0, 1]
    ref_id_row = df[df.iloc[:, 0] == "ref_id"].index[0] + 1
    validate_ref_id(ref_id_value, fct_name, ref_id_row)

    # Extra locales
    validate_extra_locales_in_meta(df, sheet_name, fct_name)

    print_sheet_validation(sheet_name, verbose, ctx)


# [META] Implementation Groups {OK}
def validate_implementation_groups_meta(wb: Workbook, df, sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.IMPLEMENTATION_GROUPS
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

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.REQUIREMENT_MAPPING_SET
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
    validate_urn_type(urn_value, URNMetadataFormat.MAPPING_URN, fct_name, urn_row)

    # source_framework_urn
    source_framework_urn_value = df[df.iloc[:, 0] == "source_framework_urn"].iloc[0, 1]
    source_framework_urn_row = df[df.iloc[:, 0] == "source_framework_urn"].index[0] + 1 
    validate_urn_type(source_framework_urn_value, URNMetadataFormat.MAPPING_SOURCE_AND_TARGET_FRAMEWORK_URN, fct_name, source_framework_urn_row)

    # target_framework_urn
    target_framework_urn_value = df[df.iloc[:, 0] == "target_framework_urn"].iloc[0, 1]
    target_framework_urn_row = df[df.iloc[:, 0] == "target_framework_urn"].index[0] + 1 
    validate_urn_type(target_framework_urn_value, URNMetadataFormat.MAPPING_SOURCE_AND_TARGET_FRAMEWORK_URN, fct_name, target_framework_urn_row)

    # source_node_base_urn
    source_node_base_urn_value = df[df.iloc[:, 0] == "source_node_base_urn"].iloc[0, 1]
    source_node_base_urn_row = df[df.iloc[:, 0] == "source_node_base_urn"].index[0] + 1 
    validate_urn_type(source_node_base_urn_value, URNMetadataFormat.MAPPING_SOURCE_AND_TARGET_NODE_BASE_URN, fct_name, source_node_base_urn_row)

    # target_node_base_urn
    target_node_base_urn_value = df[df.iloc[:, 0] == "target_node_base_urn"].iloc[0, 1]
    target_node_base_urn_row = df[df.iloc[:, 0] == "target_node_base_urn"].index[0] + 1 
    validate_urn_type(target_node_base_urn_value, URNMetadataFormat.MAPPING_SOURCE_AND_TARGET_NODE_BASE_URN, fct_name, target_node_base_urn_row)

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

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.SCORES
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

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.ANSWERS
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

    fct_name = get_current_fct_name()

    expected_type = MetaTypes.URN_PREFIX
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
    
    required_values_missing = []
    invalid_ref_ids = []
    
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
                    required_values_missing.append(idx)
                    # raise ValueError(f"({context}) [{sheet_name}] Row #{idx + 2}: Required value missing in column \"{col}\"")

                if col in ["ref_id", "id"]:
                    try:
                        validate_ref_id(str(value), context, idx)
                    except Exception as e:
                        invalid_ref_ids.append((str(value), idx))
            
            if required_values_missing:
                raise ValueError(
                    f"({context}) [{sheet_name}] Required values missing in column \"{col}\":\n   - "
                    + "\n   - ".join(f'Row #{idx + 2}' for idx in required_values_missing)
                )
            
            if invalid_ref_ids:
                raise ValueError(
                    f"({context}) [{sheet_name}] Invalid Ref. IDs found. Only alphanumeric characters, '-', '_', and '.' are allowed :\n   - "
                    + "\n   - ".join(f'Row #{idx + 2}: {value}' for value, idx in invalid_ref_ids)
                )


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


# Replace the suffix of each sheet name in the list with the target sheet type suffix. Valid suffixes are defined in SheetTypes.
def get_corresponding_type_sheet_names(sheet_names: List[str], sheet_type: SheetTypes) -> List[str]:

    suffixes = [t.value for t in SheetTypes]
    result = []

    for name in sheet_names:
        matched = False

        for suffix in suffixes:
            if name.endswith(suffix):
                # Replace the exact matching suffix at the end of the name with the target suffix
                new_name = re.sub(re.escape(suffix) + r'$', sheet_type.value, name)
                result.append(new_name)
                matched = True
                break

        if not matched:
            raise ValueError(f"Invalid sheet name: \"{name}\" does not end with a known sheet type suffix {suffixes}")

    return result


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

            # Convert each cells as raw text (or "None" if empty)
            # Line added to avoid the problem were numbers (like "1") are converted into floats (1.0)
            header = [str(c).strip() if c is not None else None for c in values[0]]
            rows = [[str(c).strip() if c is not None else None for c in row] for row in values[1:]]
            
            df_fw = pd.DataFrame(rows, columns=header)  # use header

            if target_column not in df_fw.columns:
                continue

            for cell in df_fw[target_column].dropna().astype(str):
                if pd.isna(cell):
                    continue

                entries = [entry.strip() for entry in re.split(r'[,\n]', str(cell)) if entry.strip()]

                if _id in entries:
                    found = True
                    break  # No need to keep looking in this sheet

            if found:
                break  # Found in one sheet : Stop checking this ID

        if not found:
            unused_ids.append(_id)

    if unused_ids:
        msg = (
            f"⚠️  [WARNING] ({context}) [{sheet_name}] The following ID(s) from column \"{id_column}\" are not used in any framework sheet:\n   - "
            f"{'\n   - '.join(f'{x}' for x in unused_ids)}\n"
            "> 💡 Tip: Use these IDs in a framework sheet, or remove them if not needed."
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
            f"{', '.join(f'\"{x}\"' for x in unused_ids)}\n"
            "> 💡 Tip: Use these Prefix IDs in a framework sheet, or remove them if not needed."
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
def _URN_prefix_classify_prefix_usage(wb: Workbook, df_urn_prefix: pd.DataFrame, meta_sheets: List[str], meta_type: MetaTypes, sheet_name: str, fct_name: str, ctx: ConsoleContext = None) -> Tuple[List[str], List[str], List[str]]:
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
    internal_meta_sheets = []

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
                        internal_meta_sheets.append(sheet)
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

    return internal_prefixes, external_prefixes, internal_meta_sheets


# Print information indicating whether the references mentioned in a URN prefix sheet are internal or external to the current workbook.
def print_info_about_internal_external_URN_prefix(sheet_name: str, internal_threats: List[str], external_threats: List[str], internal_ref_ctrl: List[str], external_ref_ctrl: List[str], context: str = None, verbose: bool = False, ctx: ConsoleContext = None, all_verbose: bool = False):
    
    verbose_icon = "💬 "
    
    if internal_threats:
        msg = f"ℹ️  [INFO] ({context}) [{sheet_name}] Internal \"threats\" prefixes found: {', '.join(f'\"{x}\"' for x in internal_threats)}"

        if all_verbose and verbose:
            msg = verbose_icon + msg
            print(msg)

            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)

        elif not all_verbose:
            print(msg)

    else:
        if verbose:
            msg = f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] No internal \"threats\" prefixes found"
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)

    if external_threats:
        msg = f"ℹ️  [INFO] ({context}) [{sheet_name}] External \"threats\" prefixes found: {', '.join(f'\"{x}\"' for x in external_threats)}"

        if all_verbose and verbose:
            msg = verbose_icon + msg
            print(msg)

            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)

        elif not all_verbose:
            print(msg)

    else:
        if verbose:
            msg = f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] No external \"threats\" prefixes found"
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)

    # Info messages for "reference_controls"
    if internal_ref_ctrl:
        msg = f"ℹ️  [INFO] ({context}) [{sheet_name}] Internal \"reference_controls\" prefixes found: {', '.join(f'\"{x}\"' for x in internal_ref_ctrl)}"

        if all_verbose and verbose:
            msg = verbose_icon + msg
            print(msg)

            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)
        elif not all_verbose:
            print(msg)

    else:
        if verbose:
            msg = f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] No internal \"reference_controls\" prefixes found"
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)

    if external_ref_ctrl:
        msg = f"ℹ️  [INFO] ({context}) [{sheet_name}] External \"reference_controls\" prefixes found: {', '.join(f'\"{x}\"' for x in external_ref_ctrl)}"

        if all_verbose and verbose:
            msg = verbose_icon + msg
            print(msg)

            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)

        elif not all_verbose:
            print(msg)

    else:
        if verbose:
            msg = f"💬 ℹ️  [INFO] ({context}) [{sheet_name}] No external \"reference_controls\" prefixes found"
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)


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
        quoted_pairs = '\n   - '.join(f'["{s}", "{t}"]' for s, t in duplicate_pairs)

        msg = (
            f"({context}) [{sheet_name}] Duplicate mapping(s) found for [source_node_id + target_node_id] pair(s):\n   - {quoted_pairs}"
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


def _framework_validate_column_against_reference_sheet(wb: Workbook, df: pd.DataFrame, column_name: str, current_sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None):

    context = get_current_fct_name()

    column_to_key_mapping = {
        "implementation_groups": "implementation_groups_definition",
        "answer": "answers_definition"
    }

    if column_name not in column_to_key_mapping:
        raise ValueError(f"({context}) [{current_sheet_name}] Unsupported column \"{column_name}\" for this validation")

    # Get associated meta sheet
    meta_sheet_name = get_corresponding_type_sheet_names([current_sheet_name], SheetTypes.META)[0]
    if meta_sheet_name not in wb.sheetnames:
        raise ValueError(f"({context}) [{current_sheet_name}] Missing meta sheet \"{meta_sheet_name}\" required to validate column \"{column_name}\"")

    # Convert meta sheet to DataFrame
    meta_ws = wb[meta_sheet_name]
    meta_df = pd.DataFrame(meta_ws.values)
    meta_df.columns = meta_df.iloc[0]
    meta_df = meta_df.drop(index=0).reset_index(drop=True)

    # Get the referenced sheet name from meta key
    meta_key = column_to_key_mapping[column_name]
    ref_base_name = get_meta_value(meta_df, meta_key, meta_sheet_name)

    if not ref_base_name:
        raise ValueError(
            f"({context}) [{current_sheet_name}] The meta key \"{meta_key}\" is missing or empty, required for column \"{column_name}\".\n"
            f"> 💡 Tip: Either remove column \"{column_name}\" or define a proper value for \"{meta_key}\" in the meta sheet."
        )

    ref_content_sheet = f"{ref_base_name}_content"
    if ref_content_sheet not in wb.sheetnames:
        raise ValueError(f"({context}) [{current_sheet_name}] Referenced sheet \"{ref_content_sheet}\" (from key \"{meta_key}\") not found")

    # Convert referenced sheet to DataFrame
    ref_ws = wb[ref_content_sheet]
    ref_df = pd.DataFrame(ref_ws.values)
    ref_df.columns = ref_df.iloc[0]
    ref_df = ref_df.drop(index=0).reset_index(drop=True)

    if column_name == "implementation_groups":
        ref_column = "ref_id"
        separator = ","
    elif column_name == "answer":
        ref_column = "id"
        separator = "\n"
    else:
        raise RuntimeError(f"({context}) [{current_sheet_name}] Unexpected internal error: invalid column dispatch")

    if ref_column not in ref_df.columns:
        raise ValueError(f"({context}) [{current_sheet_name}] Referenced sheet \"{ref_content_sheet}\" does not contain required column \"{ref_column}\"")

    valid_values = set(ref_df[ref_column].dropna().astype(str).map(str.strip))


    invalid_values = []

    for idx, value in df[column_name].dropna().astype(str).items():
        items = [v.strip() for v in value.split(separator) if v.strip()]
        for i, item in enumerate(items, start=1):
            if item not in valid_values:
                invalid_values.append((idx, item, i))

    if invalid_values:
        raise ValueError(
            f"({context}) [{current_sheet_name}] Invalid values in column \"{column_name}\" :\n   - "
            + "\n   - ".join(f'Row #{idx + 2} (element #{i}) -> {item}' for idx, item, i in invalid_values)
            + f"\n> 💡 Tip: Make sure these values exist in column \"{ref_column}\" of the referenced sheet \"{ref_content_sheet}\"."
        )

    if verbose:
        msg = f'💬 ℹ️  [INFO] ({context}) [{current_sheet_name}] Column \"{column_name}\" has valid values'
        print(msg)
        if ctx:
            ctx.add_sheet_verbose_msg(current_sheet_name, msg)


# For each row, ensure that the number of entries in "questions" matches the number of entries in "answer" (or is 1), unless both are empty.
def _framework_validate_question_answer_alignment(df: pd.DataFrame, sheet_name: str, context: str, verbose: bool = False, ctx: ConsoleContext = None):

    if "questions" not in df.columns or "answer" not in df.columns:
        return  # Skip if one of them is missing — already validated elsewhere

    for idx, row in df.iterrows():
        q_raw = str(row["questions"]).strip() if pd.notna(row["questions"]) else ""
        a_raw = str(row["answer"]).strip() if pd.notna(row["answer"]) else ""

        if not q_raw:
            if a_raw:
                raise ValueError(
                    f"({context}) [{sheet_name}] Row #{idx + 2}: \"questions\" is empty but \"answer\" is not."
                    "\n> 💡 Tip: Either remove the answer or provide a question."
                )
            continue  # both empty = OK

        q_list = [q.strip() for q in q_raw.split("\n") if q.strip()]
        a_list = [a.strip() for a in a_raw.split("\n") if a.strip()]

        q_count = len(q_list)
        a_count = len(a_list)

        if a_count not in [1, q_count]:
            raise ValueError(
                f"({context}) [{sheet_name}] Row #{idx + 2}: Found {q_count} question(s) but {a_count} answer(s)."
                f"\n> 💡 Tip: You must provide either 1 answer for all questions ({q_count} answer{'s' if q_count > 1 else ''}), or one answer per question."
            )

    if verbose:
            msg = f'💬 ℹ️  [INFO] ({context}) [{sheet_name}] Number of entries in the column "questions" matches the number of entries in the column "answer"'
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(sheet_name, msg)


# Validate that all URNs in the column use defined prefix_ids and reference existing ref_ids when required
def _framework_validate_framework_column_urns(wb: Workbook, df: pd.DataFrame, column_name: str, current_sheet_name: str, external_refs: List[str] = None, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()

    if column_name not in ("threats", "reference_controls"):
        raise ValueError(f"({fct_name}) [{current_sheet_name}] Column \"{column_name}\" is not supported for URN validation")

    # ───────────────────────────────────────────────────────────────
    # 1st Part: Load and validate all URN_PREFIX sheets
    # ───────────────────────────────────────────────────────────────

    urn_meta_sheets = get_meta_sheets_names_from_type(wb, MetaTypes.URN_PREFIX)

    if not urn_meta_sheets:
        raise ValueError(
            f"({fct_name}) [{current_sheet_name}] Column \"{column_name}\" cannot be validated because no URN_PREFIX meta sheet exists.\n"
            f"> 💡 Tip: Either remove column \"{column_name}\" or define a valid URN prefix sheet."
        )

    urn_prefix_map = {}     # {prefix_id: (prefix_value, sheet_name)}
    seen_prefix_ids = {}    # {prefix_id: sheet_name}

    for meta_sheet_name in urn_meta_sheets:
        content_sheet = get_corresponding_type_sheet_names([meta_sheet_name], SheetTypes.CONTENT)[0]
        if content_sheet not in wb.sheetnames:
            raise ValueError(f"({fct_name}) [{current_sheet_name}] URN_PREFIX content sheet \"{content_sheet}\" not found")

        content_df = pd.DataFrame(wb[content_sheet].values)
        content_df.columns = content_df.iloc[0]
        content_df = content_df.drop(index=0).reset_index(drop=True)

        # Filter out rows where both 'prefix_id' and 'prefix_value' are empty or null
        content_df = content_df.dropna(subset=["prefix_id", "prefix_value"], how='all')
        content_df = content_df[(content_df["prefix_id"].astype(str).str.strip() != "") | (content_df["prefix_value"].astype(str).str.strip() != "")]

        for _, row in content_df.iterrows():
            prefix_id = str(row.get("prefix_id", "")).strip()
            prefix_value = str(row.get("prefix_value", "")).strip()
            if not prefix_id:
                continue
            if prefix_id in seen_prefix_ids:
                other_sheet = seen_prefix_ids[prefix_id]
                raise ValueError(
                    f"({fct_name}) [{current_sheet_name}] Duplicate prefix_id \"{prefix_id}\" found in sheets \"{meta_sheet_name}\" and \"{other_sheet}\""
                )
            urn_prefix_map[prefix_id] = (prefix_value, content_sheet)
            seen_prefix_ids[prefix_id] = content_sheet

    all_prefix_ids = set(urn_prefix_map.keys())

    # ───────────────────────────────────────────────────────────────
    # 2nd Part: Validate that all URN prefix_id used in the column are known
    # ───────────────────────────────────────────────────────────────

    for idx, value in df[column_name].dropna().astype(str).items():
        elements = re.split(r"[\n,]", value)
        for i, raw in enumerate(elements, start=1):
            raw = raw.strip()
            if not raw or ":" not in raw:
                continue
            prefix_id = raw.split(":", 1)[0].strip()
            if prefix_id not in all_prefix_ids:
                raise ValueError(
                    f"({fct_name}) [{current_sheet_name}] Row #{idx + 2} - Invalid URN prefix \"{prefix_id}\" (element #{i}) in column \"{column_name}\".\n"
                    f"> 💡 Tip: This prefix must be defined in a URN Prefix sheet."
                )

    # ───────────────────────────────────────────────────────────────
    # 3rd Part: Determine internal and external prefixes for threats / reference_controls
    # ───────────────────────────────────────────────────────────────

    threats_meta = get_meta_sheets_names_from_type(wb, MetaTypes.THREATS)
    ref_ctrl_meta = get_meta_sheets_names_from_type(wb, MetaTypes.REFERENCE_CONTROLS)

    all_internal_threats = []
    all_external_threats = []
    all_internal_threat_sheets = []
    all_internal_ref_ctrl = []
    all_external_ref_ctrl = []
    all_internal_ref_ctrl_sheets = []

    for meta_sheet_name in urn_meta_sheets:
        urn_content_sheet = get_corresponding_type_sheet_names([meta_sheet_name], SheetTypes.CONTENT)[0]
        if urn_content_sheet not in wb.sheetnames:
            raise ValueError(f"({fct_name}) [{current_sheet_name}] URN_PREFIX content sheet \"{urn_content_sheet}\" not found")

        df_urn = pd.DataFrame(wb[urn_content_sheet].values)
        df_urn.columns = df_urn.iloc[0]
        df_urn = df_urn.drop(index=0).reset_index(drop=True)

        # Filter out empty rows
        df_urn = df_urn.dropna(how='all')
        df_urn = df_urn[
            df_urn.apply(lambda row: any(str(cell).strip() != "" for cell in row), axis=1)
        ]

        if threats_meta:
            internal_threats, external_threats, internal_threat_sheets = _URN_prefix_classify_prefix_usage(
                wb, df_urn, threats_meta, MetaTypes.THREATS, current_sheet_name, fct_name, ctx
            )
            all_internal_threats.extend(internal_threats)
            all_external_threats.extend(external_threats)
            all_internal_threat_sheets.extend(internal_threat_sheets)

        if ref_ctrl_meta:
            internal_ref_ctrl, external_ref_ctrl, internal_ref_ctrl_sheets = _URN_prefix_classify_prefix_usage(
                wb, df_urn, ref_ctrl_meta, MetaTypes.REFERENCE_CONTROLS, current_sheet_name, fct_name, ctx
            )
            all_internal_ref_ctrl.extend(internal_ref_ctrl)
            all_external_ref_ctrl.extend(external_ref_ctrl)
            all_internal_ref_ctrl_sheets.extend(internal_ref_ctrl_sheets)

    print_info_about_internal_external_URN_prefix(
        current_sheet_name,
        all_internal_threats, all_external_threats,
        all_internal_ref_ctrl, all_external_ref_ctrl,
        fct_name, verbose, ctx, True
    )

    # ───────────────────────────────────────────────────────────────
    # 4th Part: Validate prefix_id types based on column context
    # ───────────────────────────────────────────────────────────────

    allowed_prefix_ids = set()
    forbidden_prefix_ids = set()

    # We must use prefix_id (not URNs) to detect valid or invalid use
    if column_name == "threats":
        allowed_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_internal_threats or pval in all_external_threats}
        forbidden_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_internal_ref_ctrl or pval in all_external_ref_ctrl}
    elif column_name == "reference_controls":
        allowed_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_internal_ref_ctrl or pval in all_external_ref_ctrl}
        forbidden_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_internal_threats or pval in all_external_threats}

    for idx, value in df[column_name].dropna().astype(str).items():
        elements = re.split(r"[\n,]", value)
        for i, raw in enumerate(elements, start=1):
            raw = raw.strip()
            if not raw:
                continue

            prefix_id = raw.split(":", 1)[0].strip()

            if prefix_id in forbidden_prefix_ids:
                raise ValueError(
                    f"({fct_name}) [{current_sheet_name}] Row #{idx + 2} - Invalid URN prefix \"{prefix_id}\" (element #{i}) in column \"{column_name}\"."
                    f"\n> 💡 Tip: This prefix is not allowed in column \"{column_name}\", as the URN to which it refers is not a \"{column_name}\" URN."
                )

    # Dict prefix_value -> "sheet_content" for "threats"
    prefix_to_threats_content_sheet = {}

    for i, prefix_val in enumerate(all_internal_threats):
        # Correspondence index => internal threat content sheet
        if i < len(all_internal_threat_sheets):
            meta_sheet_name = all_internal_threat_sheets[i]
            content_sheet_name = get_corresponding_type_sheet_names([meta_sheet_name], SheetTypes.CONTENT)[0]
            prefix_to_threats_content_sheet[prefix_val] = content_sheet_name

    # Dict prefix_value -> "sheet_content" for "reference_controls"
    prefix_to_refctrl_content_sheet = {}

    for i, prefix_val in enumerate(all_internal_ref_ctrl):
        if i < len(all_internal_ref_ctrl_sheets):
            meta_sheet_name = all_internal_ref_ctrl_sheets[i]
            content_sheet_name = get_corresponding_type_sheet_names([meta_sheet_name], SheetTypes.CONTENT)[0]
            prefix_to_refctrl_content_sheet[prefix_val] = content_sheet_name

    # ───────────────────────────────────────────────────────────────
    # 5th Part: Validate that internal URN values exist in ref_id column only
    # ───────────────────────────────────────────────────────────────

    if column_name == "threats":
        internal_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_internal_threats}
    else:  # reference_controls
        internal_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_internal_ref_ctrl}

    
    for prefix_id in internal_prefix_ids:
        prefix_value, _ = urn_prefix_map[prefix_id]

        # Get the actual content sheet name based on the column type
        content_sheet = None

        if column_name == "threats":
            content_sheet = prefix_to_threats_content_sheet.get(prefix_value)
        else:  # reference_controls
            content_sheet = prefix_to_refctrl_content_sheet.get(prefix_value)

        if not content_sheet:
            raise ValueError(
                f"({fct_name}) [{current_sheet_name}] Referenced content sheet for prefix_value \"{prefix_value}\" (prefix_id \"{prefix_id}\") not found"
            )

        if content_sheet not in wb.sheetnames:
            raise ValueError(
                f"({fct_name}) [{current_sheet_name}] Referenced content sheet \"{content_sheet}\" not found in workbook"
            )

        # Get reference sheet
        content_df = pd.DataFrame(wb[content_sheet].values)
        content_df.columns = content_df.iloc[0]
        content_df = content_df.drop(index=0).reset_index(drop=True)

        # Only check "ref_id" column of the reference sheet
        if "ref_id" not in content_df.columns:
            raise ValueError(
                f"({fct_name}) [{current_sheet_name}] Sheet \"{content_sheet}\" has no \"ref_id\" column"
            )

        valid_ref_ids = set(content_df["ref_id"].astype(str).str.strip())

        verification_errors = []

        # Check Ref. IDs validity
        for idx, value in df[column_name].dropna().astype(str).items():
            elements = re.split(r"[\n,]", value)
            for i, raw in enumerate(elements, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                # Only process elements that start with the expected prefix (e.g. "1:REF")
                if not raw.startswith(prefix_id + ":"):
                    continue

                # Extract the REF part after the first ":"
                urn_id = raw.split(":", 1)[1].strip()

                # Check if it exists in the ref_ids from reference sheet
                if urn_id not in valid_ref_ids:
                    verification_errors.append((idx, i, urn_id, prefix_id))

        # Print all errors and exit
        if verification_errors:
            msgs = []
            for idx, i, urn_id, prefix_id in verification_errors:
                msgs.append(f"   - Row #{idx + 2} (element #{i}) -> ref_id \"{urn_id}\" with prefix \"{prefix_id}\" ({prefix_id}:{urn_id})")

            msgs.append(f"> 💡 Tip: These IDs must exist in the sheet \"{content_sheet}\" in column \"ref_id\".")
            raise ValueError(f"({fct_name}) [{current_sheet_name}] Invalid internal references found in column \"{column_name}\":\n" + "\n".join(msgs))
        
    # ───────────────────────────────────────────────────────────────
    # 6th Part: Validate that external URN values exist in external references from YAML files only
    # ───────────────────────────────────────────────────────────────

    if column_name == "threats":
        external_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_external_threats}
    else:  # reference_controls
        external_prefix_ids = {pid for pid, (pval, _) in urn_prefix_map.items() if pval in all_external_ref_ctrl}

    yaml_section_type = None
    if column_name == "threats":
        yaml_section_type = YAMLSectionTypes.THREATS
    else:  # reference_controls
        yaml_section_type = YAMLSectionTypes.REFERENCE_CONTROLS


    yaml_external_references_retrieved = False
    yaml_references_from_files = None

    # Get references in YAML files
    if external_prefix_ids:

        # If there are external references in the Excel file, but no YAML files containing external references are given as argument
        if not external_refs:
            msg = (
                f"⚠️  [WARNING] ({fct_name}) [{current_sheet_name}] No YAML files provided as external references to check external references in column \"{column_name}\" (URN Prefix concerned: " + ", ".join(f"\"{f}\"" for f in external_prefix_ids) + ")\n" 
                f"> ❌ Unable to check for external \"{yaml_section_type.value}\" !\n"
                f"> 💡 Tip: Provide the right YAML file(s) as argument, corresponding to the external references, that contain a \"{yaml_section_type.value}\" section"
            )
            print(msg)
            if ctx:
                ctx.add_sheet_warning_msg(current_sheet_name, msg)

        # Else if there are external references in the Excel file, and YAML file(s) containing external references is(are) given as argument
        else:
            yaml_references_from_files = get_yaml_section_from_files(external_refs, yaml_section_type, current_sheet_name, verbose, ctx)

            if yaml_references_from_files:
                yaml_external_references_retrieved = True
            if not yaml_references_from_files:
                msg = (
                    f"⚠️  [WARNING] ({fct_name}) [{current_sheet_name}] None of the YAML files provided as external references contain a \"{yaml_section_type.value}\" section (URN prefixes requiring verification of external references: " + ", ".join(f"\"{f}\"" for f in external_prefix_ids) + ")\n"
                    f"> ❌ Unable to check for external \"{yaml_section_type.value}\" !\n"
                    f"> 💡 Tip: Make sure the YAML file(s) you provided as argument actually contain a \"{yaml_section_type.value}\" section."
                )
                print(msg)
                if ctx:
                    ctx.add_sheet_warning_msg(current_sheet_name, msg)


    # Not checked reference list
    not_checked_prefix_id = []

    # Check external references
    if yaml_references_from_files:
        
        for prefix_id in external_prefix_ids:
            prefix_value, _ = urn_prefix_map[prefix_id]
            
            yaml_filename = ""
            
            # Search for the "prefix_value" in "yaml_references_from_files" and get the corresponding Ref. IDs of the section
            base_urn_with_ref_ids = {}      # { base_urn: { ref_id: name, ... } }

            for filename, file_sections in yaml_references_from_files.items():
                if prefix_value in file_sections:
                    base_urn_with_ref_ids = {prefix_value: file_sections[prefix_value]}
                    yaml_filename = filename
                    break


            # If "yaml_references_from_files" doesn't have the searched "prefix_value"
            if prefix_value not in base_urn_with_ref_ids.keys():
                msg = (
                    f"⚠️  [WARNING] ({fct_name}) [{current_sheet_name}] None of the YAML files provided as external references contain references for the URN Prefix \"{prefix_id}\" ({prefix_value}) (Column \"{column_name}\")\n"
                    f"> 💡 Tip: Specify the right YAML file as an argument to check external \"{yaml_section_type.value}\""
                )
                print(msg)
                if ctx:
                    ctx.add_sheet_warning_msg(current_sheet_name, msg)

                # Add the non checked "prefix_value" to the unchecked element list
                not_checked_prefix_id.append(prefix_value)

                continue
                
            # Validation of Ref. IDs against the external reference extracted from YAML
            yaml_ref_ids_map = base_urn_with_ref_ids.get(prefix_value, {})  # mapping ref_id -> name | { ref_id1: name1, ... }
            valid_ref_ids = set(yaml_ref_ids_map.keys())                    # (ref_id1, ref_id2, ref_id3, ...)
            verification_errors = []

            for idx, value in df[column_name].dropna().astype(str).items():
                elements = re.split(r"[\n,]", value)
                for i, raw in enumerate(elements, start=1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    # Only process elements that start with the expected prefix (e.g. "1:REF")
                    if not raw.startswith(prefix_id + ":"):
                        continue

                    # Extract the REF part after the first ":"
                    urn_id = raw.split(":", 1)[1].strip()

                    # Check if it exists in the ref_ids from YAML
                    if urn_id not in valid_ref_ids:
                        verification_errors.append((idx, i, urn_id, prefix_id))


            # Print all errors and exit
            if verification_errors:
                msgs = []
                for idx, i, urn_id, prefix_id in verification_errors:
                    msgs.append(f"   - Row #{idx + 2} (element #{i}) -> ref_id \"{urn_id}\" with prefix \"{prefix_id}\" ({prefix_id}:{urn_id})")

                msgs.append(f"> 💡 Tip: These Ref. IDs must exist in the YAML file \"{yaml_filename}\" provided as external references (in the \"{yaml_section_type.value}\" section of the YAML file).")
                raise ValueError(f"({fct_name}) [{current_sheet_name}] Invalid external references found in column \"{column_name}\":\n" + "\n".join(msgs))


    # If there are no external reference to check [OR] (there are external references to check [AND] the YAML files contains element of the section we're working on [AND] NOT a single external reference wasn't check)
    if not external_prefix_ids or (external_prefix_ids and yaml_external_references_retrieved and not not_checked_prefix_id):
        if verbose:
            msg = f'💬 ℹ️  [INFO] ({fct_name}) [{current_sheet_name}] Column \"{column_name}\" contains valid URN references'
            print(msg)
            if ctx:
                ctx.add_sheet_verbose_msg(current_sheet_name, msg)
    else:
        msg = (
            f"⚠️  [WARNING] ({fct_name}) [{current_sheet_name}] Column \"{column_name}\" contains valid *internal* URN references. However, something went wrong while checking one or all of the external elements for \"{yaml_section_type.value}\" !\n"
            f"> 💡 Tip: Read the warnings above to understand the problem."
        )
        print(msg)
        if ctx:
            ctx.add_sheet_warning_msg(current_sheet_name, msg)



# Get the "threats" or "reference_controls" section from a YAML Framework file passed as argument
def get_yaml_section_from_files(yaml_files: List[str], section_type: YAMLSectionTypes, current_sheet_name: str, verbose: bool = False, ctx: ConsoleContext = None) -> Dict:
        
    fct_name = get_current_fct_name()

    if type(yaml_files) == str:
        yaml_files = [yaml_files]

    extracted_sections = {}
    """
    - Object structure :
    {
        file: {
            section_urn : {  
                element_ref_id1: name1
                element_ref_id2: name2
                ...
            }
        }
    }
    """
    
    for file in yaml_files:

        # Attempt to load YAML file, raise an error if file is missing or YAML is invalid
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"({fct_name}) [{current_sheet_name}] YAML file not found: \"{file}\"")
        except yaml.YAMLError as e:
            raise ValueError(f"({fct_name}) [{current_sheet_name}] Error parsing YAML file \"{file}\": {e}")


        # Search for the element we want
        for obj_key, obj_value in data.get("objects", {}).items():
            
            # --- [Section] reference_controls [OR] threats ---
            if (
                (section_type == YAMLSectionTypes.REFERENCE_CONTROLS and obj_key == "reference_controls")
                or (section_type == YAMLSectionTypes.THREATS and obj_key == "threats")
            ):

                # Calculate base_urn
                base_urn = __calculate_base_urn(obj_value)
                
                # If the "base_urn" couldn't be defined, skip
                if not base_urn:
                    if verbose:
                        msg = (
                            f"💬 ℹ️  [INFO] ({fct_name}) [{current_sheet_name}] URN of section \"{section_type.value}\" of the YAML file \"{file}\" couldn't be defined.\n"
                            f"> 💡 Tip: This is probably because the \"{section_type.value}\" section of the file contains only 1 element (2 elements are required to determine the \"base_urn\" of the \"{section_type.value}\" section in the YAML file)"
                        )
                        print(msg)
                        if ctx:
                            ctx.add_sheet_verbose_msg(current_sheet_name, msg)

                    break
                
                element_obj = {
                    base_urn: {}
                }
                
                # Store Ref. IDs, associated with their names
                for ref_ctrl in obj_value:
                    ref_id = ref_ctrl.get("ref_id")
                    name = ref_ctrl.get("name")
                    if ref_id:  # on ignore si pas de ref_id
                        element_obj[base_urn][ref_id] = name

                if file not in extracted_sections:
                    extracted_sections[file] = {}
                extracted_sections[file].update(element_obj)
                    
                break


        # If the file doesn't contains the requested section
        if file not in extracted_sections.keys():
            if verbose:
                msg = (f"💬 ℹ️  [INFO] ({fct_name}) [{current_sheet_name}] The YAML file \"{file}\" contains no \"{section_type.value}\" section.")
                print(msg)
                if ctx:
                    ctx.add_sheet_verbose_msg(current_sheet_name, msg)

    return extracted_sections



# [CONTENT] Framework {OK}
def validate_framework_content(wb: Workbook, df: pd.DataFrame, sheet_name, external_refs: List[str] = None, verbose: bool = False, ctx: ConsoleContext = None):

    fct_name = get_current_fct_name()
    required_columns = ["depth"]  # "assessable" isn't there because it can be empty
    optional_columns = [
        "implementation_groups", "description", "threats",
        "reference_controls", "typical_evidence", "annotation",
        "questions", "answer", "urn_id"
    ]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)
    validate_optional_columns_content_sheet(df, sheet_name, optional_columns, fct_name, verbose, ctx)

    # Check that "questions" and "answer" appear together (or not at all)
    has_questions = "questions" in df.columns
    has_answer = "answer" in df.columns

    if has_questions != has_answer:
        missing_col = "answer" if has_questions else "questions"
        raise ValueError(
            f"({fct_name}) [{sheet_name}] Column \"{missing_col}\" is required when column \"{'questions' if missing_col == 'answer' else 'answer'}\" is present."
            f"\n> 💡 Tip: Either provide both \"questions\" and \"answer\" columns, or remove both."
        )

    # Check uniqueness of some column values
    validate_unique_column_values(df, ["ref_id"], sheet_name, fct_name, ctx=ctx)
    
    # Enforce presence of "assessable" column (even if values can be empty)
    if "assessable" not in df.columns:
        raise ValueError(f"[{fct_name}] [{sheet_name}] Missing required column \"assessable\"")

    # Additional rule: for non-empty rows, at least "ref_id", "name" or "description" must be filled
    empty_id_name_desc_rows = []
    invalid_ref_ids = []

    for idx, row in df.iterrows():
        if row.dropna().empty:
            continue  # skip completely empty rows

        ref_id = row.get("ref_id", "")
        if pd.isna(ref_id):
            ref_id = ""
        else:
            ref_id = str(ref_id).strip()

        name = row.get("name", "")
        if pd.isna(name):
            name = ""
        else:
            name = str(name).strip()
            
        description = row.get("description", "")
        if pd.isna(description):
            description = ""
        else:
            description = str(description).strip()


        if not ref_id and not name and not description:
            empty_id_name_desc_rows.append(idx)

        # Check Ref. IDs
        if ref_id:
            try:
                validate_ref_id_with_spaces(ref_id, fct_name, idx)
            except Exception as e:
                invalid_ref_ids.append((ref_id, idx))


    # If any, returns an error and print rows with empty Ref. ID, Name and Description 
    if empty_id_name_desc_rows:
        raise ValueError(
            f"({fct_name}) [{sheet_name}] Invalid rows: \"ref_id\", \"name\" and \"description\" are empty :\n   - "
            + "\n   - ".join(f'Row #{idx + 2}' for idx in empty_id_name_desc_rows)
            + "\n> 💡 Tip: For each row, at least one of the values must be filled."
        )

    # If any, returns an error and print invalid Ref. IDs
    if invalid_ref_ids:
        raise ValueError(
            f"({fct_name}) [{sheet_name}] Invalid Ref. IDs found. Only alphanumeric characters, '-', '_', ' ', and '.' are allowed :\n   - "
            + "\n   - ".join(f'Row #{idx + 2}: {value}' for value, idx in invalid_ref_ids)
        )


    # Validate columns that reference other sheets (only if they contain non-empty values)
    for column in ["implementation_groups", "answer"]:
        if column in df.columns:
            non_empty_values = df[column].dropna().astype(str).map(str.strip)
            if not non_empty_values[non_empty_values != ""].empty:
                _framework_validate_column_against_reference_sheet(wb, df, column, sheet_name, verbose, ctx)

    # Validate URN-related columns only if they contain non-empty values
    for column in ["threats", "reference_controls"]:
        if column in df.columns:
            non_empty_values = df[column].dropna().astype(str).map(str.strip)
            if not non_empty_values[non_empty_values != ""].empty:
                _framework_validate_framework_column_urns(wb, df, column, sheet_name, external_refs, verbose, ctx)

    # Ensure that the number of "questions" and "answer" entries match per row (1 or same count), or both are empty
    _framework_validate_question_answer_alignment(df, sheet_name, fct_name, verbose, ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)

    print_sheet_validation(sheet_name, verbose, ctx)


# [CONTENT] Threats {OK}
def validate_threats_content(df, sheet_name, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    required_columns = ["ref_id", "name"]
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
    required_columns = ["ref_id", "name"]
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
    required_columns = ["type", "id", "abbreviation", "name", "description"]
    # No optional columns

    # Special values
    type_values = ["probability", "impact", "risk"]

    validate_content_sheet(df, sheet_name, required_columns, fct_name)

    # Check if values in "type" column are valid
    validate_allowed_column_values(df, "type", type_values, sheet_name, fct_name,ctx=ctx)

    # Extra locales
    validate_extra_locales_in_content(df, sheet_name, fct_name, ctx, verbose)


    msg = (
        f"⚠️  [WARNING] ({fct_name}) [{sheet_name}] In this script, Matrix content sheet verification is partially implemented."
        f"\n> 💡 Tip: Matrix verification will be improved in a future update."
    )
    print(msg)
    if ctx:
        ctx.add_sheet_warning_msg(sheet_name, msg)

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
    frameworks_with_imp_grp = get_corresponding_type_sheet_names(frameworks_with_imp_grp, SheetTypes.CONTENT)

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
    required_columns = ["score", "name"]
    optional_columns = ["description_doc", "description"]

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
    frameworks_with_answers = get_corresponding_type_sheet_names(frameworks_with_answers, SheetTypes.CONTENT)

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
    framework_sheets = get_corresponding_type_sheet_names(framework_sheets, SheetTypes.CONTENT)

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
    internal_threats = []
    external_threats = []
    internal_ref_ctrl = []
    external_ref_ctrl = []
    
    if threats_sheets:
        internal_threats, external_threats, _ = _URN_prefix_classify_prefix_usage(wb, df, threats_sheets, MetaTypes.THREATS, sheet_name, fct_name, ctx)
    if ref_ctrl_sheets:
        internal_ref_ctrl, external_ref_ctrl, _ = _URN_prefix_classify_prefix_usage(wb, df, ref_ctrl_sheets, MetaTypes.REFERENCE_CONTROLS, sheet_name, fct_name, ctx)

    # Info messages for "threats"
    print_info_about_internal_external_URN_prefix(sheet_name, internal_threats, external_threats, internal_ref_ctrl, external_ref_ctrl, fct_name, verbose, ctx)

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


def dispatch_content_validation(wb: Workbook, df, sheet_name: str, corresponding_meta_type: str, external_refs: List[str] = None, verbose: bool = False, ctx: ConsoleContext = None):
    
    fct_name = get_current_fct_name()
    
    if corresponding_meta_type == MetaTypes.FRAMEWORK.value:
        validate_framework_content(wb, df, sheet_name, external_refs, verbose, ctx)
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

def validate_excel_structure(filepath, external_refs: List[str] = None, verbose: bool = False, ctx: ConsoleContext = None):

    fct_name = get_current_fct_name()

    # Check provided YAML external reference
    if external_refs:
        check_file_validity(external_refs, "YAML", (".yaml", "yml"), "External Reference")

    # Check Excel file
    check_file_validity(filepath, "Excel", (".xlsx", ".xlsm", ".xltx", ".xltm"))


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
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=None, dtype=str, keep_default_na=False)
            meta_sheets[sheet_name] = df
        elif sheet_name.endswith("_content"):
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=0, dtype=str, keep_default_na=False)
            content_sheets[sheet_name] = df
        else:
            ignored_sheets.append(sheet_name)

    if not "library_meta" in meta_sheets:
        raise ValueError(
            f"({fct_name}) [{sheet_name}] No \"library_meta\" sheet found."
            f"\n> 💡 Tip: Ensure your Excel file \"{file_name}\" is in v2 format."
        )

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
        dispatch_content_validation(wb, df, sheet_name, meta_types[base_name], external_refs, verbose, ctx)

    # Warn about ignored sheets
    for sheet_name in ignored_sheets:
        msg = f"⏩ [SKIP] Ignored sheet \"{sheet_name}\" (does not end with \"_meta\" or \"_content\")"
        print(msg)

    print("")

    if ctx.count_all_warnings() > 0:
        print(f"✅⚠️  [SUCCESS] Excel structure validation ended with warnings for \"{file_name}\"")
        print(f"📜 [SUMMARY] ⚠️  Total [WARNING] for \"{file_name}\": {ctx.count_all_warnings()}")
    else:
        print(f"✅ [SUCCESS] Excel structure is valid for \"{file_name}\"")

    if verbose and ctx.count_all_verbose() > 0:
        print(f"📜 [SUMMARY] 💬 Total [Verbose Messages] for \"{file_name}\": {ctx.count_all_verbose()}")



# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate Excel file structure (v2 format)", formatter_class=argparse.RawTextHelpFormatter,)
    parser.add_argument(
        "file_input",
        help="Path to Excel file to validate."
    )

    parser.add_argument(
        "-e", "--external-refs",
        type=str,
        help="YAML files containing external references mentioned in the library.\n"
        "Use it to check the following columns if necessary : \"threats\", \"reference_controls\".\n"
        "Separate external references with commas (e.g., ./threats1.yaml,./refs/ref_ctrl.yaml,../test.yaml)",
    )

    parser.add_argument(
        "-b", "--bulk",
        action="store_true",
        help="Enable bulk mode to process all Excel files in a directory.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output. Verbose messages start with a 💬 (speech bubble) emoji."
    )

    args = parser.parse_args()


    # Store YAML external references filenames in a list 
    external_refs = []
    if args.external_refs:
        external_refs = args.external_refs.split(",")        


    # If "enable_ctx == True", the "ConsoleContext" object will be enabled and returned by the function
    enable_ctx = True
    err = False
    
    # --- BULK CHECK ------------------------------------------------------------
    if args.bulk:
        _, err = bulk_check(args, external_refs, enable_ctx)

    # --- SINGLE FILE CHECK -----------------------------------------------------
    else:
        _, err = single_file_check(args, external_refs, enable_ctx)


    if err:
        sys.exit(1)
    else:
        sys.exit(0)



def bulk_check(args, external_refs: List[str] = None, enable_ctx: bool = False) -> Tuple[Dict[str, ConsoleContext], List[str]]:
    
    ctxs: Dict[str, ConsoleContext] = {}   # List of all contexts
    """
    {
        file1: ctx1,
        file2: ctx2,
        ...
    }
    """
    
    input_path = Path(args.file_input)
    if not input_path.is_dir():
        print("❌ [ERROR] Bulk mode requires a directory as input")
        sys.exit(1)


    error_files = []  # Collect names of files that failed
    
    # Find all Excel files in the input directory (temp Excel files starting with "~$" are excluded)
    valid_exts = {".xlsx", ".xlsm", ".xltx", ".xltm"}       # Excel Extensions allowed
    excel_files = [
        f for f in input_path.iterdir()
        if f.suffix.lower() in valid_exts and not f.name.startswith("~$")
    ]

    if not excel_files:
        print(f'❌ [ERROR] No Excel files found in directory: "{input_path}". Abort...')
        sys.exit(1)

    for i, file in enumerate(excel_files):
        
        temp_ctx = None
        
        if enable_ctx:
            temp_ctx = ConsoleContext()
        
        try:
            if i > 0:
                print("\n-------------------------------------------------------------------\n")
            print(f'▶️  Processing file [{i + 1}/{len(excel_files)}]: "{file}"')
            validate_excel_structure(str(file), external_refs, args.verbose, temp_ctx)
        except Exception as e:
            print(f'❌ [ERROR] Failed to process "{file.name}":\n🛑 {e}')
            error_files.append(file.name)


        if enable_ctx:
            ctxs[file.name] = temp_ctx


    # Summary at the end of bulk processing
    print("\n###################################################################\n")
    print("📋 Bulk mode completed!")


    warning_files = []

    # Check files with at least 1 warning
    for file, ctx in ctxs.items():
        if ctx.count_all_warnings() > 0: warning_files.append(file)


    # Print files that got at least 1 warning
    if warning_files:
        print(f"⚠️  The following file{'s' if len(error_files) > 1 else ''} encountered at least 1 warning:")

        for f in warning_files:
            print(f"   - {f}")


    # Print files that encounter an error
    if error_files:
        print(f"❌ The following file{'s' if len(error_files) > 1 else ''} failed to process:")

        for f in error_files:
            print(f"   - {f}")


    if warning_files or error_files: 
        if not args.verbose:
            print('💡 Tip: Use "--verbose" to display hidden messages. This can help to understand certain errors.')
    else:
        print("✅ All files processed successfully!")


    return ctxs, error_files


def single_file_check(args, external_refs: List[str] = None, enable_ctx: bool = False) -> Tuple[ConsoleContext, bool]:
    
    ctx = None
    error_encountered = False
    
    if enable_ctx:
        ctx = ConsoleContext()

    try:
        validate_excel_structure(args.file_input, external_refs, args.verbose, ctx)
        if not args.verbose:
                print("💡 Tip: Use \"--verbose\" to display hidden messages. This can help to understand certain errors.")
    except Exception as e:
        print(f"❌ [FATAL ERROR] {e}")
        if not args.verbose:
                print("💡 Tip: Use \"--verbose\" to display hidden messages. This can help to understand certain errors.")
        error_encountered = True

    return ctx, error_encountered


if __name__ == "__main__":
    main()
