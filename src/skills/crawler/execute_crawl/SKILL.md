---
name: execute_crawl
description: 执行匹配到的爬虫脚本，管理爬取全生命周期：启动、监控、重试、结果收集
agent_type: crawler
version: 1
parameters:
  script_name: str - 要执行的爬虫脚本名称
  script_config: dict - 脚本执行配置参数
  execution_strategy: str - 执行策略
  retry_config: dict - 重试配置
  rate_limit: dict - 速率限制
  proxy_config: dict - 代理配置
---