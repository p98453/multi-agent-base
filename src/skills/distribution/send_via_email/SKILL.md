---
name: send_via_email
description: 通过企业邮箱SMTP/Exchange发送邮件，支持附件、抄送、密送、已读回执，记录发送状态
agent_type: distribution
version: 1
parameters:
  email_content: dict - compose_email的输出结果
  smtp_config: dict - SMTP/Exchange服务器配置 {host, port, username, password, use_tls, use_exchange}
  recipients: list[dict] - 收件人列表
  retry_config: dict - 重试配置 {max_retries: 3, retry_delay_seconds: 60}
  tracking: dict - 追踪配置 {read_receipt: bool, track_links: bool}
---