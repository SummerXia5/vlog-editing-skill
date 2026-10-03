# 从实际项目提取的代码

工具层源于这次旅行剪辑中生成和修复过的 Python 逻辑，再去除本机目录、人物、路线、精确选段、旧版本动态导入和发布凭证。这里保留源脚本相对路径，便于原工作区追溯；安装包运行不依赖这些旧文件。

| 现在的工具 | 参考过的项目代码 | 抽取内容 |
| --- | --- | --- |
| review_media.py / media_utils.py | work/cinematic/inventory.py、full_proxy_scan.py | PyAV 探测、带实际时间的关键帧；没有继承全量已审看的声明 |
| render_title.py | work/vlog/typefix_v20/build.py、v07_rebuild/render.py | CJK 共用基线、RGBA 管线、ProRes 4444 |
| render_route.py | work/vlog/v06_maps/render_maps_v06.py | 弧长采样、去重、朝向展开、固定车贴中心；位置保留原路线，不复用旧地图动态 exec |
| build_fcpxml.py | work/cinematic/build_deliverables.py、work/vlog/days_v14/xml/build_xml_v14.py | 有理时间、原片引用、真实包装/声音连接、CSV 和 DTD；明确增加非零源时码输入 |
| make_preview.py | work/vlog/typefix_v20/build.py、work/vlog/days_v14/make_light_preview.py | 手机兼容预览、原声窗口、独立交付检查 |

没有原样收进整个 work 目录：旧项目的镜头选择、Cyrus / Trinidad 顺序、人物身份/露脸例外、字体设计、车辆/地图美术和调色数值属于项目数据。旧版依赖链和私密站点脚本也没有搬入；通用包不携带素材、凭证、个人绝对路径、临时服务授权或大型视频。

这些是可执行的通用基础组件，并不声称自动完成审美决策、连续听审、转录、AI 角色生成、专业调色、完整 FCP 渲染或部署。五个阶段会根据当前项目调用组件，并为超出组件能力的编辑保存项目专用代码。
