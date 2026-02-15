#!/usr/bin/env python3
"""
优化后的多智能体系统（Multi-Agent System）- 简化版（无RAG增强）

本模块是整个多智能体安全分析系统的核心协调器，负责：
1. 统一管理路由智能体（Router Agent）和多个专家智能体（Expert Agents）
2. 协调完整的分析流水线：路由决策 → 专家分析 → 结果综合
3. 提供系统级的日志记录和性能统计

处理流程：
  用户提交告警 → 路由智能体判断攻击类型 → 选择对应专家智能体 → 专家深度分析 → 返回综合结果

架构说明：
- MultiAgentSystem 是系统的唯一入口点，外部调用方（如 AgentService）只需与它交互
- 内部维护 1 个路由智能体 + 3 个专家智能体的实例池
- 使用 async/await 异步模型，支持高并发请求处理
"""
import time
import uuid
from typing import Dict, Any, Optional
from src.agents.optimized_router import OptimizedRouterAgent
from src.agents.optimized_expert import OptimizedExpertAgent
from src.utils.structured_logger import get_logger, reset_logger


class MultiAgentSystem:
    """多智能体协调系统 - 简化版
    
    系统组成：
    - router: OptimizedRouterAgent 实例，负责路由决策
    - experts: Dict[str, OptimizedExpertAgent]，三个领域专家的实例池
    - logger: StructuredLogger 实例，负责全链路日志记录
    
    生命周期：
    1. 创建实例（__init__）：仅初始化空属性，不执行耗时操作
    2. 异步初始化（initialize）：创建各智能体实例，标记系统就绪
    3. 分析告警（analyze）：执行完整的路由→分析→综合流程
    """
    
    def __init__(self):
        """构造函数 - 延迟初始化模式
        
        此处仅声明属性，不执行实际初始化。
        真正的初始化工作由 initialize() 异步方法完成。
        这种设计允许在异步上下文中进行初始化，同时保持构造函数的轻量级。
        """
        self.logger = None             # 结构化日志记录器，在 initialize() 中创建
        self.router = None             # 路由智能体实例
        self.experts = {}              # 专家智能体字典：{expert_type: OptimizedExpertAgent}
        self.is_initialized = False    # 系统初始化状态标志，防止未初始化就调用 analyze()
    
    async def initialize(self) -> bool:
        """异步初始化系统
        
        初始化流程：
        1. 重置全局日志记录器（每次初始化创建新的日志文件）
        2. 创建路由智能体实例
        3. 创建三个专家智能体实例（web_attack, vulnerability_attack, illegal_connection）
        4. 标记系统为已初始化状态
        
        Returns:
            bool: 初始化成功返回 True，异常时返回 False
        """
        try:
            print("\n" + "="*70)
            print("正在初始化多智能体系统...")
            print("="*70)
            
            # 重置全局日志记录器，创建新的日志会话
            # 每次系统初始化都会生成新的日志文件（以时间戳命名）
            self.logger = reset_logger()
            
            # 初始化路由智能体（负责分析告警类型并决定路由到哪个专家）
            self.router = OptimizedRouterAgent()
            print("[✓] 路由智能体已初始化")
            
            # 初始化三个领域专家智能体
            # 每个专家负责特定类型的安全威胁分析
            expert_types = ['web_attack', 'vulnerability_attack', 'illegal_connection']
            for expert_type in expert_types:
                self.experts[expert_type] = OptimizedExpertAgent(expert_type)
                print(f"[✓] {expert_type}专家智能体已初始化")
            
            # 标记系统初始化完成，允许后续的 analyze() 调用
            self.is_initialized = True
            
            print("="*70)
            print("✓ 多智能体系统初始化完成")
            print("="*70 + "\n")
            
            return True
            
        except Exception as e:
            print(f"[✗] 系统初始化失败: {e}")
            return False
    
    async def analyze(self, alert_data: Dict[str, Any], save_to_db: bool = False) -> Dict[str, Any]:
        """异步分析告警数据 - 完整处理链路（无RAG增强）
        
        这是多智能体系统的核心分析方法，执行以下三阶段流水线：
        
        阶段1 - 路由决策：
          路由智能体分析告警文本，确定攻击类别和路由置信度
        
        阶段2 - 专家分析：
          根据路由结果选择对应的专家智能体进行深度分析
          如果路由到的专家不存在，降级到 web_attack 专家
        
        阶段3 - 结果综合：
          合并路由信息和专家分析结果，附加性能指标，生成最终报告
        
        Args:
            alert_data: 告警数据字典，包含 attack_type, payload, source_ip 等字段
            save_to_db: 是否保存到数据库（当前简化版未使用，保留接口兼容）
            
        Returns:
            dict: 完整的分析结果，包含：
                - success (bool): 是否分析成功
                - task_id (str): 任务唯一标识（UUID）
                - timestamp (float): 时间戳
                - routing (dict): 路由决策信息（selected_route, confidence）
                - expert_analysis (dict): 专家分析结果（attack_technique, risk_score 等）
                - performance (dict): 性能指标（total_time_ms, routing_time_ms, expert_time_ms）
                
        Raises:
            RuntimeError: 系统未初始化时抛出异常
        """
        # 前置检查：确保系统已初始化
        if not self.is_initialized:
            raise RuntimeError("系统未初始化")
        
        overall_start = time.time()
        # 为每次分析任务生成唯一的任务ID（UUID v4）
        task_id = str(uuid.uuid4())
        
        print("\n" + "="*70)
        print(f"开始分析告警...任务ID: {task_id}")
        print("="*70)
        
        # 记录用户输入日志，包含任务ID、攻击类型和载荷预览（前100字符）
        self.logger.log("user_input", {
            "task_id": task_id,
            "attack_type": alert_data.get('attack_type', ''),
            "payload_length": len(alert_data.get('payload', '')),
            "payload_preview": alert_data.get('payload', '')[:100]  # 截断载荷，避免日志过大
        })
        
        # ==================== 阶段1：路由决策 ====================
        # 路由智能体分析告警文本，确定应由哪个专家处理
        print("\n[阶段1] 路由决策中...")
        routing_result = await self.router.route(alert_data)
        selected_route = routing_result['selected_route']
        print(f" → 路由到: {selected_route} (置信度: {routing_result['confidence']:.2f})")
        
        # ==================== 阶段2：专家分析 ====================
        # 根据路由结果获取对应的专家智能体
        print(f"\n[阶段2] 调用{selected_route}专家分析...")
        expert = self.experts.get(selected_route)
        if not expert:
            # 路由到了不存在的专家类型时，降级使用 web_attack 专家
            expert = self.experts['web_attack']
        
        # 调用专家的异步分析方法，进行深度威胁分析
        expert_result = await expert.analyze(alert_data)
        print(f"  → 分析完成: {expert_result.get('attack_technique', 'unknown')}")
        print(f"  → 风险评分: {expert_result.get('risk_score', 0)}/10")
        
        # ==================== 阶段3：综合结果 ====================
        # 计算整体分析耗时
        overall_time_ms = int((time.time() - overall_start) * 1000)
        
        # 构建最终分析结果，整合路由信息、专家分析和性能指标
        final_result = {
            'success': True,                    # 分析是否成功
            'task_id': task_id,                  # 任务唯一标识
            'timestamp': time.time(),            # 完成时间戳
            'routing': {                         # 路由决策信息
                'selected_route': selected_route,
                'confidence': routing_result['confidence']
            },
            'expert_analysis': {                 # 专家分析结果
                'attack_technique': expert_result.get('attack_technique', 'unknown'),
                'risk_score': expert_result.get('risk_score', 5.0),
                'threat_level': expert_result.get('threat_level', '中危'),
                'recommendations': expert_result.get('recommendations', []),
                'analysis': expert_result.get('analysis', '')
            },
            'performance': {                     # 性能指标
                'total_time_ms': overall_time_ms,                              # 总耗时
                'routing_time_ms': routing_result['processing_time_ms'],       # 路由阶段耗时
                'expert_time_ms': expert_result.get('processing_time_ms', 0),  # 专家分析阶段耗时
            }
        }
        
        # 记录最终分析结果日志
        self.logger.log("final_result", {
            "task_id": task_id,
            "attack_technique": final_result['expert_analysis']['attack_technique'],
            "risk_score": final_result['expert_analysis']['risk_score'],
            "threat_level": final_result['expert_analysis']['threat_level'],
            "total_processing_time_ms": overall_time_ms
        })
        
        print("\n" + "="*70)
        print(f"✓ 分析完成 (总耗时: {overall_time_ms}ms)")
        print("="*70 + "\n")
        
        return final_result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统运行统计信息
        
        返回日志记录器中累积的统计数据，包括总 token 消耗、总耗时、各阶段统计等。
        
        Returns:
            dict: 统计信息字典，无日志记录器时返回空字典
        """
        if self.logger:
            return self.logger.get_stats()
        return {}
    
    def save_logs(self) -> str:
        """保存当前会话的日志到文件
        
        将日志写入磁盘（JSONL 格式的主日志 + JSON 格式的会话摘要）。
        
        Returns:
            str: 日志文件路径，无日志记录器时返回空字符串
        """
        if self.logger:
            return self.logger.save()
        return ""
