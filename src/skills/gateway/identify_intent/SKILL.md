---

name: identify_intent
description: 对用户输入进行多维度意图分类，识别用户需要调用哪个Agent及具体Skill组合
agent_type: gateway
version: 1
parameters:
  user_message: str - 用户原始消息
  user_context: dict - 用户上下文（历史对话、偏好、CRM数据）
  available_routes: "list[str] - 可用路由列表"

---