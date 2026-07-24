@echo off
setlocal EnableDelayedExpansion
REM ============================================================================
REM  Groundwork deploy script.
REM
REM  Workflow:
REM    1. Put new files (from Claude session) into C:\Groundwork\staging\
REM    2. Close Groundwork completely
REM    3. Run this script
REM
REM  What it does:
REM    - Backs up every file it's about to replace
REM    - Routes each staged file to its correct destination
REM        (database.py -> core\  -- encoded so it can never go wrong again)
REM    - Runs smoke_test.py against the new code (isolated temp DB)
REM    - If the smoke test FAILS: restores the backup automatically
REM    - If it PASSES: commits to git (if git is set up)
REM ============================================================================

cd /d C:\Groundwork
set STAGING=C:\Groundwork\staging

if not exist "%STAGING%" (
    echo No staging folder found. Create C:\Groundwork\staging and put the
    echo new files in it, then run this again.
    exit /b 1
)

dir /b "%STAGING%" >nul 2>&1 || (
    echo Staging folder is empty - nothing to deploy.
    exit /b 1
)

REM ── Warn if Groundwork appears to be running ────────────────────────────────
tasklist /FI "IMAGENAME eq Groundwork.exe" 2>nul | find /i "Groundwork.exe" >nul
if not errorlevel 1 (
    echo.
    echo WARNING: Groundwork appears to be running. Close it first.
    echo Press Ctrl+C to abort, or
    pause
)

REM ── Backup ──────────────────────────────────────────────────────────────────
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set DT=%%I
set TS=%DT:~0,8%_%DT:~8,6%
set BACKUP=C:\Groundwork\backups\deploy_%TS%
mkdir "%BACKUP%" 2>nul
mkdir "%BACKUP%\core" 2>nul
mkdir "%BACKUP%\static\js" 2>nul

echo.
echo === Backing up current files to %BACKUP% ===
for %%F in ("%STAGING%\*") do call :backup_one "%%~nxF"

REM ── Route staged files to destinations ──────────────────────────────────────
echo.
echo === Deploying ===
set DEPLOY_FAILED=0
for %%F in ("%STAGING%\*") do call :route_one "%%~nxF" "%%F"
if %DEPLOY_FAILED%==1 (
    echo.
    echo Unknown file in staging - fix and re-run. Nothing was smoke-tested.
    exit /b 1
)

REM ── Smoke test gate ─────────────────────────────────────────────────────────
echo.
echo === Running smoke test ===
python smoke_test.py
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  SMOKE TEST FAILED - ROLLING BACK
    echo ============================================================
    xcopy /y /s "%BACKUP%\*" "C:\Groundwork\" >nul
    echo Previous version restored. The staged files are still in
    echo %STAGING% - send the smoke test output to your next session.
    exit /b 1
)

REM ── Success: clear staging, commit ──────────────────────────────────────────
del /q "%STAGING%\*" 2>nul
where git >nul 2>&1
if not errorlevel 1 (
    if exist ".git" (
        git add -A >nul 2>&1
        git commit -m "deploy %TS%" >nul 2>&1
        echo Committed to git as "deploy %TS%".
    )
)

echo.
echo ============================================================
echo  DEPLOYED AND VERIFIED. Start Groundwork.
echo ============================================================
exit /b 0

REM ── Subroutines ─────────────────────────────────────────────────────────────
:backup_one
set N=%~1
if /i "%N%"=="app.js"      copy /y "static\js\app.js" "%BACKUP%\static\js\" >nul 2>&1
if /i "%N%"=="index.html"  copy /y "static\index.html" "%BACKUP%\static\" >nul 2>&1
if /i "%N%"=="database.py" copy /y "core\database.py" "%BACKUP%\core\" >nul 2>&1
if /i "%N%"=="server.py"     copy /y "server.py"     "%BACKUP%\" >nul 2>&1
if /i "%N%"=="launch.py"     copy /y "launch.py"     "%BACKUP%\" >nul 2>&1
if /i "%N%"=="migrate.py"    copy /y "migrate.py"    "%BACKUP%\" >nul 2>&1
if /i "%N%"=="smoke_test.py" copy /y "smoke_test.py" "%BACKUP%\" >nul 2>&1
if /i "%N%"=="bank_importer.py"  copy /y "bank_importer.py"  "%BACKUP%\" >nul 2>&1
if /i "%N%"=="quicken_import.py" copy /y "quicken_import.py" "%BACKUP%\" >nul 2>&1
goto :eof

:route_one
set N=%~1
set SRC=%~2
if /i "%N%"=="app.js"      ( copy /y "%SRC%" "static\js\app.js" >nul     & echo   app.js      -^> static\js\        & goto :eof )
if /i "%N%"=="index.html"  ( copy /y "%SRC%" "static\index.html" >nul    & echo   index.html  -^> static\           & goto :eof )
if /i "%N%"=="database.py" ( copy /y "%SRC%" "core\database.py" >nul     & echo   database.py -^> core\  [THE RULE]  & goto :eof )
if /i "%N%"=="server.py"     ( copy /y "%SRC%" "server.py" >nul     & echo   server.py   -^> root & goto :eof )
if /i "%N%"=="launch.py"     ( copy /y "%SRC%" "launch.py" >nul     & echo   launch.py   -^> root & goto :eof )
if /i "%N%"=="migrate.py"    ( copy /y "%SRC%" "migrate.py" >nul    & echo   migrate.py  -^> root & goto :eof )
if /i "%N%"=="smoke_test.py" ( copy /y "%SRC%" "smoke_test.py" >nul & echo   smoke_test  -^> root & goto :eof )
if /i "%N%"=="bank_importer.py"  ( copy /y "%SRC%" "bank_importer.py" >nul  & echo   bank_importer -^> root & goto :eof )
if /i "%N%"=="quicken_import.py" ( copy /y "%SRC%" "quicken_import.py" >nul & echo   quicken_import -^> root & goto :eof )
echo   UNKNOWN FILE: %N%  (no routing rule - add one to deploy.bat)
set DEPLOY_FAILED=1
goto :eof
