@echo off
chcp 65001 >nul
cd /d "%~dp0.."
where uv >nul 2>nul
if not errorlevel 1 (
  echo 正在使用 uv 同步依赖...
  uv sync
  if errorlevel 1 goto failed
  echo.
  echo 依赖同步完成。使用 uv run python src\localization_gui.py 启动编辑器。
  pause
  exit /b 0
)
echo 未找到 uv，改用 pip 安装...
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo 依赖安装完成。Tkinter 随 python.org 的 Windows 安装包提供。
pause
exit /b 0

:failed
echo.
echo 安装失败，请确认 Python / uv 已安装并加入 PATH。
pause
exit /b 1
