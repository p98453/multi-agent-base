#!/usr/bin/env python3
"""
FastAPI 主应用入口 - 简化版（无RAG增强）

本模块是多智能体安全分析系统的后端服务入口，基于 FastAPI 框架构建。

主要职责：
1. 创建和配置 FastAPI 应用实例
2. 管理应用生命周期（启动时初始化智能体服务，关闭时清理资源）
3. 配置 CORS 中间件（允许前端跨域访问）
4. 注册 API 路由（分析路由 + 统计路由）
5. 提供根端点（服务信息）

请求处理流程：
  前端（Streamlit） → FastAPI 路由 → AgentService → MultiAgentSystem → 路由/专家智能体
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from backend.config import BackendConfig
from backend.api.routes import analysis, stats
from backend.services.agent_service import get_agent_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器（异步上下文管理器）
    
    FastAPI 的 lifespan 机制替代了旧版的 @app.on_event("startup") / @app.on_event("shutdown")。
    使用 yield 分隔启动逻辑和关闭逻辑：
    - yield 之前的代码在应用启动时执行（初始化）
    - yield 之后的代码在应用关闭时执行（清理）
    
    启动流程：
    1. 验证后端配置（检查 API Key 等必需项）
    2. 初始化智能体服务（创建路由智能体和专家智能体）
    
    关闭流程：
    - 记录关闭日志（当前无需特殊清理操作）
    
    Args:
        app: FastAPI 应用实例
    """
    # ===== 启动阶段 =====
    logger.info("正在启动FastAPI服务...")

    # 步骤1: 验证配置项是否完整
    try:
        BackendConfig.validate()
        logger.info("配置验证通过")
    except ValueError as e:
        logger.error(f"配置验证失败: {e}")
        raise   # 配置缺失时直接终止启动

    # 步骤2: 初始化智能体服务（单例模式）
    # 这会创建 MultiAgentSystem 并初始化所有智能体
    try:
        service = get_agent_service()
        await service.initialize()      # 异步初始化：创建路由智能体 + 3个专家智能体
        logger.info("✓ 智能体服务初始化完成")
    except Exception as e:
        logger.error(f"智能体服务初始化失败: {e}")
        raise

    logger.info("✓ FastAPI服务启动完成")

    yield   # 应用运行中...

    # ===== 关闭阶段 =====
    logger.info("FastAPI服务正在关闭...")


# ==================== 创建 FastAPI 应用实例 ====================
app = FastAPI(
    title="多智能体安全分析系统 API",                           # API 文档标题
    description="基于多智能体架构的网络安全威胁智能分析系统",      # API 文档描述
    version="1.0.0",                                           # API 版本号
    lifespan=lifespan                                          # 绑定生命周期管理器
)

# ==================== 配置 CORS 中间件 ====================
# CORS（跨域资源共享）允许前端从不同端口/域名访问后端 API
# 这对于 Streamlit（8501端口）调用 FastAPI（8000端口）是必需的
app.add_middleware(
    CORSMiddleware,
    allow_origins=BackendConfig.CORS_ORIGINS,     # 允许的来源列表（前端地址）
    allow_credentials=True,                        # 允许携带 Cookie
    allow_methods=["*"],                           # 允许所有 HTTP 方法（GET, POST 等）
    allow_headers=["*"],                           # 允许所有请求头
)

# ==================== 注册 API 路由 ====================
# 将分析路由和统计路由注册到应用
# 路由前缀在各自的文件中定义（均为 /api）
app.include_router(analysis.router)     # /api/analyze, /api/history
app.include_router(stats.router)        # /api/stats, /api/health


@app.get("/")
async def root():
    """根端点 - 返回服务基本信息
    
    访问 http://localhost:8000/ 可查看服务状态和常用 URL。
    
    Returns:
        dict: 服务名称、版本、文档地址和健康检查地址
    """
    return {
        "service": "多智能体安全分析系统",
        "version": "1.0.0",
        "docs": "/docs",               # Swagger UI 自动生成的 API 文档
        "health": "/api/health"         # 健康检查端点
    }


# ==================== 直接运行入口 ====================
# 当直接运行 python backend/main.py 时启动服务（一般使用 start_backend.py 启动）
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",                         # 应用模块路径
        host=BackendConfig.API_HOST,                 # 监听地址
        port=BackendConfig.API_PORT,                 # 监听端口
        reload=BackendConfig.API_RELOAD,             # 热重载开关
        log_level=BackendConfig.LOG_LEVEL.lower()    # 日志级别
    )
