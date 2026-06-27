---
name: parse_document_structure
description: 对文档进行结构化解析，提取标题层级、段落、表格、图片、目录结构等元素
agent_type: document
version: 1
parameters:
  file_path: str - 文档路径
  document_format: str - 已识别的文档格式
  parse_depth: str - 解析深度: basic|standard|deep
  extract_tables: bool - 是否提取表格
  extract_images: bool - 是否提取图片及OCR
  language: str - 文档语言
---