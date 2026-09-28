@echo off
REM Double-click this file to start Career Intelligence.
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Please follow docs\SETUP_WINDOWS.md, step 1.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo First start: preparing the application. This takes a minute...
  py -3 -m venv .venv
  if errorlevel 1 ( echo Could not create the Python environment. & pause & exit /b 1 )
)

".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 ( echo Could not install the required packages. Check your internet connection. & pause & exit /b 1 )

if not exist ".env" copy ".env.example" ".env" >nul
if not exist "private" mkdir private

".venv\Scripts\python.exe" run.py
pause
