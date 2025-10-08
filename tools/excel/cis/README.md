This script prepares the file to be parsed by the converter:

- Copy the downloaded excel sheet from CIS next to this script (for instance [CIS_Controls_Version_8.xlsx](https://learn.cisecurity.org/cis-controls-download))
- Run `pip install -r requirements.txt`
- Run the preparation script by passing the filename as 1st argument and your name/entity as a second one for the packager (e.g. `./convert_cis.sh ./cis_v8.xlsx intuitem`)
- Use the resulting yaml in CISO Assistant
