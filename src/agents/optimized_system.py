#!/usr/bin/env python3
"""
优化后的多智能体系统（Multi-Agent System）- LangGraph 重构版

本模块是整个多智能体安全分析系统的核心协调器，使用 LangGraph StateGraph
实现声明式的工作流编排，替代原有的过程式代码。

LangGraph 重构要点：
- 定义 AnalysisState（TypedDict）作为图的状态容器
- 将路由决策、专家分析、结果综合拆分为三个独立的图节点
- 使用 StateGraph 定义 START → route_node → expert_node → aggregate_node → END 的流转

处理流程（与重构前完全一致）：
  用户提交告警 → route_node(路由决策) → expert_node(专家分析) → aggregate_node(结果综合)
"""
import time
import uuid
from typing import Dict, Any, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END

from src.agents.optimized_router import OptimizedRouterAgent
from src.agents.optimized_expert import OptimizedExpertAgent
from src.utils.structured_logger import get_logger, reset_logger


# ==================== LangGraph 状态定义 ====================

class AnalysisState(TypedDict):
    """LangGraph 图的状态容器

    定义在图执行过程中各节点共享的数据结构。
    每个节点读取并更新状态中的特定字段。

    Fields:
        alert_data: 输入的告警数据字典
        task_id: 分析任务的唯一 ID（UUID）
        start_time: 任务开始时间戳
        routing_result: 路由节点的输出（selected_route, confidence, processing_time_ms）
        selected_route: 路由选择的专家类型
        expert_result: 专家分析节点的输出
        final_result: 综合结果节点的输出
    """
    alert_data: dict
    task_id: str
    start_time: float
    routing_result: dict
    selected_route: str
    expert_result: dict
    final_result: dict


