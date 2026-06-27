---
name: evaluate_quality
description: 对Agent输出进行多维度质量评估，判定是否满足用户需求，生成改进反馈
agent_type: gateway
version: 1
parameters:
  user_message: str - 用户原始消息
  agent_response: str - Agent输出内容
  agent_type: str - 处理该请求的Agent类型
  skill_chain: list[str] - 使用的技能链
  evaluation_rules: dict - 评估规则配置
---