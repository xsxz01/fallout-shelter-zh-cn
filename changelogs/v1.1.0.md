## Fallout Shelter 2.7.0 汉化安装器 v1.1.0（Win32）

新增 Rust + windows-rs 的纯 Win32 GUI 安装器，不使用 WinUI3。

### 安装器功能
- 自动检测 Steam 游戏目录
- 安装 / 还原 / 校验汉化包
- 自动备份 `data.unity3d.en.bak`
- 复制进度条、实时日志、MD5 状态
- 界面配色与版式取自游戏标题界面（暗绿终端 / 扫描线 / PIP-BOY 面板）
- 单文件 `fs_installer.exe`，无额外运行时依赖（Windows 系统 DLL 除外）

### 压缩包内容
- `fs_installer.exe`
- `payload/data.unity3d`（汉化补丁）
- `翻译清单.csv`
- 汉化补丁说明 / 安装器说明

### 使用
1. 解压。
2. 运行 `fs_installer.exe`。
3. 点击“安装汉化”。
4. 通过 Steam 启动游戏。

### 校验
- 汉化 `data.unity3d` MD5：`aeb2e63b1d905451f501b5814eb94c09`
- 原版备份 MD5：`ba1b274a876253a327407cb7a1fa686e`

### 说明
- 安装前请关闭游戏。
- 仅用于合法拥有的游戏副本。
