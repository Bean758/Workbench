@echo off
title Asteron Workbench - IDE
cd /d "%~dp0"
python workbench_ide.py
if errorlevel 1 (
    echo.
    echo ERROR: Make sure Python and PyQt5 are installed.
    echo Run: pip install PyQt5
    pause
)
