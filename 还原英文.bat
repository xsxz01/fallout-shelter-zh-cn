@echo off
chcp 65001 >nul
setlocal
set "GAME=%~dp0.."
if not exist "%GAME%\FalloutShelter_Data\data.unity3d.en.bak" (
  echo 未找到备份文件 data.unity3d.en.bak，无法自动还原。
  echo 可以从 D:\FS_localization_work\GameBackup_2.7.0_original\FalloutShelter_Data\data.unity3d 手动复制。
  pause
  exit /b 1
)
echo 正在还原英文原版...
copy /Y "%GAME%\FalloutShelter_Data\data.unity3d.en.bak" "%GAME%\FalloutShelter_Data\data.unity3d" >nul
echo 还原完成。
pause
