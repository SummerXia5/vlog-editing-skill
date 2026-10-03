# 可执行工具与项目数据

此文件是随 Skill 安装的 Python 工具使用约定。命令中的 `SKILL` 指总 Skill 目录，不是子 Skill 目录；`PROJECT` 指独立输出目录。参数全部由当前项目提供，没有固定行程、人物、画幅、硬盘路径或上传凭证。

## 环境

媒体工具已在 Python 3.12、PyAV 18.1.0、Pillow 10.3.0、NumPy 1.26.4 和 FFmpeg 7.1 上测试。使用独立环境安装 `requirements.txt`；不要改全局环境。FFmpeg 从 PATH 查找，或传 `--ffmpeg /path/to/ffmpeg`。DTD 验证另外需要 `lxml`（测试版本 5.2.1）与本机 Final Cut 的对应 Apple DTD。

素材清点与 XML 静态检查仍只依赖标准库。字体从项目指定路径读取，不打包商业字体；先核对中文字形覆盖。所有输出都使用新文件/版本目录，拒绝覆盖。失败后可能留下不完整媒体，不能标为交付；排查后使用新的输出名。

## 1 · 清点、配对与审片辅助

```sh
python3 "$SKILL/skills/travel-video-01-review/scripts/inventory_media.py" "$SOURCE" --output "$PROJECT/inventory.json"
python3 "$SKILL/scripts/review_media.py" "$PROXY" --times 0 8 16 --output "$PROJECT/review/clip-a"
python3 "$SKILL/scripts/review_media.py" "$PROXY" --compare-original "$ORIGINAL" --times 0 8 16 --output "$PROJECT/review/pair-a"
```

样本时间必须小于实际片长，先选合适区间。`review_media.py` 只打开指定文件；只有显式 `--compare-original` 才检查对应原片。返回媒体头、实际抽帧时间与成对时长差，默认 **没有人工审看/听审、没有视觉同步确认**。容器 PTS、源时间码和文件相对时间是不同坐标，不能互相代替。图像为编码方向，旋转显示、HDR、可变帧率需要另外检查。标记完整运动审看前必须实际播放动态视频。

可将 `make_preview.py --start 8 --duration 12` 用作含原声的 context reel（只适用于已核对的 SDR 媒体）。它不做语音识别、OCR 或人物识别；这些使用可用工具后回听/回看确认。

## 2 · 方案与可编译清单

方案仍由助手根据实际审片制定；不使用自动随机拼接代替编辑判断。Stage 2 的语义时间线通过项目适配脚本转换为 [compile.example.json](../examples/compile.example.json)。该示例需要替换素材、核对时长和色彩后才能执行，不能把示例当真实审片证据。

**编译清单 v1** 与 `project.json` 分开保存：后者记录流程状态，前者是明确、可执行的剪辑决定。清单路径相对其 JSON 所在文件夹，允许绝对路径但不应把个人路径提交通用仓库。

- `sequence`: width、height、`fps`（如 `30000/1001`）、`color_space`（FCP 格式字符串）。
- `assets`: ID → path、kind=`original|generated`、`tc_start`（必填、有理秒）、视频的 `color_space`。实拍填原片；生成资产填实际 MOV/WAV 等。`tc_start` 从已验证的源时码取得，明确没有源时码才填 `0`；不自动从 PTS 推断。
- `timelines`: 可同时包含 kind=`selects` 与 kind=`master`。`name` 用作文件名；每条 `clips` 列表构成连续主故事线。
- 每个 clip: 唯一 `id`、`asset`、`in`、`frames`，可选 `audio_enabled`、常量 `gain_db`、`conform=fit|fill|none`、note、overlays。
- **所有 `in / frames / at` 都是整数序列帧数**，不以各素材的 fps 解释。源 IN 相对媒体起点，半开区间 `[in, in+frames)`；编译器另外加 `tc_start`。主线时间由前面 clip 的帧数求和，不手填有冲突的 offset。
- overlay: asset、in、frames、`at`（相对父 clip 起点）、正 lane、role（默认 titles）、可选 id/note。当前必须完全包含在父 clip 内。图形预先渲染到序列画幅，支持真实透明 ProRes，不用 marker 冒充图形。
- timeline.audio: asset、in、frames、`at`（相对序列起点）、gain_db、role、可选 id/note。连接于第一主线片段，编译器换算父源时间坐标。保持原声与成品混音不重复叠加；使用成品混音时关闭对应 camera audio。

