file="CIS_Controls_Version_8.xlsx"
packager="personal"
python cis/prep_cis.py $file $packager
intermediate="cis-controls-v8.xlsx"
python convert_library.py cis/cis-controls-v8.xlsx
echo "Resulting file is available at cis/cis-controls-v8.yaml"