#!/usr/bin/env bash
if [[ -z "$1" || -z "$2" ]]
then
    echo "Usage: $0 cis_file.xlsx <packager>"
    exit 1
fi

echo "➡️ [STEP 1] Extract Excel file data..."
python prep_cis.py $1 $2 || { echo "❌ Step 1 failed"; exit 1; }
echo "➡️ [STEP 2] Convert extracted Excel file to v2..."
python ../../convert_v1_to_v2.py cis-controls-v8.xlsx || { echo "❌ Step 2 failed"; exit 1; }
echo "➡️ [STEP 3] Convert Excel v2 file to YAML..."
python ../../convert_library_v2.py cis-controls-v8_new.xlsx || { echo "❌ Step 3 failed"; exit 1; }
echo "✅ Resulting file is available at cis-controls-v8_new.yaml"