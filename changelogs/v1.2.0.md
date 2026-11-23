## Fallout Shelter 2.7.0 汉化安装器 v1.2.0（Win32）

修复教程文本中 `{BUILD}`、`{HAMMER ICON}` 等花括号高亮文本仍显示英文的问题。

### 原因
游戏用 `{...}` 表示高亮文本，不是本地化占位符：
`TutorialMessageItem.ConvertMessageColors()` 只是把 `{` / `}` 替换成高亮颜色标签。
因此 `{BUILD}` 会直接显示高亮的英文单词 BUILD，需要把花括号内部也翻译成中文。

### 修复
- `{BUILD}` → `{建造}`
- `{HAMMER ICON}` → `{锤子图标}`
- `{BUILD MENU}` → `{建造菜单}`
- `{OVERSEER}` → `{监督者}`
- 保留真正的格式占位符，如 `{0}`、`{1}`
- 保留按键图标标记，如 `[A]`、`[Y]`、`[RT]`

同时人工校正了新手教程 01–68 的主要文本。

### 校验
- data.unity3d MD5：`f5dcdc160b6d36d1efa82bf832dd7880`
- 原版备份 MD5：`ba1b274a876253a327407cb7a1fa686e`

压缩包内含 `fs_installer.exe` 与更新后的 `payload/data.unity3d`。
