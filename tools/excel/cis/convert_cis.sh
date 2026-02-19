#!/usr/bin/env bash
if [[ -z "$1" || -z "$2" ]]
then
    echo "Usage: $0 cis_file.xlsx <packager>"
    exit 1
fi

echo "➡️ [STEP 1] Extract Excel file data..."
python3 prep_cis_v2.py $1 -p $2 || { echo "❌ Step 1 failed"; exit 1; }
echo ""
echo "➡️ [STEP 2] Convert Excel v2 file to YAML..."
python3 ../../convert_library_v2.py cis-controls-v8-v2.xlsx || { echo "❌ Step 2 failed"; exit 1; }
echo ""
echo "✅ Resulting file is available at cis-controls-v8-v2.yaml"