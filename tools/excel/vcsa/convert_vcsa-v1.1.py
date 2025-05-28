"""
Simple script to convert VCSA v1.1 excel in a CISO Assistant Excel file
Source:  https://enx.com/en-US/VCS/downloads/

Known issue : There might be a typo in the Official document because "3.1.i" appears
twice in the original Excel file, causing a bug when converting from Excel to YAML
due to the lack of uniqueness of the ref_id. Consider changing the name of the extra
"3.1.i" (more precisely "3.1.i-s") by renaming it "3.1.i-s_bis" manually after conversion 
"""


import pandas as pd
import re
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook

# Charger le fichier source
df = pd.read_excel("ENX_VCSA_1_1_EN.xlsx", sheet_name="Vehicle CyberSecurity", header=2)

# Fonction pour filtrer le texte non vide
def has_text(cell):
    return isinstance(cell, str) and cell.strip() != ""

# Construire les lignes pour la feuille vcsa
output_rows = []

for _, row in df.iterrows():
    vcs = str(row.get("VCS", "")).strip()
    control_question = str(row.get("Control question", "")).strip()
    objective = row.get("Objective", "")

    if re.fullmatch(r"\d+", vcs):
        output_rows.append({
            "assessable": "",
            "depth": 1,
            "ref_id": vcs,
            "name": control_question,
            "description": "",
            "implementation_groups": ""
        })

    elif re.fullmatch(r"\d+\.\d+", vcs):
        if has_text(objective):
            output_rows.append({
                "assessable": "",
                "depth": 2,
                "ref_id": vcs,
                "name": control_question,
                "description": str(objective).strip(),
                "implementation_groups": ""
            })

    elif re.fullmatch(r"\d+\.\d+\.[A-Za-z]", vcs):
        x_y_z = vcs

        # Requirements (must)
        must_text = row.get("Requirements (must)", "")
        if has_text(must_text):
            output_rows.append({
                "assessable": "x",
                "depth": 3,
                "ref_id": f"{x_y_z}-m",
                "name": "(must)",
                "description": must_text.strip(),
                "implementation_groups": "must"
            })

        # Requirements (should)
        should_text = row.get("Requirements (should)", "")
        if has_text(should_text):
            output_rows.append({
                "assessable": "x",
                "depth": 3,
                "ref_id": f"{x_y_z}-s",
                "name": "(should)",
                "description": should_text.strip(),
                "implementation_groups": "should"
            })

        # Further information
        further_info = row.get("Further information", "")
        if has_text(further_info):
            output_rows.append({
                "assessable": "",
                "depth": 3,
                "ref_id": f"{x_y_z}-fi",
                "name": "Further information",
                "description": further_info.strip(),
                "implementation_groups": "fi"
            })

        # Possible evidence
        possible_evidence = row.get("Possible evidence (not mandatory)", "")
        if has_text(possible_evidence):
            output_rows.append({
                "assessable": "",
                "depth": 3,
                "ref_id": f"{x_y_z}-pe",
                "name": "Possible evidence (not mandatory)",
                "description": possible_evidence.strip(),
                "implementation_groups": "pe"
            })

# Créer les DataFrames
vcsa_df = pd.DataFrame(output_rows, columns=[
    "assessable", "depth", "ref_id", "name", "description", "implementation_groups"
])

# Données de library_content
library_content = [
    ["library_urn", "urn:intuitem:risk:library:vcsa-v1.1"],
    ["library_version", "1"],
    ["library_locale", "en"],
    ["library_ref_id", "vcsa-v1.1"],
    ["library_name", "Vehicle CyberSecurity Audit (VCSA) v1.1"],
    ["library_description", """The VCSA serves as the basis for 
- a self assessment to determine the state of vehicle cybersecurity within the organization (e.g. company)
- audits performed by internal departments (e.g. Internal Audit, Quality Management, Information Security, Cybersecurity)
- an audit in accordance with ENX 3rd party audit management framework
Source: https://enx.com/en-US/VCS/downloads/
"""],
    ["library_copyright", """© 2023 ENX Association
Contact: vcs@enx.com +49 69 9866927-71
www.enx.com
This work has been licensed under the Creative Commons Attribution - NoDerivs 4.0 International Public License. In addition, You are granted the right to distribute derivatives under certain terms. The complete and valid text of the license is to be found in line 17ff.
"""],
    ["library_provider", "ENX"],
    ["library_packager", "intuitem"],
    ["framework_urn", "urn:intuitem:risk:framework:vcsa-v1.1"],
    ["framework_ref_id", "vcsa-v1.1"],
    ["framework_name", "Vehicle CyberSecurity Audit (VCSA) v1.1"],
    ["framework_description", """The VCSA serves as the basis for 
- a self assessment to determine the state of vehicle cybersecurity within the organization (e.g. company)
- audits performed by internal departments (e.g. Internal Audit, Quality Management, Information Security, Cybersecurity)
- an audit in accordance with ENX 3rd party audit management framework
Source: https://enx.com/en-US/VCS/downloads/
"""],
    ["tab", "vcsa", "requirements"],
    ["tab", "implementation_groups", "implementation_groups"]
]

# Données pour la feuille "implementation_groups"
implementation_df = pd.DataFrame([
    {
        "ref_id": "must",
        "name": "Requirements (must)",
        "description": "The requirements indicated in this column are strict requirements without any exemptions. They are defined abstractly enough to encompass all VCS supplier types"
    },
    {
        "ref_id": "should",
        "name": "Requirements (should)",
        "description": "The requirements indicated in this column are principally to be implemented by the organization. These requirements go into granular detail. However, for certain supplier types, there may be a valid justification for non-compliance with these requirements. In case of any deviation, its effects must be understood by the supplier organization and it must be plausibly justified"
    },
    {
        "ref_id": "fi",
        "name": "Further information",
        "description": ""
    },
    {
        "ref_id": "pe",
        "name": "Possible evidence (not mandatory)",
        "description": ""
    }
])

# Création du fichier Excel avec openpyxl
wb = Workbook()

# Feuille "library_content"
ws_library = wb.active
ws_library.title = "library_content"
for row in library_content:
    ws_library.append(row)

# Feuille "vcsa"
ws_vcsa = wb.create_sheet(title="vcsa")
for r in dataframe_to_rows(vcsa_df, index=False, header=True):
    ws_vcsa.append(r)

# Feuille "implementation_groups"
ws_impl = wb.create_sheet(title="implementation_groups")
for r in dataframe_to_rows(implementation_df, index=False, header=True):
    ws_impl.append(r)

# Enregistrement du fichier final
wb.save("vcsa-v1.1.xlsx")
print(f"✅ Conversion complete: \"vcsa-v1.1.xlsx\"")

