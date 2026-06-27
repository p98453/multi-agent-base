---
name: analyze_feedback
description: 当用户指出偏差时，分析反馈内容，定位根因（具体哪个Skill的哪个环节出了问题），使用5Why分析法
agent_type: gateway
version: 1
parameters:
  user_feedback: str - 用户反馈文本
  task_context: dict - 原始任务上下文（请求、路由、使用的Skill链、输出）
  deviation_type: str - 偏差类型提示
---