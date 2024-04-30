"""
simple script to transform an Excel file to a yaml library for a CISO assistant framework
Conventions:
    | means a cell separation, <> means empty cell
    The first tab shall be named "library_content" and contain the description of the library in the other tabs
        library_urn                | <urn>
        library_version            | <version>
        library_locale             | <en/fr/...>
        library_ref_id             | <ref_id>
        library_name               | <name>
        library_description        | <description>
        library_copyright          | <copyright>
        library_provider           | <provider>
        library_packager           | <packager>
        library_dependencies       | <urn1, urn2...
        framework_urn              | <urn>
        framework_ref_id           | <ref_id>
        framework_name             | <name>
        framework_description      | <description>
        framework_min_score        | <min_score>
        framework_max_score        | <max_score>
        reference_control_base_urn | <base_urn> | id
        threat_base_urn            | <base_urn> | id
        tab                        | <tab_name> | requirements
        tab                        | <tab_name> | threats            | <base_urn>
        tab                        | <tab_name> | reference_controls | <base_urn>
        tab                        | <tab_name> | scores
        tab                        | <tab_name> | implementation_groups
        tab                        | <tab_name> | matrix

    For requirements:
        If no section_name is given, no upper group is defined, else an upper group (depth 0) with the section name is used.
        The first line is a header, with the following possible fields (* for required):
            - assessable(*): non-empty (e.g x) if this is a requirement
            - depth(*): 1/2/3/... to describe the tree
            - ref_id
            - name
            - description
            - implementation_groups
            - threats
            - reference_controls
            - annotation
        The normal tree order shall be respected
        If multiple threats or reference_control are given for a requirements, they shall be separated by blank or comma.
        They shall be prefixed by the id of the corresponding base_urn and a semicolumn.
    For reference controls:
        The first line is a header, with the following possible fields (* for required):
            - depth(*): 1/2/3/.. for requirement groups, empty for a requirement.
            - ref_id(*)
            - name
            - description
            - category (policy/process/techncial/physical).
            - annotation
    A library has a single locale. Translated libraries have the same urns, they are merged during import.
    Dependencies are given as a comma or blank separated list of urns.
"""

import openpyxl
import sys
import re
import yaml
from pprint import pprint
from collections import defaultdict

LIBRARY_VARS = (
    "library_urn",
    "library_version",
    "library_locale",
    "library_ref_id",
    "library_name",
    "library_description",
    "framework_urn",
    "framework_ref_id",
    "framework_name",
    "framework_description",
    "framework_min_score",
    "framework_max_score",
    "library_copyright",
    "library_provider",
    "library_packager",
    "reference_control_base_urn",
    "threat_base_urn",
    "library_dependencies",
    "tab",
)
library_vars = {}
library_vars_dict = defaultdict(dict)
library_vars_dict_reverse = defaultdict(dict)
library_vars_dict_arg = defaultdict(dict)
urn_unicity_checker = set()

if len(sys.argv) <= 1:
    print("missing input file parameter")
    exit()
input_file_name = sys.argv[1]
ref_name = re.sub(r"\.\w+$", "", input_file_name).lower()
output_file_name = ref_name + ".yaml"

print("parsing", input_file_name)

# Define variable to load the dataframe
dataframe = openpyxl.load_workbook(input_file_name)

requirement_nodes = []
reference_controls = []
threats = []
scores_definition = []
implementation_groups_definition = []


def error(message):
    print("Error:", message)
    exit(1)


def read_header(row):
    i = 0
    header = {}
    for v in row:
        v = str(v.value).lower()
        header[v] = i
        i += 1
    return header


