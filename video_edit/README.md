# 视频剪辑工作区

## 目录

```text
video_edit/
  raw/            # 你录制的 A1–A15 + narration.wav + bgm.mp3
  assets/         # 标题卡、结尾卡、封面
  overlays/       # 自动生成的字幕条/下三分之一
  subtitles/      # draft.srt / draft.ass
  temp/           # 归一化片段
  output/         # 成片
  edit_plan.json  # 分镜时长与素材名
  edit.py         # 自动剪辑脚本
```

## 使用

1. 把素材按 `B站视频脚本_90秒.md` 里的文件名放进 `raw/`。
2. 重新生成字幕：

   ```powershell
   python make_subtitles.py
   ```

3. 渲染：

   ```powershell
   双击 run_edit.bat
   ```

   或：

   ```powershell
   python edit.py
   ```

   无字幕预览：

   ```powershell
   python edit.py --no-subs
   ```

4. 输出：

   `output/draft_v1.mp4`

## 游戏素材

`assets/` 里的标题卡、结尾卡、封面使用游戏内提取的图片生成：

```powershell
python extract_game_assets.py   # 从游戏 bundle 导出背景 / logo / Vault Boy
python make_assets.py           # 重新合成标题卡、结尾卡、封面
python make_overlays.py         # 重新生成下三分之一短标签
```

`game_assets/` 是本地提取目录，不提交到仓库。

## ffmpeg

脚本默认使用 `D:\ffmpeg.exe`，也可用环境变量覆盖：

```powershell
$env:FFMPEG="D:\ffmpeg.exe"
```

## 说明

- `A1–A15` 必须存在，否则脚本会列出缺失文件。
- 每个片段会统一为 1920×1080 / 60fps / H.264，并叠加 `overlays/A*.png` 的下三分之一文字。
- `narration.wav` 不存在时输出无声视频；`bgm.mp3` 不存在时只用旁白。
- `draft.ass` 是按分镜时长估算的草稿字幕，最终以 TTS 实际音频为准，可在 `make_subtitles.py` 的 `edit_plan.json` 时长调整后重新生成。
