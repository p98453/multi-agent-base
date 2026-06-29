---

name: match_crawler_script
description: 根据解析后的结构化参数自动匹配最合适的预置爬虫脚本，评估脚本适配度并确定执行策略
agent_type: crawler
version: 1
parameters:
  parsed_params: dict - 从parse_crawler_intent获取的结构化参数
  available_scripts: "list[dict] - 可用爬虫脚本清单及能力描述"
  match_threshold: float - 匹配度阈值 默认0.6
  fallback_strategy: str - 备选策略

---