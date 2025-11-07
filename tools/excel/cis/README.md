This script prepares the file to be parsed by the converter:

- Copy the downloaded Excel file from the [CIS website](https://www.cisecurity.org/controls) next to this script (for instance `CIS_Controls_Version_8.xlsx`)
- Run `pip install -r requirements.txt`
- Run the preparation script by passing the filename as 1st argument and your name/entity as a second one for the packager (e.g. `./convert_cis.sh ./cis_v8.xlsx intuitem`). Use `convert_cis.bat` if you're on Windows, or `convert_cis.sh` if you're on Linux/Mac.
- Use the resulting YAML in CISO Assistant
