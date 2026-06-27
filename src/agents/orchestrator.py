import time
import uuid
import json
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.agents.gateway import GatewayAgent
from src.agents.sub_agents.crawler_agent import CrawlerAgent
from src.agents.sub_agents.document_agent import DocumentAgent
from src.agents.sub_agents.presentation_agent import PresentationAgent
from src.agents.sub_agents.distribution_agent import DistributionAgent
from src.models.llm_factory import get_chat_llm
from src.utils.structured_logger import get_logger, reset_logger
from src.skills.skill_registry import get_skill_registry, reset_skill_registry
from src.models.memory import get_memory_manager
from src.utils.cdp_client import get_cdp_client
from backend.config import BackendConfig


class ChatState(TypedDict):
    user_message: str
    user_id: str
    task_id: str
    start_time: float
    user_context: dict
    gateway_result: dict
    agent_result: dict
    evaluation: dict
    loop_count: int
    loop_history: list
    skill_chain: list
    final_result: dict


EVALUATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """you are a quality evaluator for a bid intelligence system.

evaluate the agent response against the user request.

criteria:
1. coverage (1-10): does the response cover all aspects
2. accuracy (1-10): is the data accurate
3. usability (1-10): is the output format usable
4. efficiency (1-10): is there unnecessary content

return JSON:
{
    "coverage": 1-10,
    "accuracy": 1-10,
    "usability": 1-10,
    "efficiency": 1-10,
    "weighted_score": 0.0-10.0,
    "satisfied": true/false,
    "feedback": "specific improvement feedback if not satisfied",
    "missing_elements": [],
    "wrong_elements": [],
    "improvement_priority": "coverage|accuracy|usability|efficiency",
    "suggested_skill_fix": ""
}"""),
    ("human", """user request: {user_message}
agent type: {agent_type}
skill chain: {skill_chain}
agent response: {response}
evaluate the response.""")
])


