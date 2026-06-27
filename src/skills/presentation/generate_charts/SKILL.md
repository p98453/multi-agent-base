---
name: generate_charts
description: 根据结构化数据自动生成可视化图表（柱状图、折线图、饼图、雷达图、热力图等），支持数据对比
agent_type: presentation
version: 1
parameters:
  chart_specs: list[dict] - 图表规格定义 [{type, data, config}]
  chart_theme: str - 图表主题: default|dark|professional|colorful
  chart_size: dict - 图表尺寸 {width, height}
  output_format: str - 输出格式: plotly_json|image_png|html
---