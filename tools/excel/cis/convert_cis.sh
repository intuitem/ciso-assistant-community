#!/usr/bin/env bash
if [ -z "$1" ]
then
    echo "Usage: convert_cis.sh cis_file.xlsx"
    exit 1
fi

packager="personal"

echo "➡️ [STEP 1] Extract Excel file data..."
python prep_cis.py $1 $packager
echo "➡️ [STEP 2] Convert extracted Excel file to v2..."
python ../../convert_v1_to_v2.py cis-controls-v8.xlsx
echo "➡️ [STEP 3] Convert Excel v2 file to YAML..."
python ../../convert_library_v2.py cis-controls-v8_new.xlsx
echo "✅ Resulting file is available at cis-controls-v8_new.yaml"