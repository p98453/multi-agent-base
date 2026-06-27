---
name: extract_structured_data
description: 从文档中提取结构化数据，包括表格数据、键值对、实体关系等，输出为结构化JSON/CSV格式
agent_type: document
version: 1
parameters:
  document_content: str - 文档内容
  extraction_schema: dict - 期望的数据提取Schema定义
  output_format: str - 输出格式: json|csv|excel|dict
  entity_types: list[str] - 需要提取的实体类型
---