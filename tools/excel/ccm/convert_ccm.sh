#!/usr/bin/env bash
if [[ -z "$1" || -z "$2" ]]
then
    echo "Usage: $0 ccm_file.xlsx <packager>"
    exit 1
fi

filenamev2=ccm-controls-v4-v2.xlsx
filenamev2_YAML=ccm-controls-v4-v2.yaml

echo "➡️ [STEP 1] Extract Excel file data..."
python3 convert_ccm_v2.py $1 -p $2 || { echo "❌ Step 1 failed"; exit 1; }
echo ""
echo "➡️ [STEP 2] Convert Excel v2 file to YAML..."
python3 ../../convert_library_v2.py $filenamev2 || { echo "❌ Step 2 failed"; exit 1; }
echo "✅ Resulting file is available at $filenamev2_YAML"
