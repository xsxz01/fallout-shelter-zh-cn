@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo 正在安装 Python 依赖...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo 安装失败，请确认已安装 Python 并加入 PATH。
) else (
  echo.
  echo 依赖安装完成。Tkinter 随 python.org 的 Windows 安装包提供。
)
pause
