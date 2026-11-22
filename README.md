# Fallout Shelter 2.7.0 简体中文汉化

[![Latest release](https://img.shields.io/github/v/release/xsxz01/fallout-shelter-zh-cn)](https://github.com/xsxz01/fallout-shelter-zh-cn/releases/latest)

最新汉化包：<https://github.com/xsxz01/fallout-shelter-zh-cn/releases/latest>

《辐射：避难所》2.7.0（Steam / Unity 6）简体中文汉化补丁的源码与工具。

> 仅用于你合法拥有的游戏副本。游戏文本、字体与资源版权归 Bethesda Softworks / ZeniMax 所有。
> 本仓库的代码以 MIT 协议发布；游戏资源与第三方字体不适用 MIT。

## 功能

- 14,073 条 I2 Localization 词条（界面、任务、对话、物品、教程）
- 内置 Tkinter 汉化编辑器：搜索、筛选、逐条修改、恢复机翻、导出清单
- 一键重新构建 `data.unity3d` 并安装到游戏
- 一键生成版本化压缩包并发布 GitHub Release
- 支持备份/还原原版文件

## Win32 安装器

`installer/fs_installer` 是 Rust + `windows-rs` 的纯 Win32 GDI 安装器，
用于安装/还原汉化包，界面配色与版式取自游戏标题界面。

```powershell
cd installer/fs_installer
cargo build --release
```

打包：

```powershell
python installer/build_release.py --version 1.1.0
```

### 使用编辑器

双击 `启动编辑器.bat`，或：

```bash
python localization_gui.py
```

编辑器会读取：

- `langsource_orig.json`：从原版提取的词条
- `translations_cache.json`：机翻缓存
- `overrides.json`：人工覆盖（优先级最高）

修改后点“保存修改”，再点“构建补丁”即可重新生成并安装。

### 命令行构建

```bash
python make_font.py      # 从 C:\Windows\Fonts\simhei.ttf 生成精简字体
python build_patch.py    # 从 data.unity3d.en.bak 构建补丁
python export_list.py    # 导出 翻译清单.csv
```

`build_patch.py` 固定从游戏目录的 `data.unity3d.en.bak` 读取原版，避免重复叠加翻译。

### 发布新版本

```bash
python package_release.py --version 1.0.0
```

会构建补丁、打包 `dist/FalloutShelter_2.7.0_zh-CN_v1.0.0.zip`，
并通过 `gh release create` 上传到当前仓库的 Release。

## 目录说明

| 文件 | 说明 |
|---|---|
| `localization_gui.py` | Tkinter 汉化编辑器 |
| `loc_core.py` | 词条加载、优先级、CSV 导出 |
| `translate.py` | Google gtx 批量机翻与占位符保护 |
| `retry_missing.py` | 补漏翻译 |
| `overrides.json` | 人工 UI 覆盖（按 Term Key） |
| `translations_cache.json` | 机翻缓存（按英文原文） |
| `翻译清单.csv` | 14,073 条完整对照表 |
| `make_font.py` | 生成 Unity 兼容的 SimHei 子集 |
| `build_patch.py` | 写回词条、替换字体、生成 data.unity3d |
| `package_release.py` | 版本打包与 GitHub Release |
| `verify_patch.py` | 回读校验补丁 |
| `export_list.py` | 重新导出 CSV |

## 花括号高亮文本

游戏教程中的 `{BUILD}`、`{HAMMER ICON}` 不是本地化占位符，而是高亮颜色标记：
`TutorialMessageItem.ConvertMessageColors()` 只替换 `{` / `}` 为颜色标签。
翻译时应保留花括号并翻译内部文字，例如 `{建造}`、`{锤子图标}`；
真正的格式占位符 `{0}`、`{1}` 和按键标记 `[A]`、`[RT]` 保持不变。

## SPECIAL 的翻译

- `SPECIAL` 作为属性系统时统一译为 **特殊属性**。
- `{DWELLER'S SPECIAL}` → `{居民的特殊属性}`
- `{TRAIN}` → `{训练}`，`{INCREASE}` → `{提高}`
- 英文小写 `special` 作形容词时按语境译为“特别/特殊”，不强行统一为“特殊属性”。

## 翻译优先级

```text
overrides.json（人工 UI）
  > SHORT_MAP（术语/缩写）
  > translations_cache.json（机翻）
  > 英文原文
```

## 字体说明

Unity 6 legacy 字体对部分 OpenType 表不兼容。`make_font.py` 会：

1. 删除 `vhea/vmtx/STAT/GPOS/GSUB` 等表；
2. 用 `--no-prune-unicode-ranges` 保留 CJK Unicode 范围；
3. 把 OS/2 代码页范围修正为包含简体中文；
4. 清空 `FontManager` 的 ASCII 位图字体，强制 UILabel 使用动态字体。

字体文件不随仓库分发，请在本机 `C:\Windows\Fonts\simhei.ttf` 存在时运行 `make_font.py`。

## 许可

代码：MIT。游戏资源、文本与 SimHei 字体：归各自权利人所有，仅用于个人汉化研究。
