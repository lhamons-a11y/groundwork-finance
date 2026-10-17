@echo off
rem Item 93 (gw 2.0/GPU_ENGINE.md, "G1 proven"): the engine wheel Groundwork ships on Windows.
rem llama-cpp-python 0.3.35 from source with the Vulkan backend loaded at run time (GGML_BACKEND_DL), so a computer
rem with no Vulkan driver still runs the model on the processor. GGML_NATIVE off with the AVX2 floor the engine
rem already checks for: a native build would carry this machine's instructions and crash on older processors.
rem The processor path writes the same words as the CPU-index wheel (12 of 12 voice cases, 2026-10-17).
rem
rem Needs: Visual Studio 2022 Build Tools (C++), CMake, the Vulkan SDK. The source archive has paths longer than
rem Windows' 260-character limit, so pip works in a short temporary folder (C:\gwb), removed at the end.
rem
rem Usage: build_engine_wheel.bat [python.exe]   - builds into .\engine_wheel\ and installs into that Python.
setlocal
set PY=%~1
if "%PY%"=="" set PY=python
if "%VULKAN_SDK%"=="" for /d %%v in (C:\VulkanSDK\*) do set VULKAN_SDK=%%v
if "%VULKAN_SDK%"=="" (echo The Vulkan SDK was not found. & exit /b 1)
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" || exit /b 1
set PATH=C:\Program Files\CMake\bin;%VULKAN_SDK%\Bin;%PATH%
set CMAKE_ARGS=-DGGML_VULKAN=ON -DGGML_BACKEND_DL=ON -DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_AVX512=OFF
set FORCE_CMAKE=1
if not exist C:\gwb mkdir C:\gwb
set TMP=C:\gwb
set TEMP=C:\gwb
"%PY%" -m pip install scikit-build-core
"%PY%" -m pip wheel --no-cache-dir --no-binary llama-cpp-python --no-build-isolation --no-deps -w "%~dp0engine_wheel" llama-cpp-python==0.3.35 || exit /b 1
for %%f in ("%~dp0engine_wheel\llama_cpp_python-0.3.35-*.whl") do "%PY%" -m pip install --no-deps --force-reinstall "%%f" || exit /b 1
rmdir /s /q C:\gwb
echo Engine wheel built and installed.