for tab in dataframe:
    print("parsing tab", tab.title)
    title = tab.title
    if title.lower() == "library_content":
        print("...processing content")
        for row in tab:
            if any([r.value for r in row]):
                (v1, v2, v3) = (r.value for r in row[0:3])
                v4 = row[3].value if len(row) > 3 else None
                if v1 in LIBRARY_VARS:
                    library_vars[v1] = v2
                    library_vars_dict[v1][str(v2)] = v3
                    library_vars_dict_reverse[v1][str(v3)] = v2
                    library_vars_dict_arg[v1][v2] = v4
    elif title not in library_vars_dict["tab"]:
        print(f"Ignored tab: {title}")
    elif library_vars_dict["tab"][title] == "requirements":
        print("...processing requirements")
        root_nodes_urn = re.sub("framework", "req_node", library_vars["framework_urn"])
        current_node_urn = None
        current_depth = 0
        parent_urn = None
        parent_for_depth = {}
        section = library_vars_dict_arg["tab"][title]
        if section:
            section_id = section.lower().replace(" ", "-")
            current_node_urn = f"{root_nodes_urn}:{section_id}"
            parent_for_depth[1] = current_node_urn
            requirement_nodes.append(
                {"urn": current_node_urn, "name": section, "assessable": False}
            )
        is_header = True
        counter = 0
        for row in tab:
            counter += 1
            if is_header:
                header = read_header(row)
                is_header = False
                assert "assessable" in header
                assert "depth" in header
                assert "ref_id" in header
            elif any([c.value for c in row]):
                assessable = bool(row[header["assessable"]].value)
                depth = row[header["depth"]].value
                ref_id = (
                    str(row[header["ref_id"]].value).strip()
                    if row[header["ref_id"]].value
                    else None
                )
                name = row[header["name"]].value if "name" in header else None
                description = (
                    row[header["description"]].value
                    if "description" in header
                    else None
                )
                annotation = (
                    row[header["annotation"]].value if "annotation" in header else None
                )
                implementation_groups = (
                    row[header["implementation_groups"]].value
                    if "implementation_groups" in header
                    else None
                )
                ref_id_urn = (
                    ref_id.lower().replace(" ", "-") if ref_id else f"node{counter}"
                )
                urn = f"{root_nodes_urn}:{ref_id_urn}"
                if urn in urn_unicity_checker:
                    print("URN duplicate:", urn)
                    exit(1)
                urn_unicity_checker.add(urn)
                assert type(depth) == int, f"incorrect depth for {row}"
                if depth == current_depth + 1:
                    parent_for_depth[depth] = current_node_urn
                    parent_urn = parent_for_depth[depth]
                elif depth <= current_depth:
                    pass
                else:
                    error(f"wrong depth in requirement (tab {title}) {urn}")
                current_node_urn = urn
                parent_urn = parent_for_depth[depth]
                current_depth = depth
                req_node = {"urn": urn, "assessable": assessable, "depth": depth}
                if parent_urn:
                    req_node["parent_urn"] = parent_urn
                if ref_id:
                    req_node["ref_id"] = ref_id
                if name:
                    req_node["name"] = name
                if description:
                    req_node["description"] = description
                if annotation:
                    req_node["annotation"] = annotation
                if implementation_groups:
                    req_node["implementation_groups"] = implementation_groups.split(',')
                threats = row[header["threats"]].value if "threats" in header else None
                reference_controls = (
                    row[header["reference_controls"]].value
                    if "reference_controls" in header
                    else None
                )
                threat_urns = []
                function_urns = []
                if threats:
                    for element in re.split(r"[\s,]+", threats):
                        parts = re.split(r":", element)
                        prefix = parts.pop(0)
                        part_name = ":".join(parts)
                        urn_prefix = library_vars_dict_reverse[
                            "reference_control_base_urn"
                        ][prefix]
                        threat_urns.append(f"{urn_prefix}{part_name}")
                if reference_controls:
                    for element in re.split(r"[\s,]+", reference_controls):
                        parts = re.split(r":", element)
                        prefix = parts.pop(0)
                        part_name = ":".join(parts)
                        urn_prefix = library_vars_dict_reverse[
                            "reference_control_base_urn"
                        ][prefix]
                        function_urns.append(f"{urn_prefix}{part_name}")
                if threat_urns:
                    req_node["threats"] = threat_urns
                if function_urns:
                    req_node["reference_controls"] = function_urns
                requirement_nodes.append(req_node)
            else:
                pass
                # print("empty row")
    elif library_vars_dict["tab"][title] == "reference_controls":
        print("...processing reference controls")
        current_function = {}
        is_header = True
        reference_controls_base_urn = library_vars["reference_control_base_urn"]
        for row in tab:
            if is_header:
                header = read_header(row)
                is_header = False
                assert "ref_id" in header
            elif any([c.value for c in row]):
                ref_id = (
                    str(row[header["ref_id"]].value).strip()
                    if row[header["ref_id"]].value
                    else None
                )
                name = row[header["name"]].value if "name" in header else None
                description = (
                    row[header["description"]].value
                    if "description" in header
                    else None
                )
                category = (
                    row[header["category"]].value if "category" in header else None
                )
                annotation = (
                    row[header["annotation"]].value if "annotation" in header else None
                )
                ref_id_urn = ref_id.lower().replace(" ", "-")
                current_function = {}
                current_function["urn"] = f"{reference_controls_base_urn}:{ref_id_urn}"
                current_function["ref_id"] = ref_id
                if name:
                    current_function["name"] = name
                if category:
                    current_function["category"] = category
                if description:
                    current_function["description"] = description
                if annotation:
                    current_function["annotation"] = annotation
                reference_controls.append(current_function)
    elif library_vars_dict["tab"][title] == "threats":
        print("...processing threats")
        current_threat = {}
        is_header = True
        threat_base_urn = library_vars["threat_base_urn"]
        for row in tab:
            if is_header:
                header = read_header(row)
                print(header)
                is_header = False
                assert "ref_id" in header
            elif any([c.value for c in row]):
                ref_id = (
                    str(row[header["ref_id"]].value).strip()
                    if row[header["ref_id"]].value
                    else None
                )
                name = row[header["name"]].value if "name" in header else None
                description = (
                    row[header["description"]].value
                    if "description" in header
                    else None
                )
                annotation = (
                    row[header["annotation"]].value if "annotation" in header else None
                )
                ref_id_urn = ref_id.lower().replace(" ", "-")
                current_threat = {}
                current_threat["urn"] = f"{threat_base_urn}:{ref_id_urn}"
                current_threat["ref_id"] = ref_id
                if name:
                    current_threat["name"] = name
                if description:
                    current_threat["description"] = description
                if annotation:
                    current_threat["annotation"] = annotation
                threats.append(current_threat)
    elif library_vars_dict["tab"][title] == "scores":
        print("...processing scores")
        is_header = True
        for row in tab:
            if is_header:
                header = read_header(row)
                is_header = False
                assert "score" in header
                assert "name" in header
                assert "description" in header
            elif any([c.value for c in row]):
                score = row[header["score"]].value
                name = row[header["name"]].value
                description = row[header["description"]].value
                scores_definition.append(
                    {"score": score, "name": name, "description": description}
                )
    elif library_vars_dict["tab"][title] == "implementation_groups":
        print("...processing implementation groups")
        is_header = True
        for row in tab:
            if is_header:
                header = read_header(row)
                is_header = False
                assert "ref_id" in header
                assert "name" in header
                assert "description" in header
            elif any([c.value for c in row]):
                ref_id = row[header["ref_id"]].value
                name = row[header["name"]].value
                description = row[header["description"]].value
                implementation_groups_definition.append(
                    {"ref_id": ref_id, "name": name, "description": description}
                )


