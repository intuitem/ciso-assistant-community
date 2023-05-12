import json
import csv

mylib = {}
with open('iso27001-fr.csv', 'r', encoding='utf8') as csvfile:
    reader = csv.reader(csvfile, delimiter=';', quotechar='"')
    mylib['name'] = "ISO27001:2013 - Annexe A"
    mylib['description'] = "Fonctions de sécurité depuis l'annexe A de l'ISO27001:2013"
    mylib["copyright"] = "©ISO/CEI 2013 – All rights reserved"
    mylib["locale"] = "fr"
    mylib["objects"] = []
    for (id, name, description) in reader:
        print(id, name, description)
        secfunc = {"type": "security_function", "fields": {
            "name": f"{id} - {name}", 
            "description": description + "\n", 
            "provider": "ISO 27001:2013"}}
        mylib["objects"].append(secfunc)
    with open("iso27001-fr.json", "w") as f:
        json.dump(mylib, f, indent=2)
