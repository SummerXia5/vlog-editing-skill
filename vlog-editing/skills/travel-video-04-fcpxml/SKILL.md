---
name: travel-video-04-fcpxml
description: Generate reproducible Final Cut Pro editing scripts, original-media FCPXML timelines, edit tables and validation from an approved or explicitly provisional travel video plan.
---

# Stage 4 · Final Cut Pro 可重建工程

将时间线、实际资产和声音安排转换为生成脚本、FCPXML 与剪辑表。FCPXML 是可导入的交换文件；没有在 Final Cut 成功创建并验证媒体库时，不把 XML 宣称为原生 `.fcpbundle`。

## 输入与生成
- 基础直切、连接图形和声音使用总 Skill 的 `scripts/build_fcpxml.py`，将计划转为显式配置；命令、支持字段与限制见 [Python 工具约定](../../references/python-tools.md)。随交付保存清单和重建命令；超出能力时在项目内扩展脚本，未知字段不能丢弃。
- 读取 `project.json`、Stage 1 配对与 review coverage、Stage 2 timeline、Stage 3 asset manifest。工作在新的版本目录，不覆盖已接受的 Cinematic 或其他版本。
- 按 [FCPXML 实施与验证](references/fcpxml-handoff.md) 处理时间。用户要求全流程时还需提供可运行的 `build_fcpxml.py`（或等效生成脚本）、输入数据和重建命令；只要求脚本时不要代为导入 FCP。
- 生成 `PROJECT_SELECTS.fcpxml`、`PROJECT_MASTER_vNN.fcpxml`、完整剪辑表和项目适用的 EDL。FCPXML 的实拍资源引用原始 MP4/MOV 等相机媒体，不引用分析 LRV；包装引用实际资产。
- 声音使用有意义的 roles 和真实音频素材；记录声道映射、音量、自动化、交叉淡化。原声与图像使用同一已核对的时间映射。变速、转场重叠、connected clip offset 明确计算。
- 调色先查输入 HDR/SDR、旋转/变换与目标色彩空间，再按场景匹配曝光、高光、肤色和阴影；亮部压暗不等于恢复已剪切信息。无法可靠写入目标版本 XML 的效果用明确 note/marker，加实际参考预览或必要的渲染资产。
- 不能将整个 Master 压平为一个片段后宣称可逐镜编辑。若提供渲染参考版，单独标明。

## 验证与交付
1. 运行 `scripts/check_fcpxml.py FILE` 做静态检查；它只检查 XML、资源、时间语法和文件存在，不代表 Apple DTD 或 FCP 导入成功。查目标 FCP 版本对应官方 DTD/文档或已验证导出作为结构依据。
2. 检查源 IN/OUT 在媒体范围内、帧对齐、所有图形/音频引用、总时长、布局、转场 handles、离线媒体及 selects/master 差异。包含可编辑标题时核对 title effect UID 与安装依赖。
3. 对生成器做有意义的检查：重复源片段、非零媒体起始 timecode、29.97 等有理帧率、旋转竖片、音频/图形连接、被删除的片段；根据实际项目范围选择案例。
4. 用户要求导入或已授权时，在新事件/新项目导入并核对。仅 draft 请求则不导入。导入失败保留 XML/日志，最多修复三次同类错误再报告准确缺项。
5. 导出 `04_fcp/validation.json` 和 `handoff.json`：静态检查、DTD、原生导入、主片渲染分别标状态。关联反馈的旧版本时间范围与新时间范围。

交接 `$travel-video-05-preview`；只承诺已验证的层级。
