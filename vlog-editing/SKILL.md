---
name: vlog-editing
description: Coordinate a five-stage travel video editing workflow from footage review through alternative plans, real transition assets, editable Final Cut Pro deliverables and verified previews. Use for end-to-end Vlog editing, resuming a project, or routing precise revisions to the relevant child skill.
---

# Vlog Editing

旅行视频剪辑的总入口。下属五个子 Skill 负责具体阶段；本文件负责理解范围、项目状态、交接与返修，不重复实现子阶段。

## 五个子 Skill

| 阶段 | 子 Skill | 输入 → 输出 |
| --- | --- | --- |
| 1 | [素材读取与审看](skills/travel-video-01-review/SKILL.md) | 原素材/已有索引 → 代理配对、关键帧、动态及听审证据、候选选段 |
| 2 | [多方案剪辑规划](skills/travel-video-02-plan/SKILL.md) | 已审看片段/brief → 不同方案、选定或 provisional 时间线 |
| 3 | [转场与包装资产](skills/travel-video-03-design/SKILL.md) | 时间线/风格 → 实际角色、地图动画、标题、转场和音效 |
| 4 | [Final Cut Pro 工程](skills/travel-video-04-fcpxml/SKILL.md) | 时间线/真实资产 → 生成脚本、原片引用 FCPXML、剪辑表和验证 |
| 5 | [预览与交付](skills/travel-video-05-preview/SKILL.md) | 渲染产物 → 可播放预览、按需链接、完整 MP4 下载验证 |

这些阶段由当前助手执行。加载所需子 Skill 的文件即可，不默认创建新任务或启动子代理。子 Skill 名称不可直接调用时，使用上表路径读取其指令；不要因此停止工作。

## 随附 Python 工具

这套 Skill 包含可执行代码，不只是指令。进行素材探测、抽帧、标题/地图渲染、FCPXML 编译或轻量预览时，读取 [Python 工具与配置约定](references/python-tools.md)，优先调用 `scripts/` 中已有工具；不要每个项目重写同样逻辑。已有的素材清点、XML 检查脚本位于对应子 Skill 内。

工具输入与创作决定放在项目目录，通用实现放在 Skill 内。复杂调色、变速和特殊转场超出基础编译器能力时，保存项目适配脚本并验证，不忽略字段或宣称已实现。代码来历与提取范围见 [复用来源](references/code-provenance.md)。

## 开始或续做

1. 先理解用户此轮目标：全流程、只审片、比较方案、资产制作、FCP 交付、预览发布或精确返修。不要把一次下载修复变成重剪全片，也不要因为调用总入口就上传私人视频。
2. 定位用户提供的源目录、已有项目输出和 `project.json`。新项目使用 [项目模板](skills/travel-video-01-review/assets/project.json)，字段遵循 [交接约定](skills/travel-video-01-review/references/project-contract.md)。记录当前版本、授权范围、画幅、剪辑方向、人物映射和已确认决定。
3. 有已有产物时验证路径、版本和相关输入是否仍有效，再从缺失或受影响的阶段开始；不重复全盘读取和解码。`ready`、`approved`、`native_import_verified`、`hosted` 不能互相代替。
4. 只加载当前阶段及必要前置子 Skill。用户要求完整流程时依次推进，不在每个阶段重复索要授权；用户只要求方案时到方案交付结束。

## 方案与风格决策

- 未确定剪辑方向且用户需要不同方案时，第二阶段提出素材支撑的差异方案和推荐。已有选择直接沿用。
- 未确认的方案标 provisional。需要用户决定时先交付可比较的具体方案或样段，并继续通用素材核对；不批量生成依赖未定风格的资产。
- 风格范围从 brief 决定：可做沉浸电影版、旅行 Vlog 或混合版。不要将旧 Redwood 项目的地点、人物、车辆、日期、画幅和露脸约束自动套到新旅行。
- 第三阶段先按任务需要做风格样段，再扩展；没有反馈不能标风格已批准。动画与地图必须有实际可用素材，不能用几个 marker 代替。

## 返修路由

| 用户反馈 | 从哪里处理 |
| --- | --- |
| 找遗漏互动、完整台词、新手机素材、截图对应原片 | 1 审看 → 2 更新时间线 |
| 顺序、时长、开场、Day 标签、指定露脸删除 | 2 更新约束与时间线；需要新内容时回到 1 |
| 角色不对、地图抖动、地理错误、标题难看 | 3 资产返修 |
| XML 导入失败、原片丢失、时间码/多轨问题 | 4 工程返修 |
| 音乐突然断掉、过曝或音画不同步 | 先定位源/时间线/渲染层，回到相关 1/2/3/4，再由 5 复查 |
| 链接打不开、下载无反应、线上还是旧版 | 5 交付修复；编辑内容不随之改变 |

保存旧版时间/截图 → clip_id/source range → 请求改动 → 新版时间/复查结果。优先用户最新且具体的范围，不把局部露脸删除扩大到全片人物。

## 交接与完成

每阶段更新同一 `project.json` 的 inputs、outputs、状态和缺项；让下一阶段读取真实文件而不是只依赖聊天摘要。原素材只读，已接受版本保留，新版本独立输出。

FCPXML draft、成功原生导入、导出成片、轻量预览与已上线版本分别标记。无法听审或核对原片的内容必须明确留为未确认；实际下载需验证完整 MP4，不能只检查链接存在。

按用户当前范围交付可用结果和准确限制。缺少访问、身份参考或发布服务时继续独立工作，保留可恢复状态；不得声称尚未实际完成的阶段已完成。
