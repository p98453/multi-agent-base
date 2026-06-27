import json
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.models.llm_factory import get_chat_llm
from src.utils.structured_logger import get_logger
from src.skills.skill_registry import get_skill_registry


class CrawlerAgent:
    def __init__(self):
        self.agent_type = "crawler"
        self.logger = get_logger()
        self.output_parser = StrOutputParser()
        self.skill_registry = get_skill_registry()
        self.skills = self.skill_registry.get_agent_skills("crawler")
        self.skill_chain_order = [
            "parse_crawler_intent",
            "match_crawler_script",
            "execute_crawl",
            "parse_crawl_results",
            "generate_crawl_report"
        ]

    async def handle(self, user_message: str, feedback: str = "", primary_skill: str = "", secondary_skills: list = None) -> dict:
        start_time = time.time()
        secondary_skills = secondary_skills or []
        skill_chain_used = []
        intermediate_results = {}

        try:
            llm = get_chat_llm()

            if not primary_skill:
                primary_skill = "parse_crawler_intent"

            actual_chain = self._build_skill_chain(primary_skill, secondary_skills)

            stage1_skill = actual_chain[0] if actual_chain else "parse_crawler_intent"
            skill1 = self.skills.get(stage1_skill, {})
            prompt1_text = skill1.get("prompt_template", "")
            if prompt1_text:
                prompt1 = ChatPromptTemplate.from_messages([("system", prompt1_text)])
                chain1 = prompt1 | llm | self.output_parser
                if feedback:
                    user_message = f"{user_message}\n\n[improvement feedback] previous issues: {feedback}\nplease improve based on this feedback."
                resp1 = await chain1.ainvoke({"user_message": user_message})
                intermediate_results[stage1_skill] = self._safe_parse_json(resp1)
                skill_chain_used.append(stage1_skill)

                for skill_name in actual_chain[1:]:
                    skill_def = self.skills.get(skill_name, {})
                    prompt_text = skill_def.get("prompt_template", "")
                    if prompt_text:
                        prompt_n = ChatPromptTemplate.from_messages([("system", prompt_text)])
                        chain_n = prompt_n | llm | self.output_parser
                        ctx = {
                            "parsed_params": json.dumps(intermediate_results.get(stage1_skill, {}), ensure_ascii=False),
                            "raw_data": json.dumps(intermediate_results, ensure_ascii=False),
                            "structured_data": json.dumps(intermediate_results, ensure_ascii=False),
                            "statistics": json.dumps(intermediate_results, ensure_ascii=False),
                            "script_config": json.dumps(intermediate_results, ensure_ascii=False),
                            "execution_id": "exec_sim_001",
                            "output_schema": json.dumps({}, ensure_ascii=False),
                            "user_message": user_message
                        }
                        resp_n = await chain_n.ainvoke(ctx)
                        intermediate_results[skill_name] = self._safe_parse_json(resp_n)
                        skill_chain_used.append(skill_name)

            final_response = self._format_crawler_response(intermediate_results, user_message, feedback)
        except Exception as e:
            self.logger.log("crawler_agent_error", {"error": str(e)})
            final_response = f"crawler agent error: {str(e)}"
            skill_chain_used = [primary_skill]

        processing_time_ms = int((time.time() - start_time) * 1000)
        self.logger.log("crawler_agent_response", {
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

    def _build_skill_chain(self, primary_skill: str, secondary_skills: list) -> list:
        chain = [primary_skill] if primary_skill in self.skills else []
        for s in secondary_skills:
            if s in self.skills and s not in chain:
                chain.append(s)
        if not chain:
            chain = ["parse_crawler_intent"]
        return chain

    def _safe_parse_json(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
            return json.loads(response)
        except (json.JSONDecodeError, ValueError):
            return {"raw_response": response[:500], "parse_status": "failed"}

    def _format_crawler_response(self, results: dict, user_message: str, feedback: str) -> str:
        parts = []

        intent = results.get("parse_crawler_intent", {})
        if intent:
            parts.append("## 需求解析")
            parts.append(f"- 目标平台: {intent.get('target_platforms', ['未识别'])}")
            parts.append(f"- 关键词: {intent.get('keywords', ['未识别'])}")
            parts.append(f"- 时间范围: {intent.get('date_range', {})}")
            parts.append(f"- 地域: {intent.get('region_filter', ['未指定'])}")
            parts.append(f"- 行业: {intent.get('industry_category', '未识别')}")
            parts.append(f"- 招标类型: {intent.get('bid_type', '未识别')}")
            clarification = intent.get("clarification_needed")
            if clarification and clarification != "null":
                parts.append(f"\n> 需要确认: {clarification}")
            parts.append("")

        script_match = results.get("match_crawler_script", {})
        if script_match:
            parts.append("## 脚本匹配")
            parts.append(f"- 主脚本: {script_match.get('primary_script', '未匹配')}")
            parts.append(f"- 匹配度: {script_match.get('match_score', 0):.0%}")
            parts.append(f"- 匹配理由: {script_match.get('match_reason', '')}")
            parts.append(f"- 执行策略: {script_match.get('execution_strategy', 'sequential')}")
            parts.append("")

        crawl_result = results.get("parse_crawl_results", {})
        if crawl_result:
            parts.append("## 爬取结果")
            parts.append(f"- 总记录数: {crawl_result.get('total_records', 0)}")
            parts.append(f"- 有效记录: {crawl_result.get('valid_records', 0)}")
            parts.append(f"- 去重记录: {crawl_result.get('duplicate_removed', 0)}")
            stats = crawl_result.get("statistics", {})
            if stats:
                parts.append(f"- 按类型分布: {json.dumps(stats.get('by_type', {}), ensure_ascii=False)}")
                parts.append(f"- 按地区分布: {json.dumps(stats.get('by_region', {}), ensure_ascii=False)}")
            parts.append(f"- 数据质量: {json.dumps(crawl_result.get('data_quality', {}), ensure_ascii=False)}")
            summary = crawl_result.get("summary", "")
            if summary:
                parts.append(f"\n{summary}")
            parts.append("")

        report = results.get("generate_crawl_report", {})
        if report:
            raw = report.get("raw_response", "")
            if raw:
                parts.append("## 情报分析报告")
                parts.append(raw)
            parts.append("")

        if not parts:
            parts.append("crawler agent processed your request. results are being compiled.")

        return "\n".join(parts)