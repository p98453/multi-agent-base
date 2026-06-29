---

name: format_data_table
description: 将结构化数据格式化为演示文稿中可用的数据表格，支持高亮、条件格式、排序
agent_type: presentation
version: 1
parameters:
  raw_data: "list[dict] - 原始数据"
  columns: "list[dict] - 列定义 [{field, header, width, format, alignment}]"
  table_style: "str - 表格风格: professional|compact|colorful|minimal"
  highlight_rules: dict - 高亮规则
  sort_config: dict - 排序配置

---