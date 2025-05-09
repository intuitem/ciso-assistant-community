# Library workbench

The convert-library.py script can be used to transform an Excel file to a CISO Assistant library.

Have a look to the given examples.

## Usage

Usage: python convert_library [--compat] your_library_file.xlsx

To launch it, open a shell in a command line, and type:

```bash
python convert_library.py your_library_file.xlsx
```

This will produce a file name your_library_file.yaml

The compat flag is recommended only to maintain libraries that have been generated prior or up to release 1.9.20. Without the compat flag, URNs generated for nodes without ref_id are constructed using the parent_urn. These generated URNs are much simpler to understand and maintain if required, compared to the previus system using "nodeXXX" suffix.

## Format of Excel files

```
Conventions:
    | means a cell separation, <> means empty cell
    The first tab shall be named "library_content" and contain the description of the library in the other tabs
        library_urn                     | <urn>
        library_version                 | <version>
        library_locale                  | <en/fr/...>
        library_ref_id                  | <ref_id>
        library_name                    | <name>
        library_description             | <description>
        library_copyright               | <copyright>
        library_provider                | <provider>
        library_packager                | <packager>
        library_dependencies            | <urn1, urn2...
        framework_urn                   | <urn>
        framework_ref_id                | <ref_id>
        framework_name                  | <name>
        framework_description           | <description>
        framework_min_score             | <min_score>
        framework_max_score             | <max_score>
        reference_control_base_urn      | <base_urn> | id
        threat_base_urn                 | <base_urn> | id
        risk_matrix_urn                 | <urn>
        risk_matrix_ref_id              | <ref_id>
        risk_matrix_name                | <name>
        risk_matrix_description         | <description>
        mapping_urn                     | <urn>
        mapping_ref_id                  | <ref_id>
        mapping_name                    | <name>
        mapping_description             | <description>
        mapping_source_framework_urn    | <urn>
        mapping_target_framework_urn    | <urn>
        mapping_source_node_base_urn    | <urn>
        mapping_target_node_base_urn    | <urn>
        tab                             | <tab_name> | requirements
        tab                             | <tab_name> | threats            | <base_urn>
        tab                             | <tab_name> | reference_controls | <base_urn>
        tab                             | <tab_name> | scores
        tab                             | <tab_name> | implementation_groups
        tab                             | <tab_name> | risk_matrix
        tab                             | <tab_name> | mappings
        tab                             | <tab_name> | answers

        variables can also have a translation in the form "variable[locale]"

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
            - typical_evidence
            - questions
            - answer
            - skip_count: trick for fixing a referential without changing the urns (advanced users)
        The normal tree order shall be respected
        If multiple threats or reference_control are given for a requirements, they shall be separated by blank or comma.
        They shall be prefixed by the id of the corresponding base_urn and a semicolumn.
    For reference controls:
        The first line is a header, with the following possible fields (* for required):
            - ref_id(*)
            - name
            - description
            - category (policy/process/technical/physical).
            - csf_function (govern/identify/protect/detect/respond/recover).
            - annotation
    For risk matrices:
        The first line is a header, with the following mandatory fields:
            - type: probability/impact/risk.
            - id: a number from 0 to n-1 (depending of the number of objects for a given type)
            - color: empty cells with the desired color. Can be left with no fill.
            - abbreviation: the abbreviation for the object
            - name: name of the object
            - description: description of the object
            - grid: several columns describing the matrix with colors. The colors shall be consistent with the color column.
        The grid shall be aligned with the probability objects, the columns being the impact in order of id, and the content of each cell being the id of the risk.
        This is a topological representation. The display on the screen (transposition, direction of axes) will be managed in the frontend, not in the data model.
    For mappings:
        The first line is a header, with the following possible fields (* for required):
            - source_node_id(*)
            - target_node_id(*)
            - relationship(*)
            - rationale
            - stregth_of_relationship
    For Answers:
        The first line is a header, with the following possible fields (* for required):
            - id(*)
            - type(*)
            - choices(*)
    A library has a single locale, which is the reference language. Translations are given in columns with header like "name[fr]"
    Dependencies are given as a comma or blank separated list of urns.

```

## Mappings

The `prepare_mapping.py` script can be used to create an Excel file based on two framework libraries in yaml. Once properly filled, this Excel file can be processed by the `convert_library.py` tool to get the resulting mapping library.

## Considerations for URN selection

The recommended format for URNs is: urn:\<packager\>:risk:\<object\>:\<refid\>

Object can be:
- library
- framework
- threat
- reference_control
- matrix
- req_mapping_set
- req_node

For the selection of refid, here are a few considerations:
- It makes sense to have a version of the source document in refid.
- However, this version should be generic enough to allow library updates.
- For example, if the version is v2.0.4, it is probably wise to select v2.0 or even v2. Thus if v2.1.0 is published and it is possible to make a smooth upgrade from v2.0.4, the urn will remain meaningful.
