#!/usr/bin/env python3
"""
前端服务启动脚本（Frontend Starter）

这是前端 Streamlit 应用的便捷启动入口。
运行方式：python start_frontend.py

主要功能：
1. 将项目根目录添加到 Python 路径
2. 打印启动提示信息
3. 使用 subprocess 调用 streamlit run 命令启动 Streamlit 应用

注意事项：
- 启动前请确保后端服务已运行（python start_backend.py）
- Streamlit 默认在浏览器中自动打开 http://localhost:8501
- 如果端口 8501 被占用，Streamlit 会自动选择下一个可用端口
"""
import sys
import os
import subprocess

# 将项目根目录添加到 Python 的模块搜索路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    # 打印启动信息横幅
    print("=" * 60)
    print("🎨 启动多智能体安全分析系统前端界面")
    print("=" * 60)
    print("📍 前端将在浏览器自动打开")
    print("💡 确保后端服务已启动: python start_backend.py")
    print("=" * 60)
    
    # 构建 Streamlit 入口文件的绝对路径
    frontend_app = os.path.join(project_root, "frontend", "app.py")
    
    # 使用 subprocess 启动 Streamlit 应用
    # sys.executable 确保使用当前 Python 解释器运行 streamlit 模块
    # -m streamlit run: 以模块方式运行 streamlit
    # --server.port=8501: 指定服务端口
    # --server.address=localhost: 仅监听本地连接
    subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        frontend_app,
        "--server.port=8501",
        "--server.address=localhost"
    ])
