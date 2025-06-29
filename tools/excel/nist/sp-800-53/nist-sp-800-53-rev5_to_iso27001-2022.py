import pandas as pd
import re
import warnings

# Ignore warnings related to unsupported Excel features (like data validation)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# File paths
source_file = "sp800-53r5-to-iso-27001-mapping-2022-OLIR-2023-10-12-UPDATED.xlsx"
output_file = "part_nist-sp-800-53-rev5_to_iso27001-2022.xlsx"

# List to collect all cleaned data from all sheets
final_data = []

# Load the Excel workbook
excel_file = pd.ExcelFile(source_file)

# Loop through all sheets
for sheet_name in excel_file.sheet_names:
    df = excel_file.parse(sheet_name)

    # Ensure there are at least 4 columns to work with
    if df.shape[1] >= 4:
        # Extract column A (index 0) and column D (index 3)
        temp_df = df.iloc[:, [0, 3]]
        temp_df.columns = ['source_node_id', 'target_node_id']

        # Drop rows where target_node_id is missing
        temp_df = temp_df.dropna(subset=['target_node_id'])

        # Function to clean values from column A (source_node_id)
        def clean_source(value):
            if isinstance(value, str):
                value = value.strip().lower()                     # Lowercase and remove spaces
                value = re.sub(r'-(0)(\d)\b', r'-\2', value)      # Remove unnecessary leading zeros (e.g., PX-01 → PX-1)
                value = re.sub(r'\((0+)(\d+)\)', r'(\2)', value)  # (01) → (1), (003) → (3)
            return value

        # Function to clean values from column D (target_node_id)
        def clean_target(value):
            if isinstance(value, str):
                return value.strip().lower()                     # Lowercase and remove spaces
            return value

        # Apply cleaning functions
        temp_df['source_node_id'] = temp_df['source_node_id'].apply(clean_source)
        temp_df['target_node_id'] = temp_df['target_node_id'].apply(clean_target)

        # Remove unwanted rows based on specific values in source_node_id
        rows_to_exclude = ['relationship', 'rationale', 'sor']
        temp_df = temp_df[~temp_df['source_node_id'].isin(rows_to_exclude)]
        
        # Define content as text
        temp_df['target_node_id'] = temp_df['target_node_id'].astype(str)

        # Add cleaned sheet data to the final list
        final_data.append(temp_df)

# Concatenate data from all sheets
result_df = pd.concat(final_data, ignore_index=True)

# Export to a new Excel file
result_df.to_excel(output_file, index=False)

print(f"✅ Cleaned Excel file exported as: \"{output_file}\"")
