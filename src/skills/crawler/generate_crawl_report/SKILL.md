---
name: generate_crawl_report
description: 根据采集和分析结果生成综合情报报告，包含数据概览、趋势分析、竞品分析和推荐行动
agent_type: crawler
version: 1
parameters:
  structured_data: list[dict] - 结构化情报数据
  statistics: dict - 统计数据
  report_format: str - 报告格式
  focus_areas: list[str] - 报告重点关注领域
---