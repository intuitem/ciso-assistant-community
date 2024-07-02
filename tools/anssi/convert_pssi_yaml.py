# Convert ANSSI PDF reference document to the ciso-assistant yaml for libraries
#
# This script needs pypdf to open and parse the source file

from pypdf import PdfReader
import yaml
import re

destfile = "../../backend/library/libraries/anssi-pssi.yaml"

base_urn = "urn:deepthoughtsolutions:risk"
library_name = "anssi_pssi_2004"
YAML_BASE = f"""---
urn: {base_urn}:library:{library_name}
locale: fr
ref_id: ANSSI-PSSI-2004
name: "ANSSI - Principes de la PSSI 2004"
description: ""
copyright: Licence ouverte / Open Licence v2.0 (Etalab)
version: 1
provider: ANSSI
packager: deepthoughtsolutions
objects:
  framework:
    urn: {base_urn}:framework:{library_name}
    ref_id: ANSSI-PSSI-2004
    name: "ANSSI - Principes de la PSSI 2004"
    description: ""
    implementation_groups_definition: []
    requirement_nodes: []
"""
library = yaml.load(YAML_BASE, yaml.loader.UnsafeLoader)
library[
    "description"
] = """PSSI — Guide d’élaboration de politiques de sécurité des systèmes d’information

Extraction des principes de securité du PSSI

- https://cyber.gouv.fr/publications/pssi-guide-delaboration-de-politiques-de-securite-des-systemes-dinformation

Packagé par Deepthought Solutions (http://deepthought-solutions.com/) pour ciso-assistant
Auteur: Nicolas Karageuzian
"""

sections = []
# structured = {}

reader = PdfReader("PSSI-2004.pdf")


def parse_outline(outline, level):
    if isinstance(outline, list):
        level = level + 1
        for ol in outline:
            parse_outline(ol, level)
    else:
        # re.sub here beacause of 2 labels with inconsistent char in title
        # for matching in the text later
        sections.append(f"{re.sub("€", " ", outline.title.strip())}")


for outline in reader.outline:
    parse_outline(outline, 0)

# Grab all the text from the source PDF
text = ""
for page in reader.pages:
    text += page.extract_text()
# proper line ending replacement
text = re.sub(" *\n *", " ", text)
# strip off page heading and footer
text = re.sub(
    "SGDN / DCSSI / SDO / BCS  PSSI – Section 3 – Principes de sécurité – 3 mars 2004",
    "",
    text,
)
text = re.sub("Page [0-9]+ sur [0-9]+", "", text)
# Remove TOC from text
# print(text)
text = text.split("52  SECTION 4 – RÉFÉRENCES SSI (document séparé)")[1]


def parse_description(index, section):
    """
    Extract from the document all the text between the title of
    the desired section until the title of the next section
    """

    crop_before = re.split(section, text)
    if len(crop_before) > 1:
        cropped = re.split(sections[index + 1], crop_before[1])[0]
        cropped = re.sub(" *- ", "\n - ", cropped)

        cropped = re.sub("\. ([A-Z])", ".\n\\1", cropped)
        if (len(cropped)) > 1:
            return cropped
        return ""


for index, section in enumerate(sections):
    requirement = {}
    if section == "Introduction":
        library["objects"]["framework"]["description"] = parse_description(
            index, section
        )
    pattern_section = re.compile(
        "(?P<section>[A-Z]{3})(?P<subsection>-[0-9]{2})? : (?P<title>.*)"
    )
    section_desc = re.match(pattern_section, section)
    if section_desc:
        requirement["ref_id"] = section.split(":")[0].strip()
        requirement["urn"] = (
            f'{base_urn}:req_node:{library_name}:{requirement['ref_id'].lower()}'
        )
        requirement["name"] = section_desc.group("title")
        if section_desc.group("subsection") is not None:
            requirement["parent_urn"] = (
                f'{base_urn}:req_node:{library_name}:{requirement['ref_id'].split('-')[0].strip().lower()}'
            )
            requirement["depth"] = 2
            requirement["assessable"] = True
        else:
            requirement["depth"] = 1
            requirement["assessable"] = False

        requirement["description"] = parse_description(index, section)
        library["objects"]["framework"]["requirement_nodes"].append(requirement)

f = open(destfile, "w")
yaml.dump(library, f, sort_keys=False, default_flow_style=False)
f.close()
