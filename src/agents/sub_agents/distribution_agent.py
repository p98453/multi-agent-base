import json
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.models.llm_factory import get_chat_llm
from src.utils.structured_logger import get_logger
from src.skills.skill_registry import get_skill_registry


class DistributionAgent:
    def __init__(self):
        self.agent_type = "distribution"
        self.logger = get_logger()
        self.output_parser = StrOutputParser()
        self.skill_registry = get_skill_registry()
        self.skills = self.skill_registry.get_agent_skills("distribution")

    async def handle(self, user_message: str, feedback: str = "", primary_skill: str = "", secondary_skills: list = None) -> dict:
        start_time = time.time()
        secondary_skills = secondary_skills or []
        skill_chain_used = []
        intermediate_results = {}

        try:
            llm = get_chat_llm()

            if not primary_skill:
                primary_skill = self._infer_primary_skill(user_message)

            actual_chain = self._build_skill_chain(primary_skill, secondary_skills)

            for i, skill_name in enumerate(actual_chain):
                skill_def = self.skills.get(skill_name, {})
                prompt_text = skill_def.get("prompt_template", "")
                if not prompt_text:
                    continue

                prompt = ChatPromptTemplate.from_messages([("system", prompt_text)])
                chain = prompt | llm | self.output_parser

                if i == 0 and feedback:
                    user_message = f"{user_message}\n\n[improvement feedback] previous issues: {feedback}\nplease improve based on this feedback."

                ctx = self._build_context(skill_name, user_message, intermediate_results)
                resp = await chain.ainvoke(ctx)
                intermediate_results[skill_name] = self._safe_parse_json(resp)
                skill_chain_used.append(skill_name)

            final_response = self._format_distribution_response(intermediate_results, user_message, feedback)
        except Exception as e:
            self.logger.log("distribution_agent_error", {"error": str(e)})
            final_response = f"distribution agent error: {str(e)}"
            skill_chain_used = [primary_skill]

        processing_time_ms = int((time.time() - start_time) * 1000)
        self.logger.log("distribution_agent_response", {
            "user_message": user_message[:100],
            "skill_chain": skill_chain_used,
            "response_length": len(final_response),
            "processing_time_ms": processing_time_ms
        })

        return {
            "response": final_response,
            "skill_used": "|".join(skill_chain_used),
            "skill_chain": skill_chain_used,
            "intermediate_results": {k: str(v)[:200] for k, v in intermediate_results.items()},
            "processing_time_ms": processing_time_ms
        }

    def _infer_primary_skill(self, user_message: str) -> str:
        msg_lower = user_message.lower()
        if any(kw in msg_lower for kw in ["发送报告", "分发统计", "效果", "统计", "report"]):
            return "generate_distribution_report"
        if any(kw in msg_lower for kw in ["定时", "计划任务", "schedule", "cron", "自动发送", "周期"]):
            return "manage_schedule"
        if any(kw in msg_lower for kw in ["通讯录", "联系人", "地址簿", "邮箱地址", "查找邮箱", "查询"]):
            return "query_address_book"
        if any(kw in msg_lower for kw in ["多端", "多渠道", "推送", "push", "全渠道", "群发", "广播"]):
            return "push_to_channels"
        if any(kw in msg_lower for kw in ["邮件", "email", "发送", "发邮件", "send"]):
            return "compose_email"
        if any(kw in msg_lower for kw in ["配置", "设置", "分发到", "分发", "收件人", "抄送"]):
            return "parse_channel_config"
        return "parse_channel_config"

    def _build_skill_chain(self, primary_skill: str, secondary_skills: list) -> list:
        chain = [primary_skill] if primary_skill in self.skills else []
        for s in secondary_skills:
            if s in self.skills and s not in chain:
                chain.append(s)
        if not chain:
            chain = ["parse_channel_config", "compose_email", "send_via_email"]
        return chain

    def _build_context(self, skill_name: str, user_message: str, results: dict) -> dict:
        ctx = {
            "user_message": user_message,
            "content_source": json.dumps(results, ensure_ascii=False),
            "recipient_context": json.dumps(results.get("parse_channel_config", {}), ensure_ascii=False),
            "email_tone": "professional",
            "smtp_config": json.dumps({"host": "smtp.company.com", "port": 587, "use_tls": True, "use_exchange": False}, ensure_ascii=False),
            "recipients": json.dumps(results.get("parse_channel_config", {}).get("recipients", []), ensure_ascii=False),
            "email_content": json.dumps(results.get("compose_email", {}), ensure_ascii=False),
            "content": json.dumps(results, ensure_ascii=False),
            "channels": json.dumps(["email", "wechat_work", "dingtalk"], ensure_ascii=False),
            "channel_configs": json.dumps({}, ensure_ascii=False),
            "schedule_action": "list",
            "task_config": json.dumps({}, ensure_ascii=False),
            "task_id": "",
            "timezone": "Asia/Shanghai",
            "distribution_records": json.dumps([], ensure_ascii=False),
            "report_period": json.dumps({"start": "", "end": ""}, ensure_ascii=False),
            "metrics": json.dumps(["delivery_rate", "open_rate"], ensure_ascii=False),
            "query": user_message,
            "query_type": "fuzzy",
            "source": "both",
            "max_results": "10",
        }
        for k, v in results.items():
            ctx[k] = json.dumps(v, ensure_ascii=False)
        return ctx

    def _safe_parse_json(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
            return json.loads(response)
        except (json.JSONDecodeError, ValueError):
            return {"raw_response": response[:500], "parse_status": "failed"}

    def _format_distribution_response(self, results: dict, user_message: str, feedback: str) -> str:
        parts = []

        config = results.get("parse_channel_config", {})
        if config:
            parts.append("## 分发配置解析")
            parts.append(f"- 渠道: {config.get('channels', ['未指定'])}")
            recipients = config.get("recipients", [])
            if recipients:
                parts.append(f"- 收件人({len(recipients)}人): {', '.join(r.get('name', r.get('email', '?')) for r in recipients[:5])}")
            cc = config.get("cc_list", [])
            if cc:
                parts.append(f"- 抄送({len(cc)}人): {', '.join(r.get('name', r.get('email', '?')) for r in cc[:5])}")
            schedule = config.get("schedule_config", {})
            if schedule.get("enabled"):
                parts.append(f"- 定时: cron={schedule.get('cron_expression', '')} repeat={schedule.get('repeat', '')}")
            reminder = config.get("reminder_rules", [])
            if reminder:
                parts.append(f"- 提醒规则: {len(reminder)}条")
            clarification = config.get("clarification_needed")
            if clarification and clarification != "null":
                parts.append(f"\n> need confirm: {clarification}")
            parts.append("")

        email = results.get("compose_email", {})
        if email:
            parts.append("## 邮件撰写")
            parts.append(f"- 主题: {email.get('subject', '未生成')}")
            parts.append(f"- 预计阅读时间: {email.get('estimated_read_time_minutes', 0)}分钟")
            highlights = email.get("key_highlights", [])
            if highlights:
                parts.append("- 关键要点:")
                for h in highlights[:5]:
                    parts.append(f"  - {h}")
            actions = email.get("action_items", [])
            if actions:
                parts.append("- 行动项:")
                for a in actions[:5]:
                    parts.append(f"  - [{a.get('deadline', '')}] {a.get('action', '')} -> {a.get('assignee_role', '')}")
            parts.append("")

        send = results.get("send_via_email", {})
        if send:
            parts.append("## 邮件发送")
            parts.append(f"- 状态: {send.get('status', 'unknown')}")
            parts.append(f"- 成功: {send.get('success_count', 0)}/{send.get('total_recipients', 0)}")
            failed = send.get("failed_recipients", [])
            if failed:
                parts.append(f"- 失败({len(failed)}): {', '.join(f.get('email', '?') for f in failed[:3])}")
            parts.append("")

        push = results.get("push_to_channels", {})
        if push:
            parts.append("## 多端推送")
            parts.append(f"- 状态: {push.get('status', 'unknown')}")
            parts.append(f"- 成功渠道: {push.get('total_success', 0)}")
            parts.append(f"- 失败渠道: {push.get('total_failed', 0)}")
            channel_results = push.get("channel_results", {})
            for ch, cr in channel_results.items():
                icon = "OK" if cr.get("status") == "sent" else "FAIL"
                parts.append(f"  - [{icon}] {ch}")
            parts.append("")

        schedule = results.get("manage_schedule", {})
        if schedule:
            parts.append("## 定时任务")
            parts.append(f"- 操作: {schedule.get('operation', '')}")
            parts.append(f"- 任务: {schedule.get('task_name', '')}")
            parts.append(f"- 状态: {schedule.get('status', '')}")
            parts.append(f"- 下次执行: {schedule.get('next_run', '')}")
            parts.append(f"- 执行统计: 成功{schedule.get('success_count', 0)}/失败{schedule.get('failure_count', 0)}")
            active = schedule.get("active_tasks", [])
            if active:
                parts.append("- 活跃任务:")
                for t in active[:5]:
                    parts.append(f"  - [{t.get('status', '')}] {t.get('name', '')} -> next: {t.get('next_run', '')}")
            parts.append("")

        report = results.get("generate_distribution_report", {})
        if report:
            parts.append("## 分发效果报告")
            summary = report.get("summary", {})
            parts.append(f"- 总发送: {summary.get('total_sends', 0)}")
            parts.append(f"- 送达率: {summary.get('overall_delivery_rate', 0):.1%}")
            parts.append(f"- 打开率: {summary.get('overall_open_rate', 0):.1%}")
            findings = summary.get("key_findings", [])
            if findings:
                parts.append("- 关键发现:")
                for f in findings:
                    parts.append(f"  - {f}")
            recommendations = report.get("recommendations", [])
            if recommendations:
                parts.append("- 优化建议:")
                for r in recommendations[:5]:
                    parts.append(f"  - [{r.get('priority', '')}] {r.get('action', '')}")
            parts.append("")

        addr = results.get("query_address_book", {})
        if addr:
            parts.append("## 通讯录查询")
            parts.append(f"- 查询: {addr.get('query', '')}")
            parts.append(f"- 匹配: {addr.get('total_matches', 0)}人")
            for r in addr.get("results", [])[:8]:
                parts.append(f"  - {r.get('name', '')} | {r.get('email', '')} | {r.get('department', '')} | {r.get('position', '')}")
            missing = addr.get("missing_contacts", [])
            if missing:
                parts.append(f"- 未找到: {', '.join(m.get('name', '?') for m in missing)}")
            parts.append("")

        if not parts:
            for k, v in results.items():
                raw = v.get("raw_response", "")
                if raw:
                    parts.append(f"## {k}")
                    parts.append(raw)
                    break

        if not parts:
            parts.append("distribution agent has processed your request. the content is ready for delivery.")

        return "\n".join(parts)