#!/usr/bin/env bash
if [ -z "$1" ]
then
    echo "Usage: convert_cis.sh cis_file.xlsx"
    exit 1
fi
packager="personal"
python prep_cis.py $1 $packager
python ../convert_library.py cis-controls-v8.xlsx
echo "Resulting file is available at cis-controls-v8.yaml"