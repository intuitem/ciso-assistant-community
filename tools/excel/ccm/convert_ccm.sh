#!/usr/bin/env bash
if [ -z "$1" ]
  then
    echo "Usage: convert_ccm.sh ccm_file.xlsx"
    exit 1
fi

packager="personal"
python convert_ccm.py $1 $packager
python ../convert_library.py ccm-controls-v4.xlsx
echo "Resulting file is available as ccm-controls-v4.yaml"
