@echo off
title Groundwork - Build Installer
color 0A
echo.
echo ============================================
echo   Groundwork Installer Builder
echo ============================================
echo.

:: Change to project directory
cd /d C:\Groundwork

:: -- Step 0: Preflight check - watchdog must be bundled --------------------
:: GROUNDWORK_STATUS.md flagged this as an open item: without watchdog
:: explicitly in the PyInstaller spec (as a hiddenimport or otherwise), the
:: Downloads auto-import watcher silently doesn't exist in the frozen
:: installer - no error, no warning, testers just never see the auto-import
:: banner and there's no way to tell from the outside that anything's wrong.
:: Checking the actual spec file here, at build time, instead of trusting
:: that this got fixed at some point and was never verified.
echo [0/4] Checking that watchdog is bundled...
:: Regex requires "watchdog" to appear before any '#' on the line, so a
:: line that's only a comment mentioning watchdog (e.g. if the real
:: hiddenimports entry were ever removed but an explanatory comment left
:: behind) correctly does NOT satisfy this check.
findstr /i /r "^[^#]*watchdog" groundwork.spec >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  WARNING: "watchdog" not found anywhere in groundwork.spec
    echo ============================================================
    echo  If watchdog isn't declared as a hidden import, the Downloads
    echo  auto-import watcher will be silently missing from this build.
    echo  The app will run fine - testers just won't get the "file
    echo  detected" import banner, with no indication anything's wrong.
    echo.
    echo  Press Ctrl+C to stop and fix groundwork.spec first, or
    pause
) else (
    echo       watchdog reference found in spec. OK.
)
echo.

:: -- Step 0b: Ollama installer must be present to bundle --------------------
:: Downloaded once and cached in vendor\ rather than committed - it's ~1.3GB
:: and Ollama ships updates often enough that a stale copy isn't a one-time
:: cost worth paying either. Delete vendor\OllamaSetup.exe manually before a
:: build if you want the bundled version refreshed.
echo [0b/4] Checking for bundled Ollama installer...
if not exist vendor mkdir vendor
if exist vendor\OllamaSetup.exe (
    echo       vendor\OllamaSetup.exe present. OK.
) else (
    echo       Not found - downloading from ollama.com ^(~1.3GB, this may take a while^)...
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'vendor\OllamaSetup.exe'"
    if errorlevel 1 (
        echo.
        echo ERROR: Could not download OllamaSetup.exe.
        echo Check your internet connection, or download it manually from
        echo https://ollama.com/download/OllamaSetup.exe into vendor\
        pause
        exit /b 1
    )
    echo       Downloaded.
)
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
pyinstaller groundwork.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. See output above for details.
    echo Common fixes:
    echo   - Make sure all packages are installed: pip install -r requirements.txt
    echo   - Make sure bank_importer.py is in C:\Groundwork\
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
echo [4/4] Building installer with Inno Setup...
echo.

:: Find Inno Setup compiler
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

%INNO% groundwork.iss
if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup failed. See output above.
    pause
    exit /b 1
)

:: Offline installer (Phase 6B) - only if the phi3.5 model has been staged
:: into vendor\phi3.5_model\. Unlike vendor\OllamaSetup.exe, there's no simple
:: single-file download for this (it's copied out of a real local Ollama
:: install's model store), so skip it rather than fail the whole build when
:: it's missing - Lane A (groundwork.iss) alone is still a complete, working
:: installer.
if exist "vendor\phi3.5_model\manifests\registry.ollama.ai\library\phi3.5\latest" (
    echo.
    echo Building offline installer ^(bundled phi3.5 model^)...
    %INNO% groundwork_offline.iss
    if errorlevel 1 (
        echo.
        echo ERROR: Offline installer build failed. See output above.
        pause
        exit /b 1
    )
) else (
    echo.
    echo   NOTE: vendor\phi3.5_model\ not found - skipping the offline
    echo   installer. Groundwork_Setup.exe ^(online^) was still built.
)

:: Store installer (Path 2) - only if a full Ollama runtime has been staged
:: into vendor\ollama_runtime\. This lane runs NOTHING during install: the
:: runtime and the model both go down as plain file copies, so the install
:: certifies silently under Store requirement 10.2.9.2, and Groundwork starts
:: Ollama itself on launch (_ensure_ollama_running in launch.py). The runtime
:: is staged by hand from a machine that has Ollama installed - there's no
:: single-file download for it - so skip rather than fail the whole build when
:: it's absent, same reasoning as the offline lane above.
::
:: NOT YET VERIFIED on a clean machine: portable Ollama plus an app-started
:: `ollama serve` must be tested on a box with no prior Ollama before this
:: output is submitted to the Store.
if not exist "vendor\ollama_runtime\ollama.exe" (
    echo.
    echo   NOTE: vendor\ollama_runtime\ not found - skipping the Store
    echo   installer. Stage it by copying the contents of
    echo   %%LOCALAPPDATA%%\Programs\Ollama\ from a machine that has Ollama
    echo   installed ^(ollama.exe, "ollama app.exe", lib\, app.ico^).
)
if exist "vendor\ollama_runtime\ollama.exe" if not exist "vendor\phi3.5_model\manifests\registry.ollama.ai\library\phi3.5\latest" (
    echo.
    echo   NOTE: vendor\phi3.5_model\ not found - skipping the Store
    echo   installer, which bundles the model as file copies too.
)
if exist "vendor\ollama_runtime\ollama.exe" if exist "vendor\phi3.5_model\manifests\registry.ollama.ai\library\phi3.5\latest" (
    echo.
    echo Building Store installer ^(file-copy Ollama + phi3.5, nothing executed^)...
    %INNO% groundwork_store.iss
    if errorlevel 1 (
        echo.
        echo ERROR: Store installer build failed. See output above.
        pause
        exit /b 1
    )
)

:: -- Done -----------------------------------------------------------------------
echo.
echo ============================================
echo   INSTALLER BUILT. Testers do NOT have it yet.
echo ============================================
echo.
echo   Installer is at:
echo   C:\Groundwork\installer_output\Groundwork_Setup.exe
echo.
echo   Two ways testers actually get this:
echo.
echo     A. Send that file to them directly right now
echo        ^(fastest - good for an urgent fix like tonight's^)
echo.
echo     B. Upload it to groundworkfinance.app and update
echo        version.json ^("latest" + "url"^) so the in-app
echo        "Update available" banner picks it up automatically
echo        next time they launch Groundwork
echo.
echo   For anything this important, do BOTH - direct send now,
echo   plus the site update so the download page and update
echo   banner aren't still pointing at the broken version.
echo.
explorer C:\Groundwork\installer_output
pause
