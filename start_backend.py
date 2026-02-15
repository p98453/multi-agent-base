#!/usr/bin/env python3
"""
后端服务启动脚本（Backend Starter）

这是后端 FastAPI 服务的便捷启动入口。
运行方式：python start_backend.py

主要功能：
1. 将项目根目录添加到 Python 路径（确保模块导入正确）
2. 打印服务启动信息（地址、API文档、健康检查URL）
3. 使用 uvicorn 启动 FastAPI 应用

启动后可用的地址：
- API 服务: http://0.0.0.0:8000
- Swagger 文档: http://0.0.0.0:8000/docs
- 健康检查: http://0.0.0.0:8000/api/health
"""
import sys
import os

# 将项目根目录添加到 Python 的模块搜索路径
# 这样后续导入 backend.xxx 和 src.xxx 时能够正确找到模块
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    from backend.config import BackendConfig
    
    # 打印启动信息横幅
    print("=" * 60)
    print("🚀 启动多智能体安全分析系统后端服务")
    print("=" * 60)
    print(f"📍 地址: http://{BackendConfig.API_HOST}:{BackendConfig.API_PORT}")
    print(f"📚 API文档: http://{BackendConfig.API_HOST}:{BackendConfig.API_PORT}/docs")
    print(f"🏥 健康检查: http://{BackendConfig.API_HOST}:{BackendConfig.API_PORT}/api/health")
    print("=" * 60)
    
    # 使用 uvicorn（ASGI 服务器）启动 FastAPI 应用
    # "backend.main:app" 指定模块路径和应用实例名（backend/main.py 中的 app 变量）
    uvicorn.run(
        "backend.main:app",                         # ASGI 应用入口点
        host=BackendConfig.API_HOST,                 # 监听地址
        port=BackendConfig.API_PORT,                 # 监听端口
        reload=BackendConfig.API_RELOAD,             # 热重载：代码修改后自动重启（开发模式）
        log_level=BackendConfig.LOG_LEVEL.lower()    # 日志级别
    )
