@echo off
REM Check if an argument is provided
IF "%~1"=="" (
    echo Usage: convert_ccm.bat ccm_file.xlsx ^<packager^>
    exit /b 1
)
IF "%~2"=="" (
    echo Usage: convert_ccm.bat ccm_file.xlsx ^<packager^>
    exit /b 1
)


REM Run the Python scripts
echo ==^> [STEP 1] Extract Excel file data...
call python convert_ccm.py %1 %2
if %errorlevel% neq 0 (
    echo ==^> [ERROR] Step 1 failed
    exit /b 1
)
echo ==^> [STEP 2] Convert extracted Excel file to v2...
call python ..\..\convert_v1_to_v2.py ccm-controls-v4.xlsx
if %errorlevel% neq 0 (
    echo ==^> [ERROR] Step 2 failed
    exit /b 1
)
echo ==^> [STEP 3] Convert Excel v2 file to YAML...
call python ..\..\convert_library_v2.py ccm-controls-v4_new.xlsx
if %errorlevel% neq 0 (
    echo ==^> [ERROR] Step 3 failed
    exit /b 1
)

echo ==^> [OK] Resulting file is available at ccm-controls-v4_new.yaml
