#!/usr/bin/env python3
"""
智能体服务层 - 简化版（无RAG增强）

本模块是后端的核心服务层，位于 API 路由层和多智能体系统之间，起到「桥接」作用：
- 向上：为 API 路由提供业务方法（analyze_alert, get_analysis_history, get_stats）
- 向下：调用 MultiAgentSystem 执行实际的智能分析
- 横向：与 MemoryStorage 协作，管理分析结果的持久化

职责分离：
- API 路由层（routes/）：只负责 HTTP 协议相关逻辑（参数校验、响应格式化、错误处理）
- 服务层（本模块）：负责业务编排逻辑（数据转换、调用智能体、保存结果）
- 智能体层（src/agents/）：负责核心分析算法（路由决策、LLM 调用、规则匹配）

设计模式：单例模式 + 工厂函数
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from src.agents.optimized_system import MultiAgentSystem
from backend.services.memory_storage import get_memory_storage
from backend.api.models.schemas import AlertData, AnalysisResult


class AgentService:
    """智能体服务管理器
    
    封装多智能体系统的调用逻辑，提供面向 API 的业务接口。
    同时管理分析结果的内存存储。
    """
    
    def __init__(self):
        """初始化服务管理器
        
        此处仅创建属性引用，实际的智能体初始化由 initialize() 方法完成。
        - system: MultiAgentSystem 实例（延迟初始化）
        - storage: MemoryStorage 实例（立即获取单例）
        - is_initialized: 初始化状态标志
        """
        self.system: Optional[MultiAgentSystem] = None
        self.storage = get_memory_storage()    # 获取内存存储单例
        self.is_initialized = False
        
    async def initialize(self):
        """初始化智能体系统（异步方法）
        
        创建并初始化 MultiAgentSystem，内部会依次初始化
        路由智能体和三个专家智能体。
        
        幂等性：如果已经初始化过，直接跳过，避免重复初始化。
        """
        if self.is_initialized:
            logger.info("智能体服务已初始化,跳过")
            return
            
        try:
            logger.info("开始初始化智能体服务...")
            
            # 创建多智能体系统并执行异步初始化
            self.system = MultiAgentSystem()
            await self.system.initialize()     # 内部创建路由智能体 + 3个专家智能体
            
            self.is_initialized = True
            logger.info("✓ 智能体服务初始化完成")
            
        except Exception as e:
            logger.error(f"智能体服务初始化失败: {e}")
            raise
    
    async def analyze_alert(self, alert_data: AlertData) -> AnalysisResult:
        """分析安全告警（异步方法）- 核心业务方法
        
        完整的处理流程：
        1. 将 Pydantic 模型（AlertData）转换为普通字典（智能体系统使用字典接口）
        2. 调用 MultiAgentSystem.analyze() 执行完整的路由→分析→综合流程
        3. 将分析结果保存到内存存储（生成 analysis_id）
        4. 将字典结果转换为 Pydantic 模型（AnalysisResult）返回给路由层
        
        Args:
            alert_data: Pydantic 验证后的告警数据
            
        Returns:
            AnalysisResult: 结构化的分析结果（Pydantic 模型）
            
        Raises:
            RuntimeError: 服务未初始化时抛出
        """
        if not self.is_initialized:
            raise RuntimeError("智能体服务未初始化")
        
        logger.info(f"收到分析请求: {alert_data.attack_type}")
        
        # 步骤1: 将 Pydantic 模型转换为字典
        # MultiAgentSystem 使用字典接口，这里做数据格式转换
        alert_dict = {
            'attack_type': alert_data.attack_type,
            'payload': alert_data.payload,
            'source_ip': alert_data.source_ip,
            'dest_ip': alert_data.dest_ip,
            'protocol': alert_data.protocol,
            'additional_info': alert_data.additional_info or {}
        }
        
        # 步骤2: 调用多智能体系统执行分析
        # save_to_db=False 表示不使用数据库存储（当前使用内存存储替代）
        result = await self.system.analyze(alert_dict, save_to_db=False)
        
        # 步骤3: 将分析结果保存到内存存储
        # save_analysis() 返回 analysis_id，用于后续历史记录查询
        analysis_id = self.storage.save_analysis(alert_dict, result)
        result['analysis_id'] = analysis_id
        
        # 步骤4: 将字典结果转换为 Pydantic AnalysisResult 模型
        # 这确保响应数据完全符合 API 的 Schema 定义
        analysis_result = AnalysisResult(
            success=result.get('success', True),
            task_id=result.get('task_id'),
            analysis_id=analysis_id,
            timestamp=result.get('timestamp'),
            routing=result.get('routing'),
            expert_analysis=result.get('expert_analysis'),
            performance=result.get('performance'),
            message="分析完成"
        )
        
        logger.info(f"分析完成: {analysis_id}")
        return analysis_result
    
    def get_analysis_history(
        self,
        limit: int = 50,
        offset: int = 0,
        threat_level: Optional[str] = None,
        attack_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """获取分析历史记录
        
        直接委托给 MemoryStorage 进行过滤和分页查询。
        
        Args:
            limit: 最大返回记录数
            offset: 分页偏移量
            threat_level: 按威胁等级过滤
            attack_type: 按攻击类型过滤
            start_time: 起始时间戳过滤
            end_time: 结束时间戳过滤
            
        Returns:
            List[Dict]: 符合条件的历史记录列表
        """
        return self.storage.get_history(
            limit=limit,
            offset=offset,
            threat_level=threat_level,
            attack_type=attack_type,
            start_time=start_time,
            end_time=end_time
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息
        
        委托给 MemoryStorage 计算威胁等级分布和攻击类型分布。
        
        Returns:
            dict: 包含 total_analyses, threat_level_distribution, attack_type_distribution
        """
        return self.storage.get_stats()


# ==================== 全局单例管理 ====================
_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """获取智能体服务单例（工厂函数）
    
    整个应用共享同一个 AgentService 实例，确保：
    - MultiAgentSystem 只初始化一次
    - MemoryStorage 中的数据在所有请求间共享
    
    Returns:
        AgentService: 全局唯一的服务实例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = AgentService()
    return _service_instance
