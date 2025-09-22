import pandas as pd

# Load the relevant sheet, skipping the first 2 rows
df = pd.read_excel("csf2.xlsx", sheet_name="CSF 2.0", skiprows=2, header=None)

# Initialize the list of associations NIST CSF 2.0 -> ISO/IEC 27001:2022
associations = []

for index, row in df.iterrows():
    category_cell = row[2]  # Column C (index 2)
    mapping_cell = row[4]    # Column E (index 4)

    if pd.isna(category_cell) or pd.isna(mapping_cell):
        continue

    # Extract the NIST CSF 2.0 category (before the ":")
    if ':' not in str(category_cell):
        continue
    category_nist = str(category_cell).split(":")[0].strip().lower()

    for line in str(mapping_cell).split("\n"):
        line = line.strip()
        prefix = "ISO/IEC 27001:2022:"
        if line.startswith(prefix):
            content = line[len(prefix):].strip()

            if content.startswith("Mandatory Clause:"):
                clause = content[len("Mandatory Clause:"):].strip().lower()
                if clause != "none":
                    associations.append((category_nist, clause))

            elif content.startswith("Annex A Controls:"):
                control = content[len("Annex A Controls:"):].strip().lower()
                if control != "none":
                    associations.append((category_nist, f"a.{control}"))

# Create the final DataFrame
result_df = pd.DataFrame(associations, columns=["NIST CSF 2.0 Category", "ISO/IEC 27001:2022"])

# Save to a new Excel file
result_df.to_excel("nist_to_iso27001.xlsx", index=False)
