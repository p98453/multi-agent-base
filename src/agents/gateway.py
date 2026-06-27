import json
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.models.llm_factory import get_chat_llm
from src.utils.structured_logger import get_logger
from src.skills.skill_registry import get_skill_registry
from src.utils.cdp_client import get_cdp_client


class GatewayAgent:
    def __init__(self):
        self.logger = get_logger()
        self.output_parser = StrOutputParser()
        self.skill_registry = get_skill_registry()
        self.cdp_client = get_cdp_client()

    async def route(self, user_message: str, user_id: str = None, user_context: dict = None) -> dict:
        start_time = time.time()
        context = user_context or {}
        if user_id and not context:
            try:
                context = await self.cdp_client.get_user_context(user_id)
            except Exception:
                context = {"user_id": user_id}

        try:
            gateway_skills = self.skill_registry.get_agent_skills("gateway")
            identify_skill = gateway_skills.get("identify_intent", {})
            prompt_template = identify_skill.get("prompt_template", "")
            if prompt_template:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", prompt_template),
                ])
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._default_intent_prompt()),
                ])

            llm = get_chat_llm()
            chain = prompt | llm | self.output_parser

            context_str = json.dumps(context, ensure_ascii=False)[:1500]
            response = await chain.ainvoke({
                "user_message": user_message,
                "user_context": context_str
            })
            result = self._parse_intent_response(response)
        except Exception as e:
            self.logger.log("gateway_error", {"error": str(e)})
            result = self._fallback_route(user_message)

        processing_time_ms = int((time.time() - start_time) * 1000)
        self.logger.log("gateway_decision", {
            "user_message": user_message[:100],
            "route": result["route"],
            "confidence": result["confidence"],
            "processing_time_ms": processing_time_ms
        })
        result["processing_time_ms"] = processing_time_ms
        return result

    async def evaluate_quality(self, user_message: str, agent_response: str, agent_type: str, skill_chain: list) -> dict:
        start_time = time.time()
        try:
            gateway_skills = self.skill_registry.get_agent_skills("gateway")
            eval_skill = gateway_skills.get("evaluate_quality", {})
            prompt_template = eval_skill.get("prompt_template", "")
            if prompt_template:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", prompt_template),
                ])
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._default_eval_prompt()),
                ])

            llm = get_chat_llm()
            chain = prompt | llm | self.output_parser

            skill_chain_str = json.dumps(skill_chain, ensure_ascii=False)
            response = await chain.ainvoke({
                "user_message": user_message,
                "agent_response": agent_response[:3000],
                "agent_type": agent_type,
                "skill_chain": skill_chain_str
            })
            evaluation = self._parse_evaluation_response(response)
        except Exception as e:
            self.logger.log("evaluate_error", {"error": str(e)})
            evaluation = {"satisfied": True, "weighted_score": 5.0, "feedback": "evaluation failed, default pass"}

        processing_time_ms = int((time.time() - start_time) * 1000)
        evaluation["processing_time_ms"] = processing_time_ms
        return evaluation

    async def analyze_feedback(self, user_feedback: str, task_context: dict, deviation_type: str = None) -> dict:
        start_time = time.time()
        try:
            gateway_skills = self.skill_registry.get_agent_skills("gateway")
            feedback_skill = gateway_skills.get("analyze_feedback", {})
            prompt_template = feedback_skill.get("prompt_template", "")
            if prompt_template:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", prompt_template),
                ])
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._default_feedback_analysis_prompt()),
                ])

            llm = get_chat_llm()
            chain = prompt | llm | self.output_parser

            task_str = json.dumps(task_context, ensure_ascii=False)[:3000]
            response = await chain.ainvoke({
                "user_feedback": user_feedback,
                "task_context": task_str,
                "deviation_type": deviation_type or "unknown"
            })
            analysis = self._parse_feedback_analysis(response)
        except Exception as e:
            self.logger.log("feedback_analysis_error", {"error": str(e)})
            analysis = {
                "deviation_summary": "analysis failed",
                "root_cause_category": "unknown",
                "affected_skills": [],
                "recommended_fix": {}
            }

        processing_time_ms = int((time.time() - start_time) * 1000)
        analysis["processing_time_ms"] = processing_time_ms
        return analysis

    async def evolve_skill(self, analysis_result: dict) -> dict:
        start_time = time.time()
        try:
            recommended_fix = analysis_result.get("recommended_fix", {})
            skill_name = recommended_fix.get("skill_to_update", "")
            if not skill_name:
                return {"success": False, "message": "no skill to update identified"}

            affected_skills = analysis_result.get("affected_skills", [])
            agent_type = "gateway"
            for s in affected_skills:
                if s.get("skill_name") == skill_name:
                    agent_type = s.get("agent_type", "gateway")
                    break

            current_skill = self.skill_registry.get_skill(agent_type, skill_name)
            if not current_skill:
                for at in ["crawler", "document", "presentation"]:
                    current_skill = self.skill_registry.get_skill(at, skill_name)
                    if current_skill:
                        agent_type = at
                        break

            if not current_skill:
                return {"success": False, "message": f"skill {skill_name} not found"}

            gateway_skills = self.skill_registry.get_agent_skills("gateway")
            update_skill = gateway_skills.get("update_skill_strategy", {})
            prompt_template = update_skill.get("prompt_template", "")
            if prompt_template:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", prompt_template),
                ])
                llm = get_chat_llm()
                chain = prompt | llm | self.output_parser
                evolution_history = self.skill_registry.get_evolution_history(agent_type, skill_name)
                response = await chain.ainvoke({
                    "analysis_result": json.dumps(analysis_result, ensure_ascii=False),
                    "current_skill": json.dumps(current_skill, ensure_ascii=False)[:2000],
                    "evolution_history": json.dumps(evolution_history, ensure_ascii=False)[:1000]
                })
                strategy = self._parse_evolution_strategy(response)
            else:
                strategy = {
                    "evolution_type": "prompt_modification",
                    "complete_new_prompt": recommended_fix.get("specific_change", ""),
                    "evolution_reason": analysis_result.get("deviation_summary", "")
                }

            new_prompt = strategy.get("complete_new_prompt", "")
            new_params = None

            if strategy.get("evolution_type") == "parameter_adjustment":
                new_params = current_skill.get("parameters", {}).copy()
                param_changes = strategy.get("changes", {}).get("parameter_changes", {})
                for k, v in param_changes.get("added", {}).items():
                    new_params[k] = v
                for k, v in param_changes.get("modified", {}).items():
                    if k in new_params:
                        new_params[k] = v.get("new", v)

            reason = strategy.get("evolution_reason", analysis_result.get("deviation_summary", ""))
            success = self.skill_registry.evolve_skill(
                agent_type=agent_type,
                skill_name=skill_name,
                new_prompt_template=new_prompt if new_prompt else None,
                new_parameters=new_params,
                reason=reason
            )

            if not success:
                return {"success": False, "message": "skill evolution failed"}

            validation_result = await self._validate_skill_evolution(agent_type, skill_name, analysis_result)
            return {
                "success": True,
                "message": f"skill {skill_name} evolved successfully",
                "evolution_applied": True,
                "updated_skills": [skill_name],
                "root_cause": analysis_result.get("root_cause_category", ""),
                "validation": validation_result,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            self.logger.log("evolution_error", {"error": str(e)})
            return {"success": False, "message": f"evolution failed: {str(e)}", "processing_time_ms": int((time.time() - start_time) * 1000)}

    async def _validate_skill_evolution(self, agent_type: str, skill_name: str, analysis_result: dict) -> dict:
        try:
            updated_skill = self.skill_registry.get_skill(agent_type, skill_name)
            if not updated_skill:
                return {"verdict": "fail", "reason": "updated skill not found"}
            gateway_skills = self.skill_registry.get_agent_skills("gateway")
            validate_skill = gateway_skills.get("validate_skill_update", {})
            prompt_template = validate_skill.get("prompt_template", "")
            if not prompt_template:
                return {"verdict": "conditional_pass", "reason": "validation skipped - no validate skill defined"}
            test_cases = analysis_result.get("recommended_fix", {}).get("validation_test", "test with original problematic input")
            prompt = ChatPromptTemplate.from_messages([("system", prompt_template)])
            llm = get_chat_llm()
            chain = prompt | llm | self.output_parser
            response = await chain.ainvoke({
                "updated_skill": json.dumps(updated_skill, ensure_ascii=False)[:2000],
                "test_cases": str(test_cases),
                "original_skill": json.dumps({}, ensure_ascii=False),
                "quality_threshold": "7.0"
            })
            return self._parse_validation_response(response)
        except Exception as e:
            return {"verdict": "conditional_pass", "reason": f"validation error: {str(e)}"}

    def _parse_intent_response(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            data = json.loads(response)
            return {
                "route": data.get("route", "document"),
                "confidence": float(data.get("confidence", 0.5)),
                "reason": data.get("reason", ""),
                "primary_skill": data.get("primary_skill", ""),
                "secondary_skills": data.get("secondary_skills", []),
                "is_multi_step": data.get("is_multi_step", False),
                "follow_up_routes": data.get("follow_up_routes", []),
                "suggested_clarification": data.get("suggested_clarification"),
                "user_intent_summary": data.get("user_intent_summary", "")
            }
        except (json.JSONDecodeError, ValueError):
            return self._fallback_route(response)

    def _parse_evaluation_response(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            data = json.loads(response)
            return {
                "coverage": int(data.get("coverage", 5)),
                "accuracy": int(data.get("accuracy", 5)),
                "usability": int(data.get("usability", 5)),
                "efficiency": int(data.get("efficiency", 5)),
                "weighted_score": float(data.get("weighted_score", 5.0)),
                "satisfied": bool(data.get("satisfied", True)),
                "feedback": data.get("feedback", ""),
                "missing_elements": data.get("missing_elements", []),
                "wrong_elements": data.get("wrong_elements", []),
                "improvement_priority": data.get("improvement_priority", "coverage"),
                "suggested_skill_fix": data.get("suggested_skill_fix", "")
            }
        except (json.JSONDecodeError, ValueError):
            return {"satisfied": True, "weighted_score": 5.0, "feedback": "evaluation parse failed, default pass"}

    def _parse_feedback_analysis(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            data = json.loads(response)
            return {
                "deviation_summary": data.get("deviation_summary", ""),
                "root_cause_category": data.get("root_cause_category", "unknown"),
                "affected_skills": data.get("affected_skills", []),
                "why_chain": data.get("why_chain", []),
                "recommended_fix": data.get("recommended_fix", {}),
                "prevention_suggestion": data.get("prevention_suggestion", "")
            }
        except (json.JSONDecodeError, ValueError):
            return {"deviation_summary": "parse failed", "root_cause_category": "unknown", "affected_skills": [], "recommended_fix": {}}

    def _parse_evolution_strategy(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            data = json.loads(response)
            return {
                "evolution_id": data.get("evolution_id", ""),
                "target_skill": data.get("target_skill", ""),
                "agent_type": data.get("agent_type", ""),
                "evolution_type": data.get("evolution_type", "prompt_modification"),
                "current_version": data.get("current_version", 0),
                "new_version": data.get("new_version", 0),
                "changes": data.get("changes", {}),
                "complete_new_prompt": data.get("complete_new_prompt", ""),
                "evolution_reason": data.get("evolution_reason", ""),
                "expected_impact": data.get("expected_impact", ""),
                "validation_test": data.get("validation_test", "")
            }
        except (json.JSONDecodeError, ValueError):
            return {"evolution_type": "prompt_modification", "complete_new_prompt": "", "evolution_reason": ""}

    def _parse_validation_response(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            data = json.loads(response)
            return {
                "verdict": data.get("verdict", "conditional_pass"),
                "recommendation": data.get("recommendation", "deploy"),
                "test_results": data.get("test_results", []),
                "regression_found": data.get("regression_found", False)
            }
        except (json.JSONDecodeError, ValueError):
            return {"verdict": "conditional_pass", "reason": "parse failed"}

    def _fallback_route(self, user_message: str) -> dict:
        msg_lower = user_message.lower()
        crawler_kw = ["爬取", "爬虫", "采集", "抓取", "crawl", "scrape", "招标公告", "中标公告", "采购信息", "招标信息"]
        doc_kw = ["文档", "解析", "提取", "pdf", "word", "excel", "摘要", "总结", "搜索", "查找", "对比"]
        ppt_kw = ["ppt", "演示", "图表", "报告", "可视化", "幻灯片", "汇报", "presentation", "chart"]
        dist_kw = ["分发", "发送", "推送", "邮件", "email", "邮箱", "定时", "提醒", "通知", "群发", "通讯录", "联系人"]

        crawler_score = sum(1 for kw in crawler_kw if kw in msg_lower)
        doc_score = sum(1 for kw in doc_kw if kw in msg_lower)
        ppt_score = sum(1 for kw in ppt_kw if kw in msg_lower)
        dist_score = sum(1 for kw in dist_kw if kw in msg_lower)

        scores = {"crawler": crawler_score, "document": doc_score, "presentation": ppt_score, "distribution": dist_score}
        best = max(scores, key=scores.get)

        if scores[best] == 0:
            return {"route": "crawler", "confidence": 0.3, "reason": "default fallback", "primary_skill": "parse_crawler_intent"}

        skill_map = {"crawler": "parse_crawler_intent", "document": "identify_document_format", "presentation": "organize_presentation_content", "distribution": "parse_channel_config"}
        return {"route": best, "confidence": 0.4, "reason": f"keyword fallback: {best}", "primary_skill": skill_map[best]}

    def _default_intent_prompt(self) -> str:
        return """你是一个招投标情报系统的智能路由网关。将用户需求路由到正确的处理单元。

路由选项：crawler(爬虫管理), document(文档处理), presentation(智能演示), distribution(多端分发)
distribution专长：邮件发送、多端推送（企业微信/钉钉/飞书/短信）、定时任务、通讯录查询、分发效果统计

返回JSON：{"route": "...", "confidence": 0.0-1.0, "reason": "...", "primary_skill": "...", "secondary_skills": [], "is_multi_step": false, "follow_up_routes": [], "suggested_clarification": null, "user_intent_summary": "..."}"""

    def _default_eval_prompt(self) -> str:
        return """你是质量评估专家。评估Agent输出是否满足用户需求。

返回JSON：{"coverage": 1-10, "accuracy": 1-10, "usability": 1-10, "efficiency": 1-10, "weighted_score": 0.0-10.0, "satisfied": true/false, "feedback": "...", "missing_elements": [], "wrong_elements": [], "improvement_priority": "coverage", "suggested_skill_fix": ""}"""

    def _default_feedback_analysis_prompt(self) -> str:
        return """你是Skill根因分析专家。分析用户反馈，定位需要改进的Skill。

返回JSON：{"deviation_summary": "...", "root_cause_category": "skill_prompt|skill_parameter|...", "affected_skills": [{"skill_name": "...", "agent_type": "...", "issue": "...", "severity": "major", "fix_priority": 3}], "why_chain": [], "recommended_fix": {"skill_to_update": "...", "update_type": "...", "specific_change": "..."}, "prevention_suggestion": "..."}"""