class MultiAgentOrchestrator:
    MAX_LOOPS = BackendConfig.MAX_LOOPS
    EVALUATION_THRESHOLD = BackendConfig.EVALUATION_THRESHOLD

    def __init__(self):
        self.logger = None
        self.gateway = None
        self.agents = {}
        self.graph = None
        self.output_parser = StrOutputParser()
        self.is_initialized = False
        self.skill_registry = None
        self.memory_manager = None
        self.cdp_client = None

    async def initialize(self) -> bool:
        try:
            print("\n" + "=" * 60)
            print("init bid intelligence multi-agent system...")
            print("=" * 60)

            self.logger = reset_logger()
            self.skill_registry = reset_skill_registry()
            self.memory_manager = get_memory_manager()
            self.cdp_client = get_cdp_client()

            self.gateway = GatewayAgent()
            print("[OK] gateway agent (intent + routing + quality + evolution)")

            self.agents = {
                "crawler": CrawlerAgent(),
                "document": DocumentAgent(),
                "presentation": PresentationAgent(),
                "distribution": DistributionAgent(),
            }
            print(f"[OK] crawler agent - {len(self.agents['crawler'].skills)} skills: {list(self.agents['crawler'].skills.keys())}")
            print(f"[OK] document agent - {len(self.agents['document'].skills)} skills: {list(self.agents['document'].skills.keys())}")
            print(f"[OK] presentation agent - {len(self.agents['presentation'].skills)} skills: {list(self.agents['presentation'].skills.keys())}")
            print(f"[OK] distribution agent - {len(self.agents['distribution'].skills)} skills: {list(self.agents['distribution'].skills.keys())}")

            self.graph = self._build_graph()
            print(f"[OK] langgraph loop graph (max_loop={self.MAX_LOOPS}, threshold={self.EVALUATION_THRESHOLD})")

            total_skills = len(self.skill_registry.list_all_skills())
            evolutions = len(self.skill_registry.get_evolution_history())
            print(f"[OK] skill registry - {total_skills} skills, {evolutions} evolutions")

            self.is_initialized = True
            print("=" * 60)
            print("bid intelligence multi-agent system ready")
            print("=" * 60 + "\n")
            return True

        except Exception as e:
            print(f"[FAIL] init failed: {e}")
            return False

    def _build_graph(self):
        graph_builder = StateGraph(ChatState)

        graph_builder.add_node("gateway_node", self._gateway_node)
        graph_builder.add_node("agent_node", self._agent_node)
        graph_builder.add_node("evaluate_node", self._evaluate_node)
        graph_builder.add_node("aggregate_node", self._aggregate_node)

        graph_builder.set_entry_point("gateway_node")
        graph_builder.add_edge("gateway_node", "agent_node")
        graph_builder.add_edge("agent_node", "evaluate_node")

        graph_builder.add_conditional_edges(
            "evaluate_node",
            self._should_loop,
            {
                "retry": "agent_node",
                "done": "aggregate_node",
            }
        )
        graph_builder.add_edge("aggregate_node", END)

        return graph_builder.compile()

    async def _gateway_node(self, state: ChatState) -> dict:
        print("\n[stage 1] intent recognition + routing...")
        user_id = state.get("user_id", "")
        user_context = state.get("user_context", {})
        gateway_result = await self.gateway.route(
            state["user_message"],
            user_id=user_id if user_id else None,
            user_context=user_context
        )
        route = gateway_result.get("route", "crawler")
        confidence = gateway_result.get("confidence", 0)
        print(f"  -> route: {route} (confidence: {confidence:.2f})")
        print(f"  -> primary skill: {gateway_result.get('primary_skill', '')}")
        print(f"  -> reason: {gateway_result.get('reason', '')}")
        if gateway_result.get("suggested_clarification"):
            print(f"  -> clarification: {gateway_result.get('suggested_clarification')}")

        skill_chain = [gateway_result.get("primary_skill", "")]
        skill_chain += gateway_result.get("secondary_skills", [])
        skill_chain = [s for s in skill_chain if s]

        return {
            "gateway_result": gateway_result,
            "skill_chain": skill_chain
        }

    async def _agent_node(self, state: ChatState) -> dict:
        route = state["gateway_result"].get("route", "crawler")
        loop_count = state.get("loop_count", 0)
        feedback = state.get("evaluation", {}).get("feedback", "")
        skill_chain = state.get("skill_chain", [])

        if loop_count > 0:
            print(f"\n[stage 2 - retry #{loop_count}] calling {route} agent with improvement feedback...")
        else:
            print(f"\n[stage 2] calling {route} agent...")

        agent = self.agents.get(route, self.agents["crawler"])
        primary_skill = skill_chain[0] if skill_chain else ""
        secondary_skills = skill_chain[1:] if len(skill_chain) > 1 else []

        agent_result = await agent.handle(
            state["user_message"],
            feedback=feedback,
            primary_skill=primary_skill,
            secondary_skills=secondary_skills
        )

        actual_skill_chain = agent_result.get("skill_chain", skill_chain)
        print(f"  -> skill chain: {actual_skill_chain}")
        print(f"  -> response length: {len(agent_result['response'])} chars")

        return {
            "agent_result": agent_result,
            "loop_count": loop_count + 1,
            "skill_chain": actual_skill_chain
        }

    async def _evaluate_node(self, state: ChatState) -> dict:
        loop_count = state.get("loop_count", 1)
        agent_type = state["gateway_result"].get("route", "crawler")
        skill_chain = state.get("skill_chain", [])
        print(f"\n[stage 3] quality evaluation... (round {loop_count})")

        try:
            evaluation = await self.gateway.evaluate_quality(
                state["user_message"],
                state["agent_result"]["response"],
                agent_type,
                skill_chain
            )
        except Exception as e:
            self.logger.log("evaluate_error", {"error": str(e)})
            llm = get_chat_llm()
            chain = EVALUATE_PROMPT | llm | self.output_parser
            try:
                resp = await chain.ainvoke({
                    "user_message": state["user_message"],
                    "response": state["agent_result"]["response"],
                    "agent_type": agent_type,
                    "skill_chain": json.dumps(skill_chain)
                })
                evaluation = self._parse_evaluation(resp)
            except Exception:
                evaluation = {"satisfied": True, "weighted_score": 5.0, "feedback": "evaluation failed, default pass"}

        status = "passed" if evaluation.get("satisfied", True) else "failed"
        weighted_score = evaluation.get("weighted_score", 0)
        print(f"  -> evaluation: {status} (score: {weighted_score:.1f})")
        if not evaluation.get("satisfied", True):
            print(f"  -> feedback: {evaluation.get('feedback', '')[:150]}")
            print(f"  -> missing: {evaluation.get('missing_elements', [])}")
            print(f"  -> suggested fix: {evaluation.get('suggested_skill_fix', '')}")

        loop_entry = {
            "loop": loop_count,
            "skill_chain": skill_chain,
            "evaluation": evaluation,
            "response_snippet": state["agent_result"]["response"][:200]
        }
        loop_history = state.get("loop_history", []) + [loop_entry]

        return {
            "evaluation": evaluation,
            "loop_history": loop_history
        }

    def _should_loop(self, state: ChatState) -> str:
        satisfied = state["evaluation"].get("satisfied", True)
        loop_count = state.get("loop_count", 0)

        if satisfied or loop_count >= self.MAX_LOOPS:
            if not satisfied and loop_count >= self.MAX_LOOPS:
                print(f"  [!] max loops ({self.MAX_LOOPS}) reached, forcing completion")
            return "done"
        else:
            print(f"  [loop] starting retry #{loop_count + 1}...")
            return "retry"

    async def _aggregate_node(self, state: ChatState) -> dict:
        overall_time_ms = int((time.time() - state["start_time"]) * 1000)
        print(f"\n[stage 4] aggregating results...")

        final_result = {
            "success": True,
            "task_id": state["task_id"],
            "timestamp": time.time(),
            "routing": {
                "route": state["gateway_result"].get("route", "crawler"),
                "confidence": state["gateway_result"].get("confidence", 0),
                "reason": state["gateway_result"].get("reason", ""),
                "user_intent_summary": state["gateway_result"].get("user_intent_summary", ""),
                "suggested_clarification": state["gateway_result"].get("suggested_clarification"),
            },
            "agent_info": {
                "agent_type": state["gateway_result"].get("route", "crawler"),
                "skill_used": state["agent_result"].get("skill_used", ""),
                "skill_chain": state.get("skill_chain", []),
                "loop_count": state.get("loop_count", 1),
            },
            "evaluation": {
                "satisfied": state["evaluation"].get("satisfied", True),
                "weighted_score": state["evaluation"].get("weighted_score", 0),
                "coverage": state["evaluation"].get("coverage", 0),
                "accuracy": state["evaluation"].get("accuracy", 0),
                "usability": state["evaluation"].get("usability", 0),
                "efficiency": state["evaluation"].get("efficiency", 0),
                "feedback": state["evaluation"].get("feedback", ""),
                "improvement_priority": state["evaluation"].get("improvement_priority", ""),
                "suggested_skill_fix": state["evaluation"].get("suggested_skill_fix", ""),
            },
            "response": state["agent_result"]["response"],
            "performance": {
                "total_time_ms": overall_time_ms,
                "gateway_time_ms": state["gateway_result"].get("processing_time_ms", 0),
                "agent_time_ms": state["agent_result"].get("processing_time_ms", 0),
            },
            "loop_history": state.get("loop_history", []),
            "skill_chain": state.get("skill_chain", []),
        }

        print(f"  [OK] aggregation complete (total: {overall_time_ms}ms)")
        print("=" * 60 + "\n")
        return {"final_result": final_result}

    async def chat(self, user_message: str, user_id: str = "", session_id: str = "", context: dict = None) -> dict:
        if not self.is_initialized:
            raise RuntimeError("system not initialized")

        task_id = str(uuid.uuid4())
        user_context = context or {}

        if user_id:
            try:
                memory = self.memory_manager.get_user_memory(user_id)
                memory.add_conversation("user", user_message, {"task_id": task_id})
                cdp_context = await self.cdp_client.get_user_context(user_id)
                user_context.update(cdp_context)
            except Exception:
                pass

        print("\n" + "=" * 60)
        print(f"user message | task: {task_id} | user: {user_id}")
        print(f"content: {user_message[:150]}{'...' if len(user_message) > 150 else ''}")
        print("=" * 60)

        self.logger.log("user_input", {
            "task_id": task_id,
            "user_id": user_id,
            "user_message": user_message[:200]
        })

        initial_state: ChatState = {
            "user_message": user_message,
            "user_id": user_id,
            "task_id": task_id,
            "start_time": time.time(),
            "user_context": user_context,
            "gateway_result": {},
            "agent_result": {},
            "evaluation": {},
            "loop_count": 0,
            "loop_history": [],
            "skill_chain": [],
            "final_result": {},
        }

        final_state = await self.graph.ainvoke(initial_state)
        result = final_state["final_result"]

        if user_id:
            try:
                memory = self.memory_manager.get_user_memory(user_id)
                memory.add_conversation("assistant", result["response"][:500], {"task_id": task_id})
                memory.add_task_record(task_id, result)
            except Exception:
                pass

        return result

    async def process_feedback(self, user_feedback: str, task_id: str, user_id: str = "", deviation_type: str = None, rating: int = None) -> dict:
        task_context = {}
        if user_id:
            try:
                memory = self.memory_manager.get_user_memory(user_id)
                for task in memory.task_history:
                    if task.get("task_id") == task_id:
                        task_context = {
                            "task_id": task_id,
                            "route": task.get("route", ""),
                            "skill_chain": task.get("skill_chain", []),
                            "summary": task.get("summary", ""),
                            "score": task.get("score", 0),
                        }
                        break
            except Exception:
                pass

        analysis = await self.gateway.analyze_feedback(
            user_feedback,
            task_context,
            deviation_type
        )

        evolution_result = {"success": False, "message": "evolution disabled"}
        if BackendConfig.EVOLUTION_ENABLED:
            try:
                evolution_result = await self.gateway.evolve_skill(analysis)
            except Exception as e:
                evolution_result = {"success": False, "message": f"evolution error: {str(e)}"}

        if user_id:
            try:
                memory = self.memory_manager.get_user_memory(user_id)
                affected_skills = analysis.get("affected_skills", [])
                for s in affected_skills:
                    memory.record_skill_feedback(s.get("skill_name", ""), user_feedback, rating or 5)
            except Exception:
                pass

        return {
            "success": True,
            "task_id": task_id,
            "analysis": {
                "deviation_summary": analysis.get("deviation_summary", ""),
                "root_cause_category": analysis.get("root_cause_category", ""),
                "affected_skills": analysis.get("affected_skills", []),
                "why_chain": analysis.get("why_chain", []),
                "prevention_suggestion": analysis.get("prevention_suggestion", ""),
            },
            "evolution": {
                "applied": evolution_result.get("success", False) or evolution_result.get("evolution_applied", False),
                "updated_skills": evolution_result.get("updated_skills", []),
                "root_cause": evolution_result.get("root_cause", ""),
                "validation": evolution_result.get("validation", {}),
                "message": evolution_result.get("message", ""),
            }
        }

    def _parse_evaluation(self, response: str) -> dict:
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
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

    def get_stats(self) -> dict:
        if self.logger:
            return self.logger.get_stats()
        return {}

    def get_skills(self) -> list:
        return self.skill_registry.list_all_skills()

    def get_evolution_history(self, agent_type: str = None, skill_name: str = None) -> list:
        return self.skill_registry.get_evolution_history(agent_type, skill_name)

    def save_logs(self) -> str:
        if self.logger:
            return self.logger.save()
        return ""