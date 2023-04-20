from mitreattack.stix20 import MitreAttackData
import json

def main():
    mitre_attack_data = MitreAttackData("enterprise-attack.json")

    mitigations = mitre_attack_data.get_mitigations(remove_revoked_deprecated=True)

    print(f"Retrieved {len(mitigations)} ATT&CK mitigations.")
    mylib = {}
    mylib['name'] = "MITRE ATT&CK 2.1 - Mitigations"
    mylib['description'] = "Mitigations from MITRE ATT&CK 2.1"
    mylib["format_version"] = "1.0"
    mylib["objects"] = []
    for m in mitigations:
        name = m.name
        id = m.external_references[0].external_id
        url = m.external_references[0].url
        description = m.description
        print(id, name)
        secfunc = {"type": "security_function", "fields": {
            "name": f"{id} - {name}", 
            "description": description + "\n" + url + "\n", 
            "provider": "Mitre Att&ck"}}
        mylib["objects"].append(secfunc)

    with open("mitre-mitigations.json", "w") as f:
        json.dump(mylib, f)

    techniques = mitre_attack_data.get_techniques(remove_revoked_deprecated=True)

    print(f"Retrieved {len(techniques)} ATT&CK techniques.")
    mylib = {}
    mylib['name'] = "MITRE ATT&CK 2.1 - Techniques"
    mylib['description'] = "Main techniques from MITRE ATT&CK 2.1"
    mylib["format_version"] = "1.0"
    mylib["objects"] = []
    main_techniques = [t for t in techniques if not t.x_mitre_is_subtechnique]
    print(len(main_techniques))
    for t in main_techniques:
        name = t.name
        id = t.external_references[0].external_id
        url = t.external_references[0].url
        description = t.description
        print(id, name)
        threat = {"type": "threat", "fields": {
            "name": f"{id} - {name}", 
            "description": description + "\n" + url + "\n",
            "provider": "Mitre Att&ck"}}
        mylib["objects"].append(threat)

    with open("mitre-techniques.json", "w") as f:
        json.dump(mylib, f)


if __name__ == "__main__":
    main()
