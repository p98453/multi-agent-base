---
name: match_template
description: 根据演示内容和受众，从模板库中智能匹配最合适的PPT模板，支持多模板风格适配
agent_type: presentation
version: 1
parameters:
  presentation_type: str - 演示类型
  audience: str - 目标受众
  style_preference: str - 风格偏好
  corporate_branding: dict - 企业品牌信息 {logo, colors, fonts}
  available_templates: list[dict] - 可用模板列表
---