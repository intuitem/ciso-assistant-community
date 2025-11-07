#!/usr/bin/env bash
if [[ -z "$1" || -z "$2" ]]
then
    echo "Usage: $0 ccm_file.xlsx <packager>"
    exit 1
fi

filenamev1=ccm-controls-v4.xlsx
filenamev2=ccm-controls-v4_new.xlsx
filenamev2_YAML=ccm-controls-v4_new.yaml

echo "➡️ [STEP 1] Extract Excel file data..."
python convert_ccm.py $1 $2 || { echo "❌ Step 1 failed"; exit 1; }
echo "➡️ [STEP 2] Convert extracted Excel file to v2..."
python ../../convert_v1_to_v2.py $filenamev1 || { echo "❌ Step 2 failed"; exit 1; }
echo "➡️ [STEP 3] Convert Excel v2 file to YAML..."
python ../../convert_library_v2.py $filenamev2 || { echo "❌ Step 3 failed"; exit 1; }
echo "✅ Resulting file is available at $filenamev2_YAML"
