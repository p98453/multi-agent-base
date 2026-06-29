---

name: compose_email
description: 根据系统产出内容自动撰写邮件正文，支持HTML/Markdown格式，智能生成邮件主题和正文布局
agent_type: distribution
version: 1
parameters:
  content_source: "dict - 系统产出内容 {type, data}"
  recipient_context: dict - 收件人上下文信息
  email_tone: "str - 邮件语气: formal|professional|casual|urgent"
  include_summary: bool - 是否在正文中包含内容摘要
  include_action_items: bool - 是否包含行动项/待办
  html_template: str - HTML邮件模板名称
  branding: "dict - 企业品牌信息 {logo_url, company_name, signature_template}"

---