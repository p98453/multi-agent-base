---

name: export_presentation
description: 将生成的演示文稿导出为多种格式（PPTX、PDF、HTML、图片集），支持下载和在线预览
agent_type: presentation
version: 1
parameters:
  slides_content: "list[dict] - 幻灯片内容列表"
  template_name: str - 使用的模板名称
  export_formats: "list[str] - 导出格式: [pptx, pdf, html, images]"
  include_speaker_notes: bool - 是否包含演讲备注
  include_data_appendix: bool - 是否包含数据附录
  watermark: str - 水印文字（可选）

---