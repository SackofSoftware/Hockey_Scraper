@echo off
:: Hockey Stats Auto-Update Script
:: Runs on Windows PC, updates databases in Dropbox folder

cd /d "%~dp0.."

echo ==========================================
echo Hockey Stats Update - %date% %time%
echo ==========================================

:: Update Bay State League
echo.
echo Updating Bay State Hockey League...
python smart_updater.py --league baystate
if errorlevel 1 (
    echo ERROR: Bay State update failed
) else (
    echo SUCCESS: Bay State updated
)

:: Update Eastern Hockey Federation
echo.
echo Updating Eastern Hockey Federation...
python smart_updater.py --league ehf
if errorlevel 1 (
    echo ERROR: EHF update failed
) else (
    echo SUCCESS: EHF updated
)

echo.
echo ==========================================
echo Update Complete - %date% %time%
echo ==========================================
echo.

:: Log to file
echo %date% %time% - Update completed >> update_log.txt
