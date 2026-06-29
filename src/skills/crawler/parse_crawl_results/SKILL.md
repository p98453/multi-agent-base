---

name: parse_crawl_results
description: 将爬取的原始数据解析清洗为结构化情报数据，提取关键字段，格式化输出
agent_type: crawler
version: 1
parameters:
  raw_data: "list[dict] - 爬取得到的原始数据"
  output_schema: dict - 期望输出的数据结构定义
  cleaning_rules: dict - 数据清洗规则配置
  enrichment_sources: "list[str] - 数据补全来源"

---