has_framework = "requirements" in [
    library_vars_dict["tab"][x] for x in library_vars_dict["tab"]
]
has_reference_controls = "reference_controls" in [
    library_vars_dict["tab"][x] for x in library_vars_dict["tab"]
]
has_threats = "threats" in [
    library_vars_dict["tab"][x] for x in library_vars_dict["tab"]
]

library = {
    "urn": library_vars["library_urn"],
    "locale": library_vars["library_locale"],
    "ref_id": library_vars["library_ref_id"],
    "name": library_vars["library_name"],
    "description": library_vars["library_description"],
    "copyright": library_vars["library_copyright"],
    "version": library_vars["library_version"],
    "provider": library_vars["library_provider"],
    "packager": library_vars["library_packager"],
}

if "library_dependencies" in library_vars:
    dependencies = [
        x for x in re.split(r"[\s,]+", library_vars["library_dependencies"])
    ]
    library["dependencies"] = dependencies

library["objects"] = {}

if has_framework:
    library["objects"]["framework"] = {
        "urn": library_vars["framework_urn"],
        "ref_id": library_vars["framework_ref_id"],
        "name": library_vars["framework_name"],
        "description": library_vars["framework_description"],
    }
    if "framework_min_score" in library_vars:
        library["objects"]["framework"]["min_score"] = library_vars["framework_min_score"]
    if "framework_max_score" in library_vars:
        library["objects"]["framework"]["max_score"] = library_vars["framework_max_score"]
    if scores_definition:
        library["objects"]["framework"]["scores_definition"] = scores_definition
    if implementation_groups_definition:
        library["objects"]["framework"]["implementation_groups_definition"] = implementation_groups_definition
    library["objects"]["framework"]["requirement_nodes"] = requirement_nodes

if has_reference_controls:
    library["objects"]["reference_controls"] = reference_controls

if has_threats:
    library["objects"]["threats"] = threats

print("generating", output_file_name)
with open(output_file_name, "w", encoding="utf8") as file:
    yaml.dump(library, file, sort_keys=False)
