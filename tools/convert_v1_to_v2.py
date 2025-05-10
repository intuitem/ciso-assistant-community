# This script converts a CISO Assistant Excel library from v1 to v2 format
# v1 is the original format, with library_content tab
# v2 is the newer format, with _meta and _content tabs

import pandas as pd
from pathlib import Path
import argparse

def convert_v1_to_v2(input_path: str, output_path: str):
    xls = pd.read_excel(input_path, sheet_name=None)

    library_content = xls.get("library_content")
    if library_content is None:
        raise ValueError("Missing 'library_content' sheet.")

    library_meta = [("type", "library")]
    tab_entries = []
    object_metadata = {}
    declared_tabs = {}
    urn_prefixes = {}

    known_object_types = {
        "framework", "requirements", "threats", "reference_controls",
        "scores", "implementation_groups", "risk_matrix", "mappings", "answers"
    }

    for _, row in library_content.iterrows():
        key = str(row.iloc[0]).strip().lower()
        val1 = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else None
        val2 = str(row.iloc[2]).strip() if len(row) > 2 and not pd.isna(row.iloc[2]) else None
        val3 = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else None

        if key.startswith("library_"):
            library_meta.append((key.replace("library_", ""), val1))

        elif key == "tab":
            if val2 == "requirements":
                normalized_type = "framework"
            elif val2 == "mappings":
                normalized_type = "mapping_set"
            tab_entries.append((val1, normalized_type, val3))
            declared_tabs[normalized_type] = val1

        elif key in {"reference_control_base_urn", "threat_base_urn"} and val1:
            object_type = "reference_control" if "reference_control" in key else "threat"

            # Inject into <object>_meta
            object_metadata.setdefault(object_type, {})["base_urn"] = val1

            # If a prefix is defined in column 3, also store it in urn_prefixes
            if val2:
                urn_prefixes[val2] = val1

        else:
            for obj_type in known_object_types:
                if key.startswith(f"{obj_type}_"):
                    field = key[len(obj_type)+1:]
                    object_metadata.setdefault(obj_type, {})[field] = val1

    sheets_out = {
        "library_meta": pd.DataFrame(library_meta, columns=["key", "value"])
    }

    used_tabs = set()

    for tab_name, obj_type, base_urn in tab_entries:
        tab_name = tab_name.strip()
        obj_type = obj_type.strip()
        used_tabs.add(tab_name)

        meta_rows = [("type", obj_type)]
        if base_urn:
            meta_rows.append(("base_urn", base_urn))

        clean_type = obj_type.rstrip("s")
        for k, v in object_metadata.get(clean_type, {}).items():
            meta_rows.append((k, v))

        content_df = xls.get(tab_name, pd.DataFrame())

        if obj_type == "framework":
            if "scores" in declared_tabs:
                meta_rows.append(("score", "default"))
            if "implementation_groups" in declared_tabs:
                meta_rows.append(("implementation_groups", "baseline_ig"))
            if "answers" in declared_tabs:
                meta_rows.append(("answers", "default_answers"))

        sheets_out[f"{tab_name}_meta"] = pd.DataFrame(meta_rows, columns=["key", "value"])
        sheets_out[f"{tab_name}_content"] = content_df

    if urn_prefixes:
        sheets_out["urn_prefix_meta"] = pd.DataFrame([("type", "urn_prefix")], columns=["key", "value"])
        sheets_out["urn_prefix_content"] = pd.DataFrame(
            [{"prefix_id": k, "prefix_value": v} for k, v in urn_prefixes.items()]
        )

    for sheet in xls:
        if sheet not in {"library_content"} and sheet not in sheets_out and sheet not in used_tabs:
            sheets_out[sheet] = xls[sheet]

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for name, df in sheets_out.items():
            is_meta = name.endswith("_meta")
            df.to_excel(writer, sheet_name=name, index=False, header=not is_meta)

    print(f"✅ Conversion complete: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Convert Excel library v1 to v2 format.")
    parser.add_argument("input_file", type=str, help="Path to the v1 Excel file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    output_path = input_path.with_name(f"{input_path.stem}_new.xlsx")
    convert_v1_to_v2(str(input_path), str(output_path))

if __name__ == "__main__":
    main()
