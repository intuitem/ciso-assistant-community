# Library workbench

The `example_framework.xlsx` file will help you understand the structure of a framework. 

The `prepare_framework_v2.py` script can be used to create an Excel file with the base structure of a CISO Assistant framework in v2 format.

The `convert_library_v2.py` script can be used to transform an Excel file to a CISO Assistant library.

The `convert_library_v1.py` script is the previous version working on the previous Excel file format.

The `convert_v1_to_v2.py` script converts any old Excel file to the new v2 format.

Have a look at the provided examples.

## Example framework

The structure of an Excel framework file may not be very easy to understand at first glance. That's why `example_framework.xlsx` has been created to help you understand the structure of a framework.

The sheets and cells are colored to make it easier to understand the structure of the file, and notes have also been added to some cells. If a cell has a note, you will find a colored triangle at the top right of the cell (red in Excel, brown in LibreOffice). Hover your mouse over the cell with this triangle to see the note.

This file can be converted with `convert_library_v2.py` and imported into CISO Assistant to see how it looks.

Before opening a support ticket concerning the creation of a framework, we recommend to take a look at the example framework.

You can also check the ["Format of Excel files"](#format-of-excel-files) section while viewing the example file to better understand the structure.

## Use of scripts

### > `prepare_framework_v2.py`

> [!NOTE]
> The purpose of this script is to help create the base structure of the Excel file. This avoids common mistakes that can be made when creating a framework.  

Usage (simplified):
```bash
python prepare_framework_v2.py
```

Usage (advanced):
```bash
python prepare_framework_v2.py [-i|--input input.yaml|input.xlsx] [-o|--output output.xlsx]
```

Arguments:
- **`-i, --input`**: Path to the input configuration file. Can be either a YAML (`.yaml`/`.yml`) or Excel (`.xlsx`) file. Default is `prepare_framework_v2_config.xlsx`.
- **`-o, --output`**: Optional output Excel file name. If not specified, the output file name will be derived automatically.


If we simply launch the script like this in a command line shell:

```bash
python prepare_framework_v2.py
```
the script will use an Excel configuration file called `prepare_framework_v2_config.xlsx` by default. This file contains its own documentation. Changes can be made directly in this file, avoiding you from adding arguments when you launch the script.

For advanced users, you can use the YAML configuration file instead, called `prepare_framework_v2_config.yaml`. This file contains its own documentation. Changes can be made directly in this file. To launch the script with a YAML configuration file, open a shell in a command line, and type:
```bash
python prepare_framework_v2.py -i prepare_framework_v2_config.yaml
```

> [!NOTE]
> After using this script, the `library_meta` sheet and the `_meta` sheet of type `framework` in the output Excel file will most likely not need to be modified (unless you want to add an additional language for a specific field).

> [!TIP]
> See ["Format of Excel files"](#format-of-excel-files) for a better understanding of Excel and YAML configuration file values.


### > `convert_library_v2.py`

Usage (simplified): 
```bash
python convert_library_v2.py your_library_file.xlsx [--verbose]
```

Usage (advanced):
```bash
python convert_library_v2.py your_library_file.xlsx [--compat MODE] [--output out.yaml] [--verbose]
python convert_library_v2.py path/to/folder_with_libraries --bulk [--compat MODE] [--output-dir out_folder] [--verbose]
```

Arguments:
- **`--compat`**: Specify compatibility mode number.
  - **`0`**: **[DEFAULT]** Don't use any Compatibility Mode.
  - **`1`**: Use legacy URN fallback logic (for requirements without `ref_id`). Recommended only to maintain libraries that have been generated prior or up to release `v1.9.20`.
  - **`2`**: Don't clean the URNs before saving it into the YAML file (Only spaces "` `" are replaced with hyphen "`-`" and the URN is lower-cased).
- **`--verbose`**: Enable verbose output. Verbose messages start with a 💬 (speech bubble) emoji.
- **`--output`**: Custom output file name (only for single file mode). Adds yaml' if missing.
- **`--bulk`**: Enable bulk mode to process all `.xlsx` files in a directory.
- **`--output-dir`**: Destination directory for YAML files (only valid with `--bulk`).


To launch it, open a shell in a command line, and type:

```bash
python convert_library_v2.py your_library_file.xlsx
```

`your_library_file.yaml` will be generated in the same directory. In most cases, this command line will suffice.

The resulting YAML file adheres to the CISO Assistant schema and can be directly imported into the platform.

When the `--compat` flag is omitted or when the compatibility mode is different from `1`, URNs for nodes without a `ref_id` are constructed using the `parent_urn`. This format is simpler to understand and maintain compared to the legacy `nodeXXX` suffix system.


### > `convert_library_v1.py`

> [!WARNING]
> The `v1` format is deprecated. We strongly recommend updating your Excel file in `v2` format with [`convert_v1_to_v2.py`](#-convert_v1_to_v2py).

Usage:
```bash
python convert_library_v1.py [--compat] your_library_file.xlsx
```

To launch it, open a shell in a command line, and type:

```bash
python convert_library_v1.py your_library_file.xlsx
```

This will produce a file named `your_library_file.yaml`.

The `--compat` flag is recommended only to maintain libraries that have been generated prior or up to release `1.9.20`. Without the compat flag, URNs generated for nodes without `ref_id` are constructed using the `parent_urn`. These generated URNs are much simpler to understand and maintain if required, compared to the previous system using `nodeXXX` suffix.


### > `convert_v1_to_v2.py`

Usage:
```bash
python convert_v1_to_v2.py your_v1_library_file.xlsx
```

To launch it, open a shell in a command line, and type:

```bash
python convert_v1_to_v2.py your_v1_library_file.xlsx
```

This will produce a file named `your_v1_library_file_new.yaml`.

## About framework Updates

If you want to update a framework, don't forget to increment the version number in the `version` field of the `library_meta` sheet before converting it to YAML. Otherwise, if the version number of the framework file is lower than or equal to the version number of the old version of your already imported framework in CISO Assistant, your framework will not be updated and CISO Assistant will not suggest to update the framework in your loaded libraries.


## Format of Excel files

### Principles

The `v2` format is more rigorous and general than the legacy `v1` format. Here are the main principles:
- Tabs are either of type `_meta` or `_content`, based on suffix of the name of the tab.
- A `_meta` tab contains key/value pairs, without header.
- A `_meta` tab shall contain a key `type` with the following possible values:
  - library (reserved for `library_meta` tab).
  - framework
  - risk_matrix
  - threats
  - reference_controls
  - requirement_mapping_set
  - implementation_groups
  - scores
  - answers
  - urn_prefix
- A `_content tab` contains various columns, depending on the content, and has a header.
- The `library_meta` contains the description of the library. There is no corresponding `_content`.
- The content (objects) of the library is inferred from the combined content of all other `_meta` and `_content` tabs.
- A library can contain any number of any type of objects.
- `urn_prefix` objects are fusioned, so there must be no conflict between them. It is recommended to have only one.
- Variables can have a translation in the form `variable[locale]`, in `_meta` as well as in `_content` tabs.
- When referencing `threats` or `reference_controls`, a prefix from `urn_prefix` shall be used followed by a semicolon and the `ref_id` of the object. This provides the corresponding urn.

(*) denotes mandatory fields.
(+) denotes advanced user fields.

### library_meta

The `library_meta` contains the following keys:
- type (*): must be `library`
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

A `_meta` of type `framework` contains the following keys:
- type (*): must be `framework`
- urn (*)
- ref_id (*)
- name (*)
- description (*)
- base_urn (*)
- min_score
- max_score
- scores_definition: name of an `scores` object
- implementation_groups_definition: name of an `implementation_groups` object
- answers_definition: name of an `answers` object

The `_content` tab for a `framework` object contains the following columns:
- assessable (*)
- depth (*)
- implementation_groups: comma-separated list of reference to `implementation_groups`
- ref_id (*)
- name
- description
- threats: blank/comma/LF separated list of references to `threats`
- reference_controls: blank/comma/LF separated list of references to `reference` controls
- typical_evidence
- annotation
- questions: 1 or several (n) questions, separated by line breaks
- answer: 1 (same for all questions) or n (one answer per question) answers, separated by line breaks
- urn_id (+): this is reserved for specific compatibility issues to force the urn calculation
- skip_count (+): trick to fix a referential without changing the URNs (subtract `1` from the counter) [Works with Compatibility mode `1` in `convert_library_v2.py`]
- fix_count (+): negative or positive integer. Better version of `skip_count`  (adds the integer to the counter) [Works with Compatibility mode `3` in `convert_library_v2.py`]

### Risk matrices

A `_meta` of type `risk_matrix` contains the following keys:
- type (*): must be `risk_matrix`
- urn (*)
- ref_id (*)
- name (*)
- description (*)

The `_content` tab for a `risk_matrix` object contains the following columns:
- "type" (*): one of `probability`/`impact`/`risk`
- "id" (*): a number from 0 to n-1 (depending on the number of objects for a given type)
- "color" (*): empty cells with the desired color. Can be left with no fill
- "abbreviation" (*): the abbreviation for the object
- "name" (*)
- "description" (*)
- "grid"  (*): multiple adjacent columns, renamed `grid0`, `grid1`, `grid2` automatically, with specific colors. The colors shall be consistent with the color column.

The grid shall be aligned with the probability objects, the columns being the impact in order of `id`, and the content of each cell being the id of the risk.

This is a topological representation. The display on the screen (transposition, direction of axes) will be managed in the frontend, not in the data model.

### Threats

A `_meta` of type `threats` contains the following keys:
- type (*): must be `threats`
- base_urn (*)

The `_content` tab for a `threats` object contains the following columns:
- ref_id (*)
- name (*)
- description
- annotation

### Reference controls

A `_meta` of type `reference_controls` contains the following keys:
- type (*): must be `reference_controls`
- base_urn (*)

The `_content` tab for a `reference_controls` object contains the following columns:
- ref_id (*)
- name (*)
- description
- category: one among `policy`/`process`/`technical`/`physical`/`procedure`
- csf_function: one among `govern`/`identify`/`protect`/`detect`/`respond`/`recover`
- annotation

### Requirement mapping sets

A `_meta` of type `requirement_mapping_set` contains the following keys:
- type (*): must be `requirement_mapping_set`
- source_framework_urn (*)
- source_node_base_urn (*)
- target_framework_urn (*)
- target_node_base_urn (*)

The `_content` tab for a `requirement_mapping_set` object contains the following columns:
- source_node_id (*)
- target_node_id (*)
- relationship (*): one among `equal`/`subset`/`superset`/`intersect`
- rationale
- strength_of_relationship

### Implementation groups

A `_meta` of type `implementation_groups` contains the following keys:
- type (*): must be `implementation_groups`
- name (*): the name of the object, will be used in framework objects

The `_content` tab for a `implementation_groups` object contains the following columns:
- ref_id (*)
- name (*)
- description

### Scores

A `_meta` of type `scores` contains the following keys:
- type (*): must be `scores`
- name (*): the name of the object, will be used in framework objects

The `_content` tab for a `scores` object contains the following columns:
- score (*)
- name (*)
- description (*)
- description_doc

### Answers

A `_meta` of type "answers" contains the following keys:
- type (*): must be "answers"
- name (*): the name of the object, will be used in framework objects

The `_content` tab for a "answers" object contains the following columns:
- id (*)
- question_type (*): one among `unique_choice`/`multiple_choice`/`text`/`date`
- question_choices: necessary if "question_type" is `unique_choice` or `multiple_choice`

### URN prefixes

A `_meta` of type `urn_prefix` contains the following keys:
- type (*): must be `urn_prefix`
 
The `_content` tab for a `urn_prefix` object contains the following columns:
- prefix_id	(*)
- prefix_value (*)

## Mappings

The `prepare_mapping_v2.py` script can be used to create an Excel file based on two framework libraries in YAML.

Usage :
```bash
python prepare_mapping_v2.py source.yaml target.yaml
```

To launch it, open a shell in a command line, and type:
```bash
python prepare_mapping_v2.py source.yaml target.yaml
```


Once the Excel file is properly filled in, it can be processed by the `convert_library_v2.py` tool to get the resulting mapping library. This tool also automatically creates the reverse of a mapping inside the resulting YAML file.

> [!CAUTION]
> The `convert_library_v1.py` tool does not create the reverse of a mapping. 

## Considerations for URN selection

The recommended format for URNs is: `urn:<packager>:risk:<object>:<refid>`

Object can be:
- library
- framework
- threat
- reference_control
- matrix
- req_mapping_set
- req_node

For the selection of `refid`, here are a few considerations:
- It makes sense to have a version of the source document in `refid`.
- However, this version should be generic enough to allow library updates.
- For example, if the version is `v2.0.4`, it is probably wise to select `v2.0` or even `v2`. Thus if `v2.1.0` is published and it is possible to make a smooth upgrade from `v2.0.4`, the urn will remain meaningful.
