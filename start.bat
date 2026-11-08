@echo off
chcp 65001 >nul
title Ganfan Decision Machine
setlocal

rem ===== Ganfan Decision Machine - one-click start =====
rem Double-click to start. Stop with Ctrl + C in this window.
rem Python resolve order: .venv -> D:\anaconda -> py -3, each probed via "import streamlit".

set PYTHONNOUSERSITE=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set "PY="

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import streamlit" >nul 2>&1
    if not errorlevel 1 set "PY=.venv\Scripts\python.exe"
)

if not defined PY (
    if exist "D:\anaconda\python.exe" (
        "D:\anaconda\python.exe" -c "import streamlit" >nul 2>&1
        if not errorlevel 1 set "PY=D:\anaconda\python.exe"
    )
)

if not defined PY (
    py -3 -c "import streamlit" >nul 2>&1
    if not errorlevel 1 set "PY=py -3"
)

if not defined PY (
    echo [ERROR] No usable Python with streamlit found.
    echo Tried: .venv\Scripts\python.exe, D:\anaconda\python.exe, py -3
    echo Please run first:
    echo   python -m venv --system-site-packages .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo Using Python: %PY%

rem If port 8501 is already taken (old instance), stop it first.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
    echo Port 8501 busy, stopping old instance PID=%%p ...
    taskkill /F /PID %%p >nul 2>&1
)

echo.
echo  Ganfan Decision Machine starting...
echo  URL: http://localhost:8501
echo  Stop: Ctrl + C in this window
echo.

%PY% -m streamlit run app.py

echo.
echo Server stopped. Press any key to close.
pause >nul
