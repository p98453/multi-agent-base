#!/usr/bin/env python3
"""
系统统计信息 API 路由

本模块定义了与系统状态相关的 RESTful API 端点：
1. GET /api/stats: 获取分析统计信息（威胁等级分布、攻击类型分布等）
2. GET /api/health: 健康检查端点（用于前端检测后端是否在线）
"""
from fastapi import APIRouter, HTTPException
from loguru import logger

from backend.api.models.schemas import SystemStats
from backend.services.agent_service import get_agent_service

# 创建路由器实例，统计相关端点也挂载在 /api 前缀下
router = APIRouter(prefix="/api", tags=["Statistics"])


@router.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """获取系统统计信息（GET /api/stats）
    
    从内存存储中汇总统计数据，包括：
    - 总分析次数
    - 威胁等级分布（高危/中危/低危各多少条）
    - 攻击类型分布（各种攻击类型的记录数）
    
    Returns:
        SystemStats: 系统统计数据
        
    Raises:
        HTTPException(500): 获取统计信息失败时返回服务器错误
    """
    try:
        service = get_agent_service()
        stats = service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.get("/health", response_model=dict)
async def health_check():
    """健康检查端点（GET /api/health）
    
    前端在加载时调用此端点检测后端服务是否正常运行。
    返回 200 状态码表示服务健康。
    
    Returns:
        dict: 包含服务状态、名称和版本的健康信息
    """
    return {
        "status": "healthy",
        "service": "multi-agent-security-analysis",
        "version": "1.0.0"
    }
