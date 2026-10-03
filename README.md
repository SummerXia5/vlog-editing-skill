# Vlog Editing

一个总 Skill，包含五个剪辑阶段子 Skill。

## 产品化：Vlog Editing Studio

新增面向旅行创作者的[本地 alpha 工作台](studio/README.md)：真实上传、素材预览、人工确认选段、三种排序模板、后台初剪渲染、FCPXML 与 MP4 下载。它复用本仓库的 Python 引擎；尚未接入自动 AI 审片、云端账号或收费，不应作为已上线 SaaS 宣传。

[创业产品定位与试点价格假设](docs/PRODUCT.md) · [从 alpha 到生产的路线图](docs/PRODUCTION.md) · [创始人试点运营手册](docs/PILOT.md)

```text
vlog-editing/
├── SKILL.md                 总入口：范围、状态、交接和返修路由
├── agents/openai.yaml
├── scripts/                 可直接运行的媒体/动画/FCPXML/预览工具
├── examples/                可编译剪辑、标题和地图配置样例
├── references/              命令、字段、能力边界和代码来源
├── tests/                   合成素材集成测试
└── skills/
    ├── travel-video-01-review/    素材、关键帧、动态与听审
    ├── travel-video-02-plan/      多方案与逐镜时间线
    ├── travel-video-03-design/    地图、角色、标题、转场和音效
    ├── travel-video-04-fcpxml/    生成脚本与 Final Cut Pro FCPXML
    └── travel-video-05-preview/   可播放预览及下载交付
```

## 使用

将整个 `vlog-editing` 文件夹放入个人 Skills 目录（默认 `~/.codex/skills/`），保持内部目录结构。已有同名版本先比较，不直接覆盖。

```text
使用 $vlog-editing 处理 /素材路径。
先审看素材并提供不同剪辑方案，再继续制作转场、Final Cut 工程和预览。
```

也可以告诉总入口只执行某一阶段，或按旧版时间码/截图返修。五个子 Skill 共享每个项目独立的 `project.json`，不需要每次重新开始。

## 工具与边界

内含 7 个可直接运行的 CLI：素材清点、原片/代理抽帧核对、透明标题渲染、路线动画、FCPXML 编译、XML 静态检查、手机预览；另有共享媒体模块与合成素材集成测试。它们从实际剪辑项目的 Python 代码整理而来，具体来源见 [代码提取记录](vlog-editing/references/code-provenance.md)。

使用方法、依赖与配置见 [Python 工具文档](vlog-editing/references/python-tools.md)。新项目更换原片路径、时间线清单和美术配置即可复用，无需改写通用代码。使用独立环境安装媒体依赖；清点与静态 XML 检查仍只需标准库。已使用 Python 3.12 测试。

这些 Skill 由助手编排，代码负责确定性处理。素材创作判断、连续听审、复杂调色、原生 FCP 导入/导出、按需私密发布仍要在当前环境实际执行。编译器目前支持直切、原片时码、真实连接图形与音频；不支持的变速/效果会报错，不能静默忽略。FCPXML/DTD 验证不代表 FCP 原生导入完成。

仓库仅包含工作流、模板与工具，不包含旅行原片、照片、成片、凭证或本机安装记录。未来项目发布遵循该次请求的服务与受众范围。