class MultiAgentSystem:
    """多智能体协调系统 - LangGraph 重构版

    系统组成：
    - router: OptimizedRouterAgent 实例，负责路由决策
    - experts: Dict[str, OptimizedExpertAgent]，三个领域专家的实例池
    - graph: LangGraph StateGraph 编译后的图，定义完整的分析流程
    - logger: StructuredLogger 实例，负责全链路日志记录

    生命周期：
    1. 创建实例（__init__）：仅初始化空属性
    2. 异步初始化（initialize）：创建智能体实例 + 构建 LangGraph 图
    3. 分析告警（analyze）：调用 graph.ainvoke(state) 执行图
    """

    def __init__(self):
        """构造函数 - 延迟初始化模式"""
        self.logger = None
        self.router = None
        self.experts = {}
        self.graph = None              # LangGraph 编译后的可执行图
        self.is_initialized = False

    async def initialize(self) -> bool:
        """异步初始化系统

        初始化流程：
        1. 重置全局日志记录器
        2. 创建路由智能体实例
        3. 创建三个专家智能体实例
        4. 构建 LangGraph StateGraph 并编译
        5. 标记系统为已初始化状态

        Returns:
            bool: 初始化成功返回 True
        """
        try:
            print("\n" + "="*70)
            print("正在初始化多智能体系统（LangGraph 版）...")
            print("="*70)

            # 重置全局日志记录器
            self.logger = reset_logger()

            # 初始化路由智能体
            self.router = OptimizedRouterAgent()
            print("[✓] 路由智能体已初始化")

            # 初始化三个领域专家智能体
            expert_types = ['web_attack', 'vulnerability_attack', 'illegal_connection']
            for expert_type in expert_types:
                self.experts[expert_type] = OptimizedExpertAgent(expert_type)
                print(f"[✓] {expert_type}专家智能体已初始化")

            # 构建 LangGraph 状态图
            self.graph = self._build_graph()
            print("[✓] LangGraph 状态图已构建")

            self.is_initialized = True

            print("="*70)
            print("✓ 多智能体系统初始化完成（LangGraph 编排）")
            print("="*70 + "\n")

            return True

        except Exception as e:
            print(f"[✗] 系统初始化失败: {e}")
            return False

    def _build_graph(self):
        """构建 LangGraph StateGraph

        定义三个节点和线性流转路径：
        - route_node: 路由决策节点，分析告警类别
        - expert_node: 专家分析节点，执行深度分析
        - aggregate_node: 结果综合节点，整合所有结果

        图结构：
            START → route_node → expert_node → aggregate_node → END

        Returns:
            编译后的 LangGraph 可执行图
        """
        # 创建 StateGraph，指定状态类型
        graph_builder = StateGraph(AnalysisState)

        # 添加三个处理节点
        graph_builder.add_node("route_node", self._route_node)
        graph_builder.add_node("expert_node", self._expert_node)
        graph_builder.add_node("aggregate_node", self._aggregate_node)

        # 定义节点间的流转边
        graph_builder.set_entry_point("route_node")
        graph_builder.add_edge("route_node", "expert_node")
        graph_builder.add_edge("expert_node", "aggregate_node")
        graph_builder.add_edge("aggregate_node", END)

        # 编译图为可执行对象
        return graph_builder.compile()

    async def _route_node(self, state: AnalysisState) -> dict:
        """路由决策节点

        调用 OptimizedRouterAgent.route() 分析告警类别，
        将路由结果和选择的路由写入状态。

        Args:
            state: 当前图状态

        Returns:
            dict: 需要更新的状态字段
        """
        print("\n[阶段1] 路由决策中...")
        routing_result = await self.router.route(state["alert_data"])
        selected_route = routing_result['selected_route']
        print(f" → 路由到: {selected_route} (置信度: {routing_result['confidence']:.2f})")

        return {
            "routing_result": routing_result,
            "selected_route": selected_route,
        }

    async def _expert_node(self, state: AnalysisState) -> dict:
        """专家分析节点

        根据路由结果获取对应的专家智能体并执行深度分析。
        如果路由到了不存在的专家类型，降级使用 web_attack 专家。

        Args:
            state: 当前图状态

        Returns:
            dict: 需要更新的状态字段
        """
        selected_route = state["selected_route"]
        print(f"\n[阶段2] 调用{selected_route}专家分析...")

        expert = self.experts.get(selected_route)
        if not expert:
            expert = self.experts['web_attack']

        expert_result = await expert.analyze(state["alert_data"])
        print(f"  → 分析完成: {expert_result.get('attack_technique', 'unknown')}")
        print(f"  → 风险评分: {expert_result.get('risk_score', 0)}/10")

        return {
            "expert_result": expert_result,
        }

    async def _aggregate_node(self, state: AnalysisState) -> dict:
        """结果综合节点

        合并路由信息和专家分析结果，附加性能指标，生成最终报告。

        Args:
            state: 当前图状态

        Returns:
            dict: 需要更新的状态字段（final_result）
        """
        routing_result = state["routing_result"]
        expert_result = state["expert_result"]
        overall_time_ms = int((time.time() - state["start_time"]) * 1000)

        final_result = {
            'success': True,
            'task_id': state["task_id"],
            'timestamp': time.time(),
            'routing': {
                'selected_route': state["selected_route"],
                'confidence': routing_result['confidence']
            },
            'expert_analysis': {
                'attack_technique': expert_result.get('attack_technique', 'unknown'),
                'risk_score': expert_result.get('risk_score', 5.0),
                'threat_level': expert_result.get('threat_level', '中危'),
                'recommendations': expert_result.get('recommendations', []),
                'analysis': expert_result.get('analysis', '')
            },
            'performance': {
                'total_time_ms': overall_time_ms,
                'routing_time_ms': routing_result['processing_time_ms'],
                'expert_time_ms': expert_result.get('processing_time_ms', 0),
            }
        }

        # 记录最终分析结果日志
        self.logger.log("final_result", {
            "task_id": state["task_id"],
            "attack_technique": final_result['expert_analysis']['attack_technique'],
            "risk_score": final_result['expert_analysis']['risk_score'],
            "threat_level": final_result['expert_analysis']['threat_level'],
            "total_processing_time_ms": overall_time_ms
        })

        print("\n" + "="*70)
        print(f"✓ 分析完成 (总耗时: {overall_time_ms}ms)")
        print("="*70 + "\n")

        return {
            "final_result": final_result,
        }

    async def analyze(self, alert_data: Dict[str, Any], save_to_db: bool = False) -> Dict[str, Any]:
        """异步分析告警数据 - 通过 LangGraph 图执行

        使用 LangGraph 的 graph.ainvoke() 执行完整的分析流程，
        替代原有的过程式调用链。

        Args:
            alert_data: 告警数据字典
            save_to_db: 是否保存到数据库（保留接口兼容）

        Returns:
            dict: 完整的分析结果

        Raises:
            RuntimeError: 系统未初始化时抛出
        """
        if not self.is_initialized:
            raise RuntimeError("系统未初始化")

        task_id = str(uuid.uuid4())

        print("\n" + "="*70)
        print(f"开始分析告警...任务ID: {task_id}")
        print("="*70)

        # 记录用户输入日志
        self.logger.log("user_input", {
            "task_id": task_id,
            "attack_type": alert_data.get('attack_type', ''),
            "payload_length": len(alert_data.get('payload', '')),
            "payload_preview": alert_data.get('payload', '')[:100]
        })

        # 构建初始状态
        initial_state: AnalysisState = {
            "alert_data": alert_data,
            "task_id": task_id,
            "start_time": time.time(),
            "routing_result": {},
            "selected_route": "",
            "expert_result": {},
            "final_result": {},
        }

        # 通过 LangGraph 图执行完整分析流程
        final_state = await self.graph.ainvoke(initial_state)

        return final_state["final_result"]

    def get_stats(self) -> Dict[str, Any]:
        """获取系统运行统计信息"""
        if self.logger:
            return self.logger.get_stats()
        return {}

    def save_logs(self) -> str:
        """保存当前会话的日志到文件"""
        if self.logger:
            return self.logger.save()
        return ""
