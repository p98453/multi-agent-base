---

name: organize_presentation_content
description: 将招投标情报数据组织为演示文稿的结构化大纲，规划幻灯片内容、顺序和逻辑流
agent_type: presentation
version: 1
parameters:
  input_data: dict - 输入的情报数据（结构化数据+统计+分析结果）
  presentation_type: "str - 演示类型: bid_report|competitive_analysis|project_proposal|executive_briefing"
  audience: "str - 目标受众: executive|sales|technical|government"
  slide_count_target: int - 目标幻灯片数量
  style_preference: "str - 风格偏好: professional|concise|visual|detailed"

---