---
name: generate_summary
description: 对文档内容进行智能摘要，根据用户需求决定摘要粒度（一句话/一段话/分级摘要/关键数据表）
agent_type: document
version: 1
parameters:
  document_content: str - 文档完整内容
  summary_level: str - 摘要级别: brief|standard|detailed|executive
  focus_aspects: list[str] - 重点关注方面
  language: str - 输出语言
  max_length: int - 摘要最大字数
---