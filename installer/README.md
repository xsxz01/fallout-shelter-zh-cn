# Win32 汉化安装器

Rust + `windows-rs` 的纯 Win32 GDI 安装器，不使用 WinUI3，无第三方 UI 运行时。

## 功能

- 自动检测 Steam 版 Fallout Shelter 目录（含 `libraryfolders.vdf`）
- 显示游戏版本、`data.unity3d` 大小/MD5、原版备份、汉化状态
- 安装：自动备份 `data.unity3d` → 复制汉化包 → 原子替换
- 还原：用 `data.unity3d.en.bak` 恢复英文原版
- 校验：对比汉化包与游戏文件 MD5
- 进度条、实时日志、游戏运行检测
- 颜色/版式取自游戏标题界面：暗绿终端、扫描线、PIP-BOY 面板

## 构建

```powershell
cd installer/fs_installer
cargo build --release
```

产物：`target/release/fs_installer.exe`

## 运行

安装器从自身目录读取 `payload/data.unity3d`：

```text
FalloutShelter_Installer/
  fs_installer.exe
  payload/
    data.unity3d
```

开发时若没有 payload，会回退读取 `D:\FS_localization_work\patch_data.unity3d`。

## 打包

```powershell
python installer/build_release.py --version 1.1.0
```

生成 `dist/FalloutShelter_Installer_Win32_v1.1.0.zip`，包含安装器、payload、说明和翻译清单。

## UI 主题

`extract_ui_theme.py` 从游戏标题截图提取主色，并读取游戏字体/本地化资源信息，写入 `theme.json`。
`fs_installer/src/theme.rs` 使用提取后的暗绿/灰绿配色，字体使用系统等宽/窄体字体替代游戏内 Futura Std。
