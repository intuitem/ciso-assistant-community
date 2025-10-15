This script prepares the file to be parsed by the converter:

- Copy the downloaded excel sheet from CSA next to this script (for instance [CCMv4.x.x_Generated-at_202x-x-x.xlsx](https://cloudsecurityalliance.org/research/cloud-controls-matrix) ; You need to create a free account to download the framework)
- Run `pip install -r requirements.txt`
- Run the preparation script by passing the filename as 1st argument and your name/entity as a second one for the packager (e.g. `./convert_ccm.sh ./CCMv4.xlsx intuitem`). Use `./convert_ccm.bat` if you're on Windows, or `./convert_ccm.sh` is you're on Linux/Mac.
- Use the resulting YAML in CISO Assistant
