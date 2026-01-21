# > `convert_cis.sh (Linux / Mac) / convert_cis.bat (Windows)`

This script prepares the file to be parsed by the converter:

- Copy the downloaded Excel file from the [CIS website](https://www.cisecurity.org/controls) next to this script (for instance `CIS_Controls_Version_8.xlsx`)
- Run `pip install -r requirements.txt`
- Run the preparation script by passing the filename as 1st argument and your name/entity as a second one for the packager (e.g. `./convert_cis.sh ./cis_v8.xlsx intuitem`). Use `convert_cis.bat` if you're on Windows, or `convert_cis.sh` if you're on Linux/Mac.
- Use the resulting YAML in CISO Assistant

# > `prep_mapping_cis_controls_csf_2.0.py`


This script generates a structured mapping between **CIS Controls v8** and **NIST Cybersecurity Framework (CSF) 2.0**.

It performs two steps:
1. **Create an Excel mapping file** with three sheets:
   - `library_meta`
   - `mappings_meta`
   - `mappings_content` (source_node_id | target_node_id | relationship)
2. **Convert the Excel mapping into a YAML library** using the existing conversion tooling.


## Prerequisites

Before running this script, ensure that:

- The official **CIS Controls v8 mapping Excel file** (downloaded from the [CIS website](https://www.cisecurity.org/)) is copied **next to this script** or that its path is correctly referenced when running the command.
- All required Python dependencies are installed by running:

  ```bash
  pip install -r requirements.txt
  ```


## Usage

```bash
python prep_mapping_cis_controls_csf_2.0.py <input_excel_file> <packager_name>
```

- **`<input_excel_file>`**  
  Path to the official CIS Controls v8 mapping Excel file used as input.  
  This file contains the raw mapping data between CIS Controls and the target framework.

- **`<packager_name>`**  
  Identifier of the packager used in your **CIS Controls v8 framework YAML**.  
  ⚠️ This value **must be strictly identical** to the one defined in the CIS v8 YAML file (around line ~20), for example:

  ```yaml
  packager: <packager_name>
  ```

   Using the same packager name guarantees URN consistency between the CIS framework and the generated mapping libraries.


## Example

```bash
python prep_mapping_cis_controls_csf_2.0.py CIS_Controls_v8_Mapping_to_CSF_2.0.xlsx intuitem
```


---

# > `prep_mapping_cis_controls_iso_27.py`

This script generates a mapping between **CIS Controls v8** and **ISO/IEC 27001:2022**.

The **overall behavior is strictly identical** to the CSF version..


## Prerequisites

Before running this script, ensure that:

- The official **CIS Controls v8 mapping Excel file** (downloaded from the [CIS website](https://www.cisecurity.org/)) is copied **next to this script** or that its path is correctly referenced when running the command.
- All required Python dependencies are installed by running:

  ```bash
  pip install -r requirements.txt
  ```


## Usage

```bash
python prep_mapping_cis_controls_iso_27.py <input_excel_file> <packager_name>
```

- **`<input_excel_file>`**  
  Path to the official CIS Controls v8 mapping Excel file used as input.  
  This file contains the raw mapping data between CIS Controls and the target framework.

- **`<packager_name>`**  
  Identifier of the packager used in your **CIS Controls v8 framework YAML**.  
  ⚠️ This value **must be strictly identical** to the one defined in the CIS v8 YAML file (around line ~20), for example:

  ```yaml
  packager: <packager_name>
  ```

  Using the same packager name guarantees URN consistency between the CIS framework and the generated mapping libraries.


## Example

```bash
python prep_mapping_cis_controls_iso_27.py CIS_Controls_v8_NEW_MAPPING_to_ISO.IEC_27001.2022_2_2023.xlsx intuitem
```
