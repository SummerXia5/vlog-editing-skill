# 五阶段项目交接约定

五个子 Skill 位于总 Skill `vlog-editing` 的 `skills/` 目录中，彼此同级。每阶段可以独立调用；跨阶段需读取同一项目输出目录内的 `project.json`，不依赖聊天记忆或硬编码旅行路径。用户的新指令优先，已确认的决定不重复询问。

## 项目目录

```text
PROJECT_OUTPUT/
  project.json
  01_review/       inventory, pairs, coverage, selects, keyframes, context_reels
  02_plan/         plans, timeline, edit_table, voiceover_queue
  03_design/       asset_manifest, assets, style_preview
  04_fcp/vNN/      generation script, input manifest, SELECTS/MASTER FCPXML, validation
  05_preview/vNN/ preview, delivery, QA
  feedback.json
```

目录按实际产出创建，不需要空文件或虚构已完成的阶段。原素材目录始终只读。所有输入路径在项目运行时解析，交接产物应使用绝对路径或清楚标明的项目相对路径。

## project.json

从模板初始化，填写 `project_id`、source_roots、output_root、current_version、brief、constraints、people、stages、artifacts 和 delivery。aspect_ratio、fps、color_space 在未知时保留 null。brief 记录风格、用户明确时长要求、画幅、语音/露脸/字幕偏好；`selected_plan_id` 和 `plan_status` 分开记录。

`constraints` 每条含 id、用户原话、适用版本/人物/章节/区间、状态和来源。后来的窄范围修正替代相同范围的旧约束，不把局部指令扩大到全片。

stage 状态使用 `not_started | in_progress | ready | needs_input | blocked`；ready 表示该阶段范围内产物可交接，不等于用户已批准。approval 另用 `not_requested | pending | approved`。每阶段保留 inputs/outputs 路径、验证摘要和未完成项。交接只检查相关前置条件，不为了表格完整强制执行不需要的阶段。

## 媒体、时间与选段

**inventory/pairs**：稳定 clip_id、原片路径、代理路径（可为空）、文件指纹、设备/录制批次、元数据和 pairing_status。文件名只用于候选；verified 必须有核对证据。保存 `proxy_to_source` 映射的 offset/rate 或分段对应关系；非线性或未知映射不得直接套时间。

**所有人可读 IN/OUT 使用源媒体开头起算的秒数、半开区间 [in,out)**。另存原片媒体起始 timecode。XML 编译阶段将相对时间加到媒体起始时间，按具体 FPS 用整数帧/有理秒表达。代理时间另记，不能与源时间混用。

**selects.json**：数组或带 schema_version 的对象。每段至少包含：
- select_id、clip_id、lrv_filename（无则 null）、original_path。
- proxy_in/out（若代理审看）、source_in/out、duration、timing_verified。
- description、why_it_works、suggested_chapter、composition、movement、light、action/reaction。
- review.visual (`unreviewed | keyframes_only | sampled_motion | continuous`)、review.audio (`unheard | asr_only | auditioned`)、实际 reviewed_ranges 和 evidence 路径。
- dialogue：start/end/text、verification (`asr_unverified | heard_uncertain | verified`)，与 screen_text/OCR 分开。
- source_sound、privacy_notes、framing_options、technical_issues。

**review_coverage.json**：每个源的总时长，动态播放、抽帧和听审区间分别列出。计算覆盖率时合并重叠区间；关键帧只有离散时间点，不当作连续区间。未检查尾段保留 uncovered。

## 规划与资产

**plans.json**：plan_id、logline、structure、opening、scene references、sound strategy、graphics、estimated_duration、tradeoffs、missing_evidence、approval。

**timeline.json**：schema_version、project_id、version、plan_id、sequence（width/height/frame_rate/color_space）、ordered clips。每个 clip 有 instance_id、select_id/asset_id、original_path、source_in/out、timeline_in/out、speed、chapter、framing、audio、graphics、notes。同一 select 重复使用需不同 instance_id。所有 timing 需明确单位与时间原点；连接片段按其父项参照转换。

**asset_manifest.json**：asset_id、type、path、status (`planned | placeholder | generated | reviewed | approved`)、dimensions、frame_rate、duration、alpha、color_space、license/source、generation_recipe、referencing timeline instances。文件不存在不能标 generated，静态图不能标 animated。

## 反馈与交付

**feedback.json**：feedback_id、用户原话/截图路径、reference_version、reference_range、mapped select/clip/source range、requested change、implementation version、new_range、verification、status。截图时间和播放器标签矛盾时先定位实际画面。

**delivery.json**：video_version、local_files（path/bytes/hash/duration）、fcpxml_status、native_fcp_status、preview_render_status、hosted_version、URL、download URL、audience、deployment status、playback_check、download_check、audio_review、unresolved。保存或上传成功不等于已上线；头部请求成功不等于整片可下载。

## 结束条件

按用户当前请求范围交付。整套工作流仅在需要的产物生成并通过相应验证后结束。缺少照片、素材访问、对白听审能力、目标 FCP 或发布服务时继续不依赖它们的工作，准确列明受阻部分，不造出通过状态。
