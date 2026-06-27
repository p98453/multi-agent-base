---
name: validate_skill_update
description: 对更新后的Skill进行验证测试，确保进化有效且无副作用
agent_type: gateway
version: 1
parameters:
  updated_skill: dict - 更新后的Skill完整定义
  test_cases: list[dict] - 验证测试用例
  original_skill: dict - 原始Skill定义（对比基准）
  quality_threshold: float - 质量阈值 默认7.0
---