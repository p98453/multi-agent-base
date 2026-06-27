---
name: compare_documents
description: 对多个文档进行横向对比分析，提取差异点和共同点，生成对比报告
agent_type: document
version: 1
parameters:
  document_list: list[dict] - 待对比文档列表 [{id, content, metadata}]
  compare_dimensions: list[str] - 对比维度: [预算, 工期, 资质, 技术, 评分]
  output_format: str - 输出格式: table|json|report
---