当前编译器支持直切、fit/显式 fill、常量音量、真实图形视频与音频连接。**不支持**变速、视频重叠转场、关键帧调色、裁切偏移、音量曲线、插件效果、嵌套复合片段；未知字段会报错，不能静默丢弃。需要这些功能时，在项目内扩展生成脚本并独立验证，或预渲染相应资产，交接说明编辑性变化。note 只承载未实现的说明，不表示效果已完成。

## 3 · 标题与地图动画

```sh
python3 "$SKILL/scripts/render_title.py" "$PROJECT/title.json" --output "$PROJECT/assets/title.mov"
python3 "$SKILL/scripts/render_route.py" "$PROJECT/route.json" --output "$PROJECT/assets/route.mov"
```

标题配置见 [title.example.json](../examples/title.example.json)。每行指定字体、字号、x、**baseline**、颜色和 tracking；字符共用基线，不按各字的可见顶部独立对齐。输出含淡入淡出的透明 ProRes 4444。此工具是渲染基础，具体排版、设计感、运动层次由 Stage 3 创作与回看决定，不能声称默认文字渲染即高级标题。

地图配置见 [route.example.json](../examples/route.example.json)。输入实际地图背景、车贴 PNG、核对后的路线屏幕坐标、来源记录；地图位置和像素坐标必须使用同一投影/视口。`geography_verified=true` 是人工核对记录，工具不会联网自动证明真实道路。单段路线不允许跨断开的区域直接插值，换区域另做段落。地图来源署名按其许可保留在背景或说明中。

小车原图朝屏幕上方，旋转中心固定；按折线弧长前进，首尾五次缓动，沿固定距离前后取切线并消除角度跨 ±180° 翻转。位置严格停留在原折线上，不改路线来掩盖抖动。真实急转角可以另加停顿/镜头切换，不能称所有道路自动达到平滑。输出真实 MOV 与逐帧 `.motion.json`。角色设计、白色 Tesla 等均是某个项目输入，不是通用默认。

## 4 · FCPXML 与剪辑表

```sh
python3 "$SKILL/scripts/build_fcpxml.py" "$PROJECT/compile.json" --output "$PROJECT/04_fcp/v01" --dtd "$APPLE_DTD"
python3 "$SKILL/skills/travel-video-04-fcpxml/scripts/check_fcpxml.py" "$PROJECT/04_fcp/v01/TRIP_MASTER_v01.fcpxml"
```

输出每条 timeline 的 `.fcpxml` 与包含画面/图形/音频的 `.csv`，另有 build.json（输入快照、媒体探测、验证状态）。检查原片路径、LRV 禁用、媒体界限、序列帧网格、source timecode、连接偏移及可选 DTD。静态 XML / DTD 通过不等于原生 FCP 已导入，也不等于已匹配 HDR/SDR 观感。实际 FCP 导入、旋转构图、混音与导出由第四阶段继续完成。此版本未自动生成 CMX EDL；有多轨/变速时选用能准确表达的交付格式，不能把 CSV 更名为 EDL。

## 5 · 轻量预览

```sh
python3 "$SKILL/scripts/make_preview.py" "$PROJECT/export/master.mp4" --sdr-confirmed --long-edge 960 --output "$PROJECT/05_preview/v01.mp4"
```

输入是完成的导出或明确源窗口，**不是 FCPXML**。本工具不模拟 FCP 渲染器。保持画幅缩放、不强裁；H.264/yuv420p、AAC、faststart，完整解码并校验时长，输出 SHA-256 与 receipt。PQ/HLG 输入拒绝处理，先做经过审看的色彩管理；不能靠加 bt709 标签解决 HDR。

它不会部署站点或发出私密视频。所附 receipt 中 hosted、browser_download_verified、visual_review、audio_audition 初始为 false；用户要求预览链接时按第五子 Skill 使用当前服务，再核对线上真实播放和完整文件下载。

## 回归测试

```sh
python3 "$SKILL/tests/smoke_pipeline.py" --ffmpeg "$FFMPEG" --font "$CJK_FONT" --dtd "$APPLE_DTD" --report "$PROJECT/tests/new-report.json"
```

脚本生成短合成视频，检查 29.97、非零时码、重复源片段、连接图形/声音、LRV 与错误范围拒绝、透明标题、路线端点/朝向、预览完整解码、原文件未变。可不传 DTD，但报告不得声称 DTD 通过。无需私人素材；没有覆盖实际原生 FCP 导入或站点发布。
