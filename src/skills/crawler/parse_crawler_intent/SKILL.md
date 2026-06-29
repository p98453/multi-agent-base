---

name: parse_crawler_intent
description: 将用户自然语言需求解析为结构化爬取参数，包括目标平台、关键词、时间范围、地域限制、行业分类等
agent_type: crawler
version: 1
parameters:
  target_platforms: "list[str] - 目标爬取平台列表"
  keywords: "list[str] - 搜索关键词列表"
  date_range: "dict - 时间范围 {start, end}"
  region_filter: "list[str] - 地域过滤"
  industry_category: str - 行业分类
  bid_type: str - 招标类型
  budget_range: "dict - 预算范围 {min, max}"
  data_format: str - 期望输出格式
  max_results: int - 最大采集条数
  dedup_strategy: str - 去重策略

---