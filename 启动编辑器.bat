@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
  start "" python localization_gui.py
) else (
  start "" pythonw localization_gui.py
)
