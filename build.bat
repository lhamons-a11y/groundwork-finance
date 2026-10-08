@echo off
title Groundwork - Build Installer
color 0A
echo.
echo ============================================
echo   Groundwork Installer Builder
echo ============================================
echo.

:: Build from the checkout this script is in (C:\Groundwork, or a worktree of
:: lts/1.x for a 1.1.x release). The .iss files use paths relative to this
:: folder, so the bundle, licence, icon and output all come from here.
cd /d "%~dp0"
echo       Building from: %CD%
echo.

:: -- Product line -------------------------------------------------------------
:: Which product is this build? "teaching" (GW 2.0, the default) or "lts" (1.x).
:: The spec reads GW_PRODUCT and strips static/js/teaching/ from an LTS bundle,
:: so an LTS build does not contain the teaching layer rather than disabling it.
::   build.bat        -> GW 2.0
::   build.bat lts    -> GW LTS
if /i "%~1"=="lts" (set GW_PRODUCT=lts) else (set GW_PRODUCT=teaching)
echo       Product line: %GW_PRODUCT%
echo.

:: -- Step 0: Preflight check - watchdog must be bundled --------------------
:: GROUNDWORK_STATUS.md flagged this as an open item: without watchdog
:: explicitly in the PyInstaller spec (as a hiddenimport or otherwise), the
:: Downloads auto-import watcher silently doesn't exist in the frozen
:: installer - no error, no warning, testers just never see the auto-import
:: banner and there's no way to tell from the outside that anything's wrong.
:: Regex requires "watchdog" to appear before any '#' on the line, so a
:: comment that only mentions watchdog does NOT satisfy this check.
echo [0/4] Checking that watchdog is bundled...
findstr /i /r "^[^#]*watchdog" groundwork.spec >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  WARNING: "watchdog" not found anywhere in groundwork.spec
    echo ============================================================
    echo  If watchdog isn't declared as a hidden import, the Downloads
    echo  auto-import watcher will be silently missing from this build.
    echo.
    echo  Press Ctrl+C to stop and fix groundwork.spec first, or
    pause
) else (
    echo       watchdog reference found in spec. OK.
)
echo.

:: -- Step 0b: the local AI model, the exact tested file -----------------------
:: Since item 31 (ENGINE_REPLACEMENT.md) every installer ships the model inside
:: Groundwork; there is no Ollama to download or bundle. The .iss files take it
:: from vendor\phi3.5_model\blobs\sha256-<pin>. It is git-ignored, so a fresh
:: worktree has no copy: set GW_MODEL_PATH to the pinned file (python
:: fetch_model.py downloads and verifies it) and it is linked in here.
:: The fingerprint check is mandatory (Rob, 2026-10-03): a wrong file stops the build.
echo [0b/4] Checking the local AI model...
for /f "usebackq delims=" %%H in (`python -c "import fetch_model as f; print(f.MODEL_SHA256)"`) do set MODEL_SHA=%%H
if "%MODEL_SHA%"=="" (
    echo ERROR: could not read the model pin from core\engine.py.
    pause
    exit /b 1
)
set MODEL_BLOB=vendor\phi3.5_model\blobs\sha256-%MODEL_SHA%
if not exist "%MODEL_BLOB%" (
    if "%GW_MODEL_PATH%"=="" (
        echo ERROR: the model is not at %MODEL_BLOB%
        echo Run "python fetch_model.py" and set GW_MODEL_PATH to the file it prints,
        echo or copy the pinned model into %MODEL_BLOB%.
        pause
        exit /b 1
    )
    if not exist vendor\phi3.5_model\blobs mkdir vendor\phi3.5_model\blobs
    mklink /H "%MODEL_BLOB%" "%GW_MODEL_PATH%" >nul 2>&1 || copy /b "%GW_MODEL_PATH%" "%MODEL_BLOB%" >nul
)
echo       Verifying its SHA-256 ^(about 2.2GB^)...
python -c "import sys, fetch_model as f; sys.exit(0 if f.sha256(sys.argv[1]) == f.MODEL_SHA256 else 1)" "%MODEL_BLOB%"
if errorlevel 1 (
    echo.
    echo ERROR: %MODEL_BLOB% is not the pinned model ^(SHA-256 mismatch^).
    echo The build stops: Groundwork ships only the tested file.
    pause
    exit /b 1
)
echo       Model verified. OK.
echo.

:: -- Step 1: Clean previous build --------------------------------------------
echo [1/4] Cleaning previous build...
if exist dist\Groundwork rmdir /s /q dist\Groundwork
if exist build\Groundwork rmdir /s /q build\Groundwork
if not exist installer_output mkdir installer_output
echo       Done.
echo.

:: -- Step 2: PyInstaller ------------------------------------------------------
echo [2/4] Bundling app with PyInstaller...
echo       This takes 2-5 minutes. Please wait.
echo.
python -m PyInstaller groundwork.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. See output above for details.
    echo Common fix: python -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo.
echo       PyInstaller complete.
echo.

:: -- Step 3: Quick smoke test -------------------------------------------------
echo [3/4] Checking bundle...
if not exist "dist\Groundwork\Groundwork.exe" (
    echo ERROR: Groundwork.exe not found in dist\Groundwork\
    echo PyInstaller may have failed silently.
    pause
    exit /b 1
)
echo       Groundwork.exe found. OK.
echo.

:: -- Step 4: Inno Setup --------------------------------------------------------
echo [4/4] Building the installers with Inno Setup...
echo.

set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO% (
    set INNO="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %INNO% (
    echo ERROR: Inno Setup not found at expected location.
    echo Install from: https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

:: All three ship the same app and model (item 31). They differ in name and
:: behaviour only: Groundwork_Setup.exe is the download, _Offline is the same
:: file under the name the website's offline link uses, and _Store installs
:: silently for Microsoft Store certification.
for %%S in (groundwork.iss groundwork_offline.iss groundwork_store.iss) do (
    echo       %%S
    %INNO% /Q %%S
    if errorlevel 1 (
        echo.
        echo ERROR: Inno Setup failed on %%S. See the messages above.
        pause
        exit /b 1
    )
)

:: -- Done -----------------------------------------------------------------------
echo.
echo ============================================
echo   INSTALLERS BUILT. Users do NOT have them yet.
echo ============================================
echo.
echo   In %CD%\installer_output\:
echo     Groundwork_Setup.exe          the download
echo     Groundwork_Setup_Offline.exe  the same, under the offline link's name
echo     Groundwork_Setup_Store.exe    silent install, for the Microsoft Store
echo.
echo   Before release: install on a clean machine. Then upload to
echo   groundworkfinance.app and publish version.json ^("latest" + "url"^)
echo   so the in-app "Update available" banner offers it.
echo.
explorer "%CD%\installer_output"
pause
