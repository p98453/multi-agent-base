import json
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.models.llm_factory import get_chat_llm
from src.utils.structured_logger import get_logger
from src.skills.skill_registry import get_skill_registry


class PresentationAgent:
    def __init__(self):
        self.agent_type = "presentation"
        self.logger = get_logger()
        self.output_parser = StrOutputParser()
        self.skill_registry = get_skill_registry()
        self.skills = self.skill_registry.get_agent_skills("presentation")

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

            final_response = self._format_presentation_response(intermediate_results, user_message, feedback)
        except Exception as e:
            self.logger.log("presentation_agent_error", {"error": str(e)})
            final_response = f"presentation agent error: {str(e)}"
            skill_chain_used = [primary_skill]

        processing_time_ms = int((time.time() - start_time) * 1000)
        self.logger.log("presentation_agent_response", {
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
        if any(kw in msg_lower for kw in ["图表", "chart", "可视化", "画图", "plot"]):
            return "generate_charts"
        if any(kw in msg_lower for kw in ["对比", "比较", "compare", "vs"]):
            return "generate_comparison_slides"
        if any(kw in msg_lower for kw in ["模板", "template", "风格"]):
            return "match_template"
        if any(kw in msg_lower for kw in ["导出", "下载", "export", "生成ppt", "ppt", "保存"]):
            return "export_presentation"
        if any(kw in msg_lower for kw in ["表格", "table", "数据表"]):
            return "format_data_table"
        return "organize_presentation_content"

    def _build_skill_chain(self, primary_skill: str, secondary_skills: list) -> list:
        chain = [primary_skill] if primary_skill in self.skills else []
        for s in secondary_skills:
            if s in self.skills and s not in chain:
                chain.append(s)
        if not chain:
            chain = ["organize_presentation_content", "generate_charts", "export_presentation"]
        return chain

    def _build_context(self, skill_name: str, user_message: str, results: dict) -> dict:
        ctx = {
            "user_message": user_message,
            "input_data": json.dumps(results, ensure_ascii=False),
            "presentation_type": "bid_report",
            "audience": "executive",
            "slide_count_target": "10",
            "style_preference": "professional",
            "corporate_branding": json.dumps({}, ensure_ascii=False),
            "chart_specs": json.dumps([], ensure_ascii=False),
            "chart_theme": "professional",
            "comparison_data": json.dumps(results, ensure_ascii=False),
            "comparison_type": "competitive",
            "visual_style": "radar",
            "template_name": "corporate_professional",
            "export_formats": "[\"pptx\"]",
            "slides_content": json.dumps(results, ensure_ascii=False),
            "raw_data": json.dumps([], ensure_ascii=False),
            "columns": json.dumps([], ensure_ascii=False),
            "table_style": "professional",
            "highlight_rules": json.dumps({}, ensure_ascii=False),
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

    def _format_presentation_response(self, results: dict, user_message: str, feedback: str) -> str:
        parts = []

        outline = results.get("organize_presentation_content", {})
        if outline:
            parts.append("## 演示文稿大纲")
            parts.append(f"- 标题: {outline.get('presentation_title', '未命名')}")
            parts.append(f"- 类型: {outline.get('presentation_type', '')}")
            parts.append(f"- 总页数: {outline.get('total_slides', 0)}")
            parts.append(f"- 预计时长: {outline.get('estimated_duration_minutes', 0)}分钟")
            parts.append("")
            slides = outline.get("slides", [])
            for slide in slides[:8]:
                parts.append(f"### 第{slide.get('slide_number', '?')}页: {slide.get('title', '')}")
                parts.append(f"- 类型: {slide.get('slide_type', '')}")
                parts.append(f"- 图表类型: {slide.get('chart_type', 'none')}")
                for pt in slide.get("key_points", [])[:3]:
                    parts.append(f"  - {pt}")
                parts.append("")
            if len(slides) > 8:
                parts.append(f"... 共{len(slides)}页")
                parts.append("")

        charts = results.get("generate_charts", {})
        if charts:
            parts.append("## 图表生成")
            for c in charts.get("charts", [])[:5]:
                parts.append(f"- [{c.get('chart_id', '?')}] {c.get('title', '')} ({c.get('chart_type', '')})")
                insights = c.get("insights", [])
                for ins in insights[:2]:
                    parts.append(f"  > {ins}")
            parts.append("")

        template = results.get("match_template", {})
        if template:
            parts.append("## 模板匹配")
            parts.append(f"- 首选模板: {template.get('primary_template', '')}")
            parts.append(f"- 综合匹配度: {template.get('overall_match', 0):.0%}")
            parts.append("")

        comparison = results.get("generate_comparison_slides", {})
        if comparison:
            parts.append("## 对比分析")
            parts.append(comparison.get("executive_summary", comparison.get("raw_response", "对比分析中...")))
            parts.append("")

        export = results.get("export_presentation", {})
        if export:
            parts.append("## 导出信息")
            parts.append(f"- 模板: {export.get('template_used', '')}")
            parts.append(f"- 页数: {export.get('total_slides', 0)}")
            files = export.get("files", [])
            for f in files:
                parts.append(f"- {f.get('format', '')}: {f.get('filename', '')} ({f.get('size_bytes', 0)} bytes)")
            parts.append("")

        if not parts:
            for k, v in results.items():
                raw = v.get("raw_response", "")
                if raw:
                    parts.append(f"## {k}")
                    parts.append(raw)
                    break

        if not parts:
            parts.append("presentation agent has processed your request. the PPT is being generated.")

        return "\n".join(parts)