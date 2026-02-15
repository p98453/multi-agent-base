#!/usr/bin/env python3
"""
内存存储服务（Memory Storage）- 替代 ChromaDB 的轻量方案

本模块提供基于 Python 列表的内存存储，用于保存和查询分析历史记录。
相比 ChromaDB 等向量数据库，这是一个更轻量的实现，适用于开发和演示场景。

特点：
- 纯内存存储，无外部依赖（不需要数据库服务）
- 支持多维度过滤（威胁等级、攻击类型、时间范围）
- 支持分页查询
- 自动限制历史记录大小（最多 100 条，防止内存溢出）
- 服务重启后数据会丢失（如需持久化，可替换为数据库实现）

设计模式：单例模式 + 工厂函数
"""
from typing import Dict, List, Any, Optional
import time
from loguru import logger


class MemoryStorage:
    """内存存储服务 - 简化版历史记录存储
    
    使用 Python 列表存储分析记录，新记录插入到列表头部（最新的在前）。
    当记录数超过 max_history_size 时，自动丢弃最旧的记录。
    """
    
    def __init__(self):
        """初始化内存存储
        
        创建空的历史记录列表和配置最大存储容量。
        """
        self.analysis_history: List[Dict[str, Any]] = []    # 分析历史记录列表（最新的在前）
        self.max_history_size = 100                          # 最大保存记录数，超过后自动淘汰旧记录
        logger.info("内存存储服务已初始化")
    
    def save_analysis(self, alert_data: Dict[str, Any], result: Dict[str, Any]) -> str:
        """保存一条分析结果到内存存储
        
        从告警数据和分析结果中提取关键字段，创建精简的历史记录并保存。
        新记录插入到列表头部（index=0），确保按时间倒序排列。
        
        自动容量管理：当记录数超过 max_history_size 时，截断列表丢弃最旧的记录。
        
        Args:
            alert_data: 原始告警数据字典
            result: 多智能体系统的完整分析结果字典
            
        Returns:
            str: 分析记录 ID（使用 task_id，如果不存在则使用时间戳毫秒数）
        """
        # 提取分析记录 ID：优先使用 task_id，否则用当前时间戳的毫秒数
        analysis_id = result.get('task_id', str(int(time.time() * 1000)))
        
        # 创建历史记录条目，包含原始数据和分析结果的引用
        record = {
            'analysis_id': analysis_id,
            'timestamp': result.get('timestamp', time.time()),
            'alert_data': alert_data,                                                    # 保存原始告警数据的引用
            'result': result,                                                            # 保存完整分析结果的引用
            'attack_type': alert_data.get('attack_type', ''),                           # 冗余存储，方便过滤查询
            'threat_level': result.get('expert_analysis', {}).get('threat_level', ''),   # 冗余存储
            'risk_score': result.get('expert_analysis', {}).get('risk_score', 0)         # 冗余存储
        }
        
        # 新记录插入到列表头部（index=0），保持按时间倒序排列
        self.analysis_history.insert(0, record)
        
        # 自动容量管理：超过最大容量时，丢弃尾部（最旧的）记录
        if len(self.analysis_history) > self.max_history_size:
            self.analysis_history = self.analysis_history[:self.max_history_size]
        
        logger.info(f"分析记录已保存: {analysis_id}")
        return analysis_id
    
    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        threat_level: Optional[str] = None,
        attack_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """获取分析历史记录（支持过滤和分页）
        
        过滤流程（链式过滤）：
        1. 先按威胁等级过滤（如果指定）
        2. 再按攻击类型过滤（如果指定）
        3. 再按起始时间过滤（如果指定）
        4. 再按结束时间过滤（如果指定）
        5. 最后按 offset 和 limit 进行分页截取
        
        Args:
            limit: 返回的最大记录数（默认 50）
            offset: 分页偏移量（默认 0）
            threat_level: 威胁等级过滤值（如 "高危"）
            attack_type: 攻击类型过滤值（如 "SQL注入"）
            start_time: 起始时间戳（Unix 时间戳，只返回此时间之后的记录）
            end_time: 结束时间戳（Unix 时间戳，只返回此时间之前的记录）
            
        Returns:
            List[Dict]: 符合条件的历史记录列表（已分页）
        """
        # 从全量数据开始，逐步应用过滤条件
        filtered = self.analysis_history
        
        # 按威胁等级过滤
        if threat_level:
            filtered = [r for r in filtered if r.get('threat_level') == threat_level]
        
        # 按攻击类型过滤
        if attack_type:
            filtered = [r for r in filtered if r.get('attack_type') == attack_type]
        
        # 按起始时间过滤（只保留时间戳 >= start_time 的记录）
        if start_time:
            filtered = [r for r in filtered if r.get('timestamp', 0) >= start_time]
        
        # 按结束时间过滤（只保留时间戳 <= end_time 的记录）
        if end_time:
            filtered = [r for r in filtered if r.get('timestamp', 0) <= end_time]
        
        # 分页：使用列表切片实现 offset + limit 分页
        result = filtered[offset:offset + limit]
        
        logger.info(f"查询历史记录: 共{len(filtered)}条, 返回{len(result)}条")
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息
        
        遍历所有历史记录，统计：
        - 总分析次数
        - 威胁等级分布（各等级的记录数量）
        - 攻击类型分布（各攻击类型的记录数量）
        
        Returns:
            dict: 统计信息字典，当无历史记录时返回空分布
        """
        # 无数据时返回空统计
        if not self.analysis_history:
            return {
                'total_analyses': 0,
                'threat_level_distribution': {},
                'attack_type_distribution': {}
            }
        
        # 遍历所有记录，统计威胁等级和攻击类型的频次
        threat_levels = {}      # {"高危": 5, "中危": 3, ...}
        attack_types = {}       # {"SQL注入": 4, "XSS攻击": 2, ...}
        
        for record in self.analysis_history:
            # 统计威胁等级分布
            level = record.get('threat_level', '未知')
            threat_levels[level] = threat_levels.get(level, 0) + 1
            
            # 统计攻击类型分布
            atype = record.get('attack_type', '未知')
            attack_types[atype] = attack_types.get(atype, 0) + 1
        
        return {
            'total_analyses': len(self.analysis_history),
            'threat_level_distribution': threat_levels,
            'attack_type_distribution': attack_types
        }


# ==================== 全局单例管理 ====================
_storage_instance: Optional[MemoryStorage] = None


def get_memory_storage() -> MemoryStorage:
    """获取内存存储单例（工厂函数）
    
    确保整个应用共享同一个 MemoryStorage 实例，
    所有分析结果保存在同一个列表中。
    
    Returns:
        MemoryStorage: 全局唯一的内存存储实例
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = MemoryStorage()
    return _storage_instance
