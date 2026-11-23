@echo off
chcp 65001 >nul
cd /d "%~dp0.."
where pythonw >nul 2>nul
if errorlevel 1 (
  start "" python src\localization_gui.py
) else (
  start "" pythonw src\localization_gui.py
)
