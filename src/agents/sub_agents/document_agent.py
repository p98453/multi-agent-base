import json
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.models.llm_factory import get_chat_llm
from src.utils.structured_logger import get_logger
from src.skills.skill_registry import get_skill_registry


class DocumentAgent:
    def __init__(self):
        self.agent_type = "document"
        self.logger = get_logger()
        self.output_parser = StrOutputParser()
        self.skill_registry = get_skill_registry()
        self.skills = self.skill_registry.get_agent_skills("document")

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

            final_response = self._format_document_response(intermediate_results, user_message, feedback)
        except Exception as e:
            self.logger.log("document_agent_error", {"error": str(e)})
            final_response = f"document agent error: {str(e)}"
            skill_chain_used = [primary_skill]

        processing_time_ms = int((time.time() - start_time) * 1000)
        self.logger.log("document_agent_response", {
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
        if any(kw in msg_lower for kw in ["摘要", "总结", "概述", "summar"]):
            return "generate_summary"
        if any(kw in msg_lower for kw in ["提取", "结构化", "数据提取", "extract"]):
            return "extract_structured_data"
        if any(kw in msg_lower for kw in ["搜索", "检索", "查找", "search", "查询"]):
            return "semantic_search"
        if any(kw in msg_lower for kw in ["对比", "比较", "compare", "差异"]):
            return "compare_documents"
        if any(kw in msg_lower for kw in ["存储", "入库", "向量", "vector"]):
            return "vectorize_and_store"
        if any(kw in msg_lower for kw in ["格式", "识别", "identify"]):
            return "identify_document_format"
        return "parse_document_structure"

    def _build_skill_chain(self, primary_skill: str, secondary_skills: list) -> list:
        chain = [primary_skill] if primary_skill in self.skills else []
        for s in secondary_skills:
            if s in self.skills and s not in chain:
                chain.append(s)
        if not chain:
            chain = ["parse_document_structure", "generate_summary"]
        return chain

    def _build_context(self, skill_name: str, user_message: str, results: dict) -> dict:
        ctx = {
            "user_message": user_message,
            "file_path": "user_uploaded_document.pdf",
            "document_content": user_message[:3000],
            "document_format": "pdf",
            "document_metadata": json.dumps({}, ensure_ascii=False),
            "extraction_schema": json.dumps({}, ensure_ascii=False),
            "summary_level": "standard",
            "focus_aspects": "[]",
            "chunk_strategy": "semantic",
            "collection_name": "bid_documents",
            "query": user_message,
            "top_k": "5",
            "filters": "{}",
            "compare_dimensions": "[]",
            "document_list": json.dumps([], ensure_ascii=False),
            "parse_depth": "standard",
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

    def _format_document_response(self, results: dict, user_message: str, feedback: str) -> str:
        parts = []

        fmt = results.get("identify_document_format", {})
        if fmt:
            parts.append("## 文档识别")
            parts.append(f"- 格式: {fmt.get('detected_format', '未识别')}")
            parts.append(f"- 是否加密: {fmt.get('is_encrypted', False)}")
            parts.append(f"- 是否需要OCR: {fmt.get('ocr_required', False)}")
            parts.append(f"- 页数: {fmt.get('page_count', 0)}")
            parts.append("")

        struct = results.get("parse_document_structure", {})
        if struct:
            parts.append("## 文档结构解析")
            metadata = struct.get("metadata", {})
            if metadata:
                parts.append(f"- 标题: {metadata.get('title', '未识别')}")
                parts.append(f"- 页数: {metadata.get('pages', 0)}")
                parts.append(f"- 表格数: {metadata.get('tables', 0)}")
            parts.append("")

        summary = results.get("generate_summary", {})
        if summary:
            parts.append("## 文档摘要")
            parts.append(summary.get("summary_text", summary.get("raw_response", "摘要生成中...")))
            parts.append("")

        extracted = results.get("extract_structured_data", {})
        if extracted:
            parts.append("## 结构化数据提取")
            parts.append(f"- 置信度: {extracted.get('confidence_score', 0):.0%}")
            proj = extracted.get("project_info", {})
            if proj:
                parts.append(f"- 项目名称: {proj.get('project_name', '')}")
                parts.append(f"- 项目预算: {proj.get('project_budget', '')}万元")
            parties = extracted.get("parties", {})
            if parties:
                parts.append(f"- 采购单位: {parties.get('procuring_entity', {}).get('name', '')}")
            parts.append("")

        search = results.get("semantic_search", {})
        if search:
            parts.append("## 语义搜索结果")
            for r in search.get("results", [])[:5]:
                parts.append(f"- [{r.get('rank', '?')}] 相似度: {r.get('score', 0):.0%} | 来源: {r.get('source_document', '')}")
                parts.append(f"  {r.get('content', '')[:150]}...")
            parts.append("")

        compare = results.get("compare_documents", {})
        if compare:
            parts.append("## 文档对比分析")
            parts.append(compare.get("summary", compare.get("raw_response", "对比分析中...")))
            parts.append("")

        if not parts:
            for k, v in results.items():
                raw = v.get("raw_response", "")
                if raw:
                    parts.append(f"## {k}")
                    parts.append(raw)
                    break

        if not parts:
            parts.append("document agent has processed your request.")

        return "\n".join(parts)