# Library workbench

The convert-framework.py script can be used to transform an Excel file to a CISO Assistant library.

Have a look to the given examples.

## Usage

To launch it, open a shell in a command line, and type:

```bash
python convert-framework.py your_library_file.xlsx
```

This will produce a file name your_library_file.yaml

## Format of Excel files

```
Conventions:
    | means a cell separation, <> means empty cell
    The first tab shall be named "library_content" and contain the description of the library in the other tabs
        library_urn                 | <urn>
        library_version             | <version>
        library_locale              | <en/fr/...>
        library_ref_id              | <ref_id>
        library_name                | <name>
        library_description         | <description>
        library_copyright           | <copyright>
        library_provider            | <provider>
        library_packager            | <packager>
        library_dependencies        | <urn1, urn2...
        framework_urn               | <urn>
        framework_ref_id            | <ref_id>
        framework_name              | <name>
        framework_description       | <description>
        reference_control_base_urn  | <base_urn>            | id
        threat_base_urn             | <base_urn>            | id
        tab                         | <tab_name>            | requirements       | <section_name>
        tab                         | <tab_name>            | threats            | <base_urn>
        tab                         | <tab_name>            | reference_controls | <base_urn>


    For requirements:
        If no section_name is given, no upper group is defined, else an upper group (depth 0) with the section name is used.
        The first line is a header, with the following possible fields (* for required):
            - assessable(*): non-empty (e.g x) if this is a requirement
            - depth(*): 1/2/3/... to describe the tree
            - ref_id
            - name
            - description
            - maturity
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
```

## Caveats

Currently, the name of the Excel file shall be consistent with the library URN. For example, if the URN is urn:intuitem:risk:library:dfs-500-2023-11, then the filename shall be dfs-500-2023-11.xlsx.

If this rule is not followed, then importing a library will fail with no clear message, and displaying the library will fail with a "undefined" error. This will be fixed in a future version.
