---
name: generate_comparison_slides
description: 自动生成竞品对比、方案对比、预算对比等对比类型的幻灯片，支持多维度可视化对比
agent_type: presentation
version: 1
parameters:
  comparison_data: dict - 对比数据 {entities: [], dimensions: [], values: [[]]}
  comparison_type: str - 对比类型: competitive|solution|budget|qualification
  visual_style: str - 视觉风格: table|radar|bar|matrix
---