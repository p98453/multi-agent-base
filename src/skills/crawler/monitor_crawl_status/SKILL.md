---
name: monitor_crawl_status
description: 实时监控爬虫运行状态，异常检测与自动恢复，生成进度报告
agent_type: crawler
version: 1
parameters:
  execution_id: str - 爬虫执行ID
  alert_thresholds: dict - 告警阈值配置
  auto_recovery: bool - 是否启用自动恢复
---