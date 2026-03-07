@echo off
REM Single entry point — delegates to run.py (works on macOS and Windows).
cd /d "%~dp0"
python run.py %*
