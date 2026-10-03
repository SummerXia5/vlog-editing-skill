---
name: travel-video-02-plan
description: Create distinct, footage-grounded travel film editing plans and a selected timeline blueprint from reviewed selects. Use for cinematic, playful Vlog or hybrid planning, not media rendering.
---

# Stage 2 · 多方案剪辑规划

基于真实审片结果提供有区别、可实施的方案，并把选定方案写成机器可读时间线。参考专业创作者的叙事方法；不复制对方素材、镜头顺序或调色风格。

## 输入
读取项目 brief、Stage 1 selects/coverage 和最新反馈。字段约定见 [项目交接约定](../travel-video-01-review/references/project-contract.md)。未知内容保留 unknown，不以旅行计划当成实际经历。

## 多方案
用户还没确定方向且要求不同方案时，通常给 2–3 个真正不同的选项：
- **沉浸电影版**：空间、光线、尺度、自然声构成叙事；风景镜头可以停留，人物提供动作与尺度。
- **体验 Vlog**：体验 → 真实反应或小插曲 → 有证据的感受 → 下一段；保留因果、互动和动作完成。
- **混合版**：用短高光建立期待，再在生活互动与长风景之间换气。

这是候选方向，不是每次必须套用的模板。对比每案的开场、章节顺序、情绪节奏、对白占比、音乐/环境声策略、包装、基于选段估算的时长与缺项。列出支持主张的 clip_id 与 IN/OUT。

## 落地
使用随附 FCPXML 编译器时，将语义时间线转换为 [编译清单](../../references/python-tools.md) 的整数帧结构，并保留 clip_id 关联。不要用代码默认值代替素材证据、计划选择或用户要求。

1. 已有选定风格就沿用；只请求方案时不要擅自把某案当已批准。可以标记推荐案和 provisional 时间线。需要选择而尚无答复时，继续做通用素材核对，避免抢先批量生成只适用于某案的资产。
2. 画幅沿用确认值；未确认时根据素材给建议。横片放入竖片采用具体重构图/裁切策略，逐段检查主体，不能直接强裁。时长从内容推导，Selects 可长于 Master，不能默认限制 4 分钟。
3. 写 `plans.json` 与阅读版比较表。选定或明确 provisional 的案形成 `timeline.json`：逐镜、声音、图形、旁白占位、节奏变化和匹配切点。
4. 高光快开场有明确回报，不全程快切。对白保留完整意群、前因与后反应；音乐在对白下退让，自然声独奏须有设计过的进入/退出，不留下意外断音。
5. 地图顺序采用实际行程证据，区分计划与已发生。住宿、出游、返程按用户纠正更新；Day 标签/日期、推荐信息与露脸规则按本项目 brief，不把旧项目偏好当全局限制。
6. 把露脸限制落实到人物、版本与精确区间。默认仅移除被明确指定的镜头或话题，不扩展为全员不露脸。新增手机素材必须在时间线有引用才算加入。
7. 需补旁白时写录音提示、建议时长、插入位置与目的，标 `voiceover_pending`，不冒充现场原声。费用、许可、用时和推荐结论未经证实不写进成片。

## 交付
输出 `02_plan/plans.json`、`timeline.json`、`edit_table.csv`、`voiceover_queue.csv`（仅需补录时）及方案说明。为 Stage 3 生成按镜头引用的资产任务表；用户授权执行的范围内交接 `$travel-video-03-design`。
