@echo off
setlocal
pushd "%~dp0"

call :execute_installation
set EXIT_CODE=%errorlevel%

call deactivate 2>nul
popd

if "%~1" neq "nopause" pause
exit /b %EXIT_CODE%

:execute_installation
if not exist .venv (
    echo Creating virtual environment for applio...
    py -3.12 -m venv .venv 2>nul || python -m venv .venv || exit /b 1
)

call .venv\Scripts\activate.bat
call python -m pip install --upgrade pip || exit /b 1
call python -m pip install -r requirements.txt || exit /b 1

nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo NVIDIA GPU detected. Installing CUDA torch...
    call python -m pip install --upgrade torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128 || exit /b 1
)

python install.py || exit /b 1

echo Installation for applio complete
goto :eof