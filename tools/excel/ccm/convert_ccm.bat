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
@echo
echo ==^> [STEP 1] Extract Excel file data...
call python ../../../backend/scripts/convert_ccm_v2.py %1 -p %2
if %errorlevel% neq 0 (
    echo ==^> [ERROR] Step 1 failed
    exit /b 1
)
echo.
echo ==^> [STEP 2] Convert Excel v2 file to YAML...
call python ../../../backend/scripts/convert_library_v2.py ccm-controls-v4-v2.xlsx
if %errorlevel% neq 0 (
    echo ==^> [ERROR] Step 2 failed
    exit /b 1
)
echo.
echo ==^> [OK] Resulting file is available at ccm-controls-v4-v2.yaml
