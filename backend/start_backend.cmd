@echo off
setlocal
set "KMP_DUPLICATE_LIB_OK=TRUE"
set "HF_HUB_OFFLINE=1"
if "%HF_HOME%"=="" if exist "%~dp0..\.hf" set "HF_HOME=%~dp0..\.hf"
if "%HF_HOME%"=="" if exist "%~dp0..\..\.hf" set "HF_HOME=%~dp0..\..\.hf"
set "DIAGNEX_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%DIAGNEX_PYTHON%" set "DIAGNEX_PYTHON=%~dp0..\..\.venv\Scripts\python.exe"
if not exist "%DIAGNEX_PYTHON%" (
  echo Python environment not found. Install dependencies into a .venv beside the repository or in its parent folder.
  exit /b 1
)
cd /d "%~dp0.."
"%DIAGNEX_PYTHON%" "%~dp0run_backend.py"
