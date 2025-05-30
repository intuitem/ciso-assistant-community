# d3fend library generator for CISO Assistant

import csv
from openpyxl import Workbook

tactic_to_csf_funtion = {
    "Model": "identify",
    "Harden": "protect",
    "Detect": "detect",
    "Isolate": "protect",
    "Deceive": "protect",
    "Evict": "respond",
}

output_file_name = "d3fend.xlsx"

library_description = """A cybersecurity ontology designed to standardize vocabulary for employing techniques to counter malicious cyber threats.
Version - 1.0.0 - 2024-12-20
https://d3fend.mitre.org/resources/"""

library_copyright = """Terms of Use
LICENSE
The MITRE Corporation (MITRE) hereby grants you a non-exclusive, royalty-free license to use D3FEND for research, development, and commercial purposes. Any copy you make for such purposes is authorized provided that you reproduce MITRE’s copyright designation and this license in any such copy.
DISCLAIMERS
ALL DOCUMENTS AND THE INFORMATION CONTAINED THEREIN ARE PROVIDED ON AN "AS IS" BASIS AND THE CONTRIBUTOR, THE ORGANIZATION HE/SHE REPRESENTS OR IS SPONSORED BY (IF ANY), THE MITRE CORPORATION, ITS BOARD OF TRUSTEES, OFFICERS, AGENTS, AND EMPLOYEES, DISCLAIM ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION THEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.
"""

packager = "intuitem"


with open("d3fend.csv", newline="") as csvfile:
    reader = csv.reader(csvfile, delimiter=",")

    n = 0
    current_technique = ""
    current_technique_l1 = ""

    wb_output = Workbook()
    ws = wb_output.active
    print("generating", output_file_name)
    ws.title = "library_content"
    ws.append(["library_urn", f"urn:{packager.lower()}:risk:library:mitre-d3fend"])
    ws.append(["library_version", 1])
    ws.append(["library_locale", "en"])
    ws.append(["library_publication_date", "2025-01-22"])
    ws.append(["library_ref_id", "d3fend"])
    ws.append(["library_name", "Mitre D3FEND"])
    ws.append(["library_description", library_description])
    ws.append(["library_copyright", library_copyright])
    ws.append(["library_provider", "Mitre D3FEND"])
    ws.append(["library_packager", packager])
    ws.append(["tab", "controls", "reference_controls"])
    ws.append(
        [
            "reference_control_base_urn",
            "urn:intuitem:risk:reference-controls:mitre-d3fend",
        ]
    )
    ws1 = wb_output.create_sheet("controls")
    ws1.append(("ref_id", "name", "description", "category", "csf_function"))

    for row in reader:
        n += 1
        if n == 1:
            header = row
        else:
            id, tactic, technique, technique_l1, technique_l2, definition = row
            if technique:
                current_technique = technique
                continue
            if technique_l1:
                current_technique_l1 = technique_l1
                ref_id = id
                name = current_technique_l1
                description = f"tactic: {tactic}\ntechnique level 1: {current_technique_l1}\ndefinition: {definition}"
            if technique_l2:
                ref_id = id
                name = technique_l2
                description = f"tactic: {tactic}\ntechnique level 1: {current_technique_l1}\ntechnique level 2: {technique_l2}\ndefinition: {definition}"
            ws1.append(
                (ref_id, name, description, "technical", tactic_to_csf_funtion[tactic])
            )

    wb_output.save(output_file_name)
