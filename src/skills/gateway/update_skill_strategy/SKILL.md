---
name: update_skill_strategy
description: 根据根因分析结果自动生成Skill更新策略，生成新的Prompt模板和参数配置
agent_type: gateway
version: 1
parameters:
  analysis_result: dict - analyze_feedback的输出结果
  current_skill: dict - 当前Skill定义（prompt_template, parameters等）
  evolution_history: list[dict] - 该Skill的历史进化记录
---