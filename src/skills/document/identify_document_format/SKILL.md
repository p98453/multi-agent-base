---

name: identify_document_format
description: 自动识别上传文档的格式类型（PDF、Word、Excel、HTML、扫描件、图片等），检测文档是否加密或损坏
agent_type: document
version: 1
parameters:
  file_path: str - 文档文件路径
  file_bytes: bytes - 文档二进制数据（可选）
  content_sniffing: bool - 是否启用内容嗅探深度识别
  ocr_required: bool - 是否需要OCR识别

---