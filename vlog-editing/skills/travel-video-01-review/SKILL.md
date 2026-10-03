---
name: travel-video-01-review
description: Inventory local travel footage, pair LRV proxies with originals, and review motion, dialogue and keyframes into evidence-backed selects. Use for footage intake or starting this five-stage travel video workflow.
---

# Stage 1 · 素材读取与内容审看

将素材变成有证据的候选片段，不把截图浏览等同于完整审片。可单独运行；用户要求整套流程时依次交接给后四个 Skill，不另建任务、不默认委派。

## 开始与项目记录
- 先确认可访问的源目录、已有索引、最近版本与用户最新要求。只读原素材；在独立项目输出目录写索引、代理分析和新版本。
- 阅读 [项目交接约定](references/project-contract.md)。新项目从 [project.json](assets/project.json) 复制并填写；继续项目先读实际记录，保留用户已确认的选择。
- 读取 [审片方法](references/review-method.md)。已有索引可复用，但不同剪辑方向需要重新寻找适合的内容。

## 执行
配对抽帧可调用总 Skill 的 `scripts/review_media.py`；动态 context reel 可使用 `scripts/make_preview.py` 的源窗口参数。先读 [工具用法](../../references/python-tools.md)，抽帧与生成 context reel 都不等于实际审看或听审。

1. 先列文件路径、大小和修改时间，不一开始解码全部 MP4。可运行 `python3 scripts/inventory_media.py SOURCE --output NEW_JSON`；它只提供文件名配对候选，绝不代表可靠配对或已审片。
2. 优先 LRV。建立稳定 clip_id、LRV ↔ 原始 MP4/MOV、未配对和歧义清单。按设备/命名族抽查若干组；核对帧率、视频起点、时长、旋转元数据，并在开头/中间/结尾检查同一动作。记录误差和具体时间映射，不能凭同名或同长度认定同步。
3. 新手机文件先去重并检查 HDR/SDR、可变帧率、旋转方向；无代理时有针对性地检查原片或另建分析代理，不改原文件。
4. 分批审看动态内容，提取带 source time 的关键帧和前后 context reel。围绕动作起止、相机运动、构图、尺度、光线、反应、互动和意外寻找片段。为每个候选实际播放足够前后内容。
5. 单独审听对白、笑声和环境声；ASR 是线索，OCR 是画面文字，二者分开保存。字幕引用、人物评价、笑点必须回到原声确认。听不清或没有可用听审能力时明确标为未确认，不虚构台词。
6. 建立覆盖记录：抽帧、动态审看、听审分别记录已检查范围。用户要求全量筛选时继续处理全部 LRV；只抽样过的区间不得写成完整审看。

## 产出与交接
- `01_review/inventory.json`、`proxy_pairs.json`、`review_coverage.json`。
- `01_review/selects.json` 和便于阅读的剪辑候选表，附 keyframes/context_reels、转录和 OCR。
- 每段包含源 IN/OUT、描述、有效原因、动作/对白完整性、声音、建议章节、配对及审看证据。
- 候选数量随素材质量和用户要求决定，不为凑数或固定时长丢弃有价值的段落。关键缺失映射、未审听和未审看范围必须随选段交接。
- 下一步使用 `$travel-video-02-plan`。用户只要求审片时交付本阶段即可。
