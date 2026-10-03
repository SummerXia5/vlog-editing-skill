# FCPXML 实施要点

1. 先识别用户 FCP 版本与可用格式支持，参考官方 DTD 或该版本实际导出的可导入 XML。不要凭记忆猜 effect UID、颜色校正参数、Motion 标题路径或 version。
2. 用 Fraction/整数帧处理所有时间；29.97 常为 30000/1001，不能用浮点累计 duration。区分序列 frameDuration、源帧率、音频采样和时间码显示模式；drop-frame 是显示计数规则。
3. 资源 start 保存媒体真实起点。asset-clip start 是源媒体时间域，主 storyline offset 是序列时间域，connected clip 的 offset 依父项时间域计算。零起点素材测试不能证明非零起点正确。
4. 源 IN/OUT 检查媒体边界与帧对齐。XML out 为排他边界。变速必须有可靠 timeMap 并核查声音；变速不能只改 duration。转场需要 handles 和重叠时长，不能重复累计。
5. 实拍引用原始源文件（MP4/MOV 等），URI 正确 percent-encode 空格、中文和特殊字符。只用于分析的 LRV 不允许成为交付资源。对原片设置 spatial conform/transform 前应用正确旋转解释，逐段核对构图。
6. 实际动画、音乐、SFX、补录旁白均需真实存在的资源。未生成的元素使用说明性 marker 并列入缺项，不标已完成。字体或 Motion 依赖写进交付说明；有可编辑与渲染替代版本时分别标明。
7. 保留单个镜头、声音 roles 和图形层的可编辑性。颜色无法可靠表达时附调色说明、LUT/参考渲染（如确已制作），明确 FCP 导入与外部预览的差异。
8. `check_fcpxml.py` 是辅助静态 lint，不能替代 DTD、时间域语义、素材 probe 和原生导入。离线磁盘缺失可用 `--allow-missing` 输出警告，但必须在交付中继续标为离线，而不是通过在线媒体检查。
9. 标准 CMX3600 EDL 不足以表达复杂多轨、图形与音频自动化。始终交付完整剪辑表；只有用户/下游需要时另附主轨 CMX EDL 并说明限制。不要把 CSV 命名成标准 EDL。
10. 重建脚本把路径、计划、媒体起点、目标格式放入输入 manifest 或参数，不硬编码个人用户名/挂载盘。输出到新版本，拒绝无意覆盖。实际执行一次并验证 XML 与 edit table 来自同一 manifest。
