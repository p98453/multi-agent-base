---

name: parse_channel_config
description: 解析用户的分发渠道需求，识别邮件收件人、抄送列表、多端分发目标渠道、定时规则等配置
agent_type: distribution
version: 1
parameters:
  recipients: "list[dict] - 收件人列表 [{email, name, role, channel_type}]"
  cc_list: "list[dict] - 抄送列表 [{email, name}]"
  channels: "list[str] - 分发渠道: email|sms|wechat_work|dingtalk|feishu|internal_system"
  subject_format: str - 邮件/通知标题格式模板
  body_format: "str - 正文格式: plain_text|html|markdown|rich_text"
  attachment_config: "dict - 附件配置 {include_original, formats}"
  schedule_config: "dict - 定时配置 {enabled, cron_expression, timezone, repeat}"
  reminder_rules: "list[dict] - 提醒规则 [{trigger_event, advance_days, repeat_interval_hours}]"
  priority: "str - 优先级: normal|important|urgent"

---