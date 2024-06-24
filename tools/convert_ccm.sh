file="CCMv4.0.12.xlsx"
packager="personal"
python ccm/convert_ccm.py $file $packager
intermediate="ccm-controls-v4.xlsx"
python convert_library.py $intermediate
echo "Resulting file is available at cis/cis-controls-v8.yaml"
