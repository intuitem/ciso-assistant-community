# Library workbench

The convert_library_v2.py script can be used to transform an Excel file to a CISO Assistant library.

The convert_library_v1.py script is the previous version working on the previous Excel file format.

The convert_v1_to_v2.py script converts any old Excel file to the new v2 format.

Have a look at the provided examples.

## Usage

Usage: python convert_library_v2.py [--compat] your_library_file.xlsx

To launch it, open a shell in a command line, and type:

```bash
python convert_library_v2.py your_library_file.xlsx
```

"your_library_file.yaml" will be generated in the same directory.

The resulting YAML file adheres to the CISO Assistant schema and can be directly imported into the platform.

The compat flag is recommended only to maintain libraries that have been generated prior or up to release 1.9.20. 

When the --compat flag is omitted, URNs for nodes without a ref_id are constructed using the parent_urn. This format is simpler to understand and maintain compared to the legacy "nodeXXX" suffix system.


## Format of Excel files

### Principles

The v2 format is more rigorous and general than the legacy v1 format. Here are the main principles:
- Tabs are either of type _meta or _content, based on suffix of the name of the tab.
- A _meta tab contains key/value pairs, without header.
- A _meta tab shall contain a key "type" with the following possible values:
  - library (reserved for library_meta tab).
  - framework
  - risk_matrix
  - threats
  - reference_controls
  - requirement_mapping_set
  - implementation_groups
  - scores
  - answers
  - urn_prefix
- A _content tab contains various columns, depending on the content, and has a header.
- The library_meta contains the description of the library. There is no corresponding _content.
- The content (objects) of the library is inferred from the combined content of all other _meta and _content tabs.
- A library can contain any number of any type of objects.
- urn_prefix objects are fusioned, so there must be no conflict between them. It is recommended to have only one.
- Variables can have a translation in the form "variable[locale]", in _meta as well as in _content tabs.
- When referencing threats or reference_controls, a prefix from urn_prefix shall be used followed by a semicolon and the ref_id of the object. This provides the corresponding urn.

(*) denotes mandatory fields.

### library_meta

The library_meta contains the following keys:
- type (*): must be "library"
- urn (*)
- version (*)
- locale (*)
- ref_id (*)
- name (*)
- description (*)
- copyright (*)
- provider (*)
- packager (*)
- dependencies: list of the urns of libraries referenced in this current one

### Frameworks

A _meta of type "framework" contains the following keys:
- type (*): must be "framework"
- urn (*)
- ref_id (*)
- name (*)
- description (*)
- base_urn (*)
- min_score
- max_score
- scores_definition: name of an "scores" object
- implementation_groups_definition: name of an "implementation_groups" object
- answers_definition: name of an "answers" object

The _content tab for a framework object contains the following columns:
- assessable (*)
- depth (*)
- implementation_groups
- ref_id (*)
- name
- description
- threats: blank/comma/LF separated list of references to threats
- reference_controls: blank/comma/LF separated list of references to reference controls
- typical_evidence
- annotation
- questions: 1 or several (n) questions
- answer: 1 (same for all questions) or n (one answer per question) answers
- urn_id: this is reserved for specific compatibility issues to force the urn calculation

### Risk matrices

A _meta of type "risk_matrix" contains the following keys:
- type (*): must be "risk_matrix"
- urn (*)
- ref_id (*)
- name (*)
- description (*)

The _content tab for a risk_matrix object contains the following columns:
- "type" (*): one of probability/impact/risk
- "id" (*): a number from 0 to n-1 (depending on the number of objects for a given type)
- "color" (*): empty cells with the desired color. Can be left with no fill
- "abbreviation" (*): the abbreviation for the object
- "name" (*)
- "description" (*)
- "grid"  (*): multiple adjacent columns, renamed grid0, grid1, grid2 automatically, with specific colors. The colors shall be consistent with the color column.

The grid shall be aligned with the probability objects, the columns being the impact in order of id, and the content of each cell being the id of the risk.

This is a topological representation. The display on the screen (transposition, direction of axes) will be managed in the frontend, not in the data model.

### Threats

A _meta of type "threats" contains the following keys:
- type (*): must be "threats"
- urn (*)
- ref_id (*)
- name (*)
- description (*)

The _content tab for a "threats" object contains the following columns:
- ref_id (*)
- name
- description
- annotation

### Reference controls

A _meta of type "reference_controls" contains the following keys:
- type (*): must be "reference_controls"
- urn (*)
- ref_id (*)
- name (*)
- description (*)

The _content tab for a "reference_controls" object contains the following columns:
- ref_id (*)
- name
- description
- category: one among policy/process/technical/physical
- csf_function: one among govern/identify/protect/detect/respond/recover
- annotation

### Requirement mapping sets

A _meta of type "requirement_mapping_set" contains the following keys:
- type (*): must be "requirement_mapping_set"
- source_framework_urn (*)
- source_node_base_urn (*)
- target_framework_base_urn (*)
- target_node_base_urn (*)

The _content tab for a "requirement_mapping_set" object contains the following columns:
- source_node_id (*)
- target_node_id (*)
- relationship (*): equal, subset, superset, intersect
- rationale
- strength_of_relationship

### Implementation groups

A _meta of type "implementation_groups" contains the following keys:
- type (*): must be "implementation_groups"
- name (*): the name of the object, will be used in framework objects

The _content tab for a "implementation_groups" object contains the following columns:
- ref_id
- name
- description

### Scores

A _meta of type "scores" contains the following keys:
- type (*): must be "scores"
- name (*): the name of the object, will be used in framework objects

The _content tab for a "scores" object contains the following columns:
- score (*)
- name (*)
- description (*)
- description_doc

### Answers

A _meta of type "answers" contains the following keys:
- type (*): must be "answers"
- name (*): the name of the object, will be used in framework objects

The _content tab for a "answers" object contains the following columns:
- id (*)
- question_type (*): one of "unique_choice", "multiple_choice", "text", "date"
- question_choices: necessary if question_type is "unique_choice" or "multiple_choice"

### URN prefixes

A _meta of type "urn_prefix" contains the following keys:
- type (*): must be "urn_prefix"
 
The _content tab for a "urn_prefix" object contains the following columns:
- prefix_id	(*)
- prefix_value (*)

## Mappings

The `prepare_mapping_v2.py` script can be used to create an Excel file based on two framework libraries in yaml. Once properly filled, this Excel file can be processed by the `convert_library_v2.py` tool to get the resulting mapping library.

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
