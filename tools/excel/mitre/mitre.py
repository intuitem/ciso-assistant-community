from mitreattack.stix20 import MitreAttackData
import json
from openpyxl import Workbook

MITRE_COPYRIGHT = """
Terms of Use
LICENSE
The MITRE Corporation (MITRE) hereby grants you a non-exclusive, royalty-free license to use ATT&CK® for research, development, and commercial purposes. Any copy you make for such purposes is authorized provided that you reproduce MITRE's copyright designation and this license in any such copy.
"© 2022 The MITRE Corporation. This work is reproduced and distributed with the permission of The MITRE Corporation."
DISCLAIMERS
MITRE does not claim ATT&CK enumerates all possibilities for the types of actions and behaviors documented as part of its adversary model and framework of techniques. Using the information contained within ATT&CK to address or cover full categories of techniques will not guarantee full defensive coverage as there may be undisclosed techniques or variations on existing techniques not documented by ATT&CK.
ALL DOCUMENTS AND THE INFORMATION CONTAINED THEREIN ARE PROVIDED ON AN "AS IS" BASIS AND THE CONTRIBUTOR, THE ORGANIZATION HE/SHE REPRESENTS OR IS SPONSORED BY (IF ANY), THE MITRE CORPORATION, ITS BOARD OF TRUSTEES, OFFICERS, AGENTS, AND EMPLOYEES, DISCLAIM ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION THEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.
"""


def main():
    mitre_attack_data = MitreAttackData("enterprise-attack.json")

    mitigations = mitre_attack_data.get_mitigations(remove_revoked_deprecated=True)
    print(f"Retrieved {len(mitigations)} ATT&CK mitigations.")
    wb = Workbook()
    ws = wb.active
    ws.append(["ref_id", "name", "category", "description"])
    for m in mitigations:
        ws.append(
            [
                m.external_references[0].external_id,
                m.name,
                "technical",
                m.description.strip(" \n") + "\n" + m.external_references[0].url,
            ]
        )
    wb.save("measures.xlsx")

    techniques = mitre_attack_data.get_techniques(remove_revoked_deprecated=True)
    print(f"Retrieved {len(techniques)} ATT&CK techniques.")
    main_techniques = [t for t in techniques if not t.x_mitre_is_subtechnique]
    wb = Workbook()
    ws = wb.active
    ws.append(["ref_id", "name", "description"])
    for t in techniques:
        ws.append(
            [
                t.external_references[0].external_id,
                t.name,
                t.description.strip(" \n") + "\n" + t.external_references[0].url,
            ]
        )
    wb.save("techniques.xlsx")


if __name__ == "__main__":
    main()
