@echo off
chcp 65001 >nul
setlocal
set "GAME=%~dp0.."
if not exist "%GAME%\FalloutShelter_Data\data.unity3d" (
  echo 未找到游戏目录。请把“汉化补丁”文件夹放在 FalloutShelter.exe 所在目录下再运行。
  pause
  exit /b 1
)
if not exist "%GAME%\FalloutShelter_Data\data.unity3d.en.bak" (
  echo 正在备份原始文件...
  copy /Y "%GAME%\FalloutShelter_Data\data.unity3d" "%GAME%\FalloutShelter_Data\data.unity3d.en.bak" >nul
)
echo 正在安装汉化...
copy /Y "%~dp0data.unity3d" "%GAME%\FalloutShelter_Data\data.unity3d" >nul
if errorlevel 1 (
  echo 安装失败：请右键“以管理员身份运行”本脚本。
) else (
  echo 汉化安装完成。请通过 Steam 启动游戏。
)
pause
