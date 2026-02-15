#!/usr/bin/env python3
"""
分析相关 API 路由 - 简化版（无RAG增强）

本模块定义了与安全告警分析相关的 RESTful API 端点：
1. POST /api/analyze: 提交告警数据进行智能分析
2. GET /api/history: 获取分析历史记录（支持过滤和分页）

所有路由都挂载在 /api 前缀下，由 FastAPI 的 APIRouter 管理。
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from loguru import logger

from backend.api.models.schemas import AlertData, AnalysisResult, AnalysisHistory
from backend.services.agent_service import get_agent_service

# 创建路由器实例，设置 URL 前缀和 Swagger 文档标签
router = APIRouter(prefix="/api", tags=["Analysis"])


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_alert(alert_data: AlertData):
    """分析安全告警（POST /api/analyze）

    接收前端提交的告警数据，调用多智能体系统进行智能分析。
    
    处理流程：
    1. 接收并验证请求数据（Pydantic 自动完成）
    2. 获取智能体服务单例
    3. 调用异步分析方法（路由决策 → 专家分析）
    4. 返回完整的分析结果
    
    Args:
        alert_data: 经 Pydantic 验证的告警数据（AlertData 模型）
        
    Returns:
        AnalysisResult: 完整的分析结果，包含路由信息、专家分析和性能指标
        
    Raises:
        HTTPException(500): 分析过程中发生异常时返回服务器错误
    """
    try:
        logger.info(f"收到分析请求: {alert_data.attack_type}")

        # 获取全局智能体服务实例（单例模式）
        service = get_agent_service()
        # 调用异步分析方法，内部会执行：路由决策 → 专家分析 → 结果综合
        result = await service.analyze_alert(alert_data)

        logger.info(f"分析完成: {alert_data.attack_type}")
        return result

    except Exception as e:
        logger.error(f"分析失败: {e}")
        # 返回 500 状态码和错误详情
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/history", response_model=List[AnalysisHistory])
async def get_analysis_history(
    limit: int = 50,
    offset: int = 0,
    threat_level: Optional[str] = None,
    attack_type: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
):
    """获取分析历史记录（GET /api/history）
    
    从内存存储中查询分析历史，支持多维度过滤和分页。
    
    Query 参数说明：
    - limit: 返回的最大记录数（默认 50）
    - offset: 分页偏移量（默认 0，即从头开始）
    - threat_level: 按威胁等级过滤（如 "高危"、"中危"、"低危"）
    - attack_type: 按攻击类型过滤（如 "SQL注入"、"XSS攻击"）
    - start_time: 起始时间戳过滤
    - end_time: 结束时间戳过滤
    
    Returns:
        List[AnalysisHistory]: 符合条件的历史记录列表
        
    Raises:
        HTTPException(500): 查询失败时返回服务器错误
    """
    try:
        service = get_agent_service()
        # 将查询参数传递给存储层进行过滤
        history = service.get_analysis_history(
            limit=limit,
            offset=offset,
            threat_level=threat_level,
            attack_type=attack_type,
            start_time=start_time,
            end_time=end_time
        )
        return history

    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")
