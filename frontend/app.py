#!/usr/bin/env python3
"""
Streamlit 主应用 - 多智能体安全分析系统前端入口

本文件是 Streamlit 多页面应用的主页面（Home Page），负责：
1. 配置页面基本设置（标题、图标、布局）
2. 展示系统欢迎页和核心功能介绍
3. 在侧边栏显示后端连接状态和技术栈信息

Streamlit 多页面应用结构说明：
- 本文件（app.py）作为主入口和首页
- frontend/pages/ 目录下的文件自动注册为子页面
- 文件名格式「数字_emoji_名称.py」决定页面在侧边栏的排列顺序和显示名称
"""
import streamlit as st

# ==================== 页面配置 ====================
# 必须在所有 Streamlit 命令之前调用 set_page_config()
st.set_page_config(
    page_title="多智能体安全分析系统",      # 浏览器标签页标题
    page_icon="🛡️",                        # 浏览器标签页图标
    layout="wide",                          # 宽屏布局，充分利用屏幕空间
    initial_sidebar_state="expanded"        # 侧边栏默认展开
)

# ==================== 主页面内容 ====================
st.title("🛡️ 多智能体安全分析系统")
st.markdown("---")

# 系统介绍和功能说明（Markdown 格式）
st.markdown("""
### 欢迎使用多智能体网络安全威胁智能分析系统

本系统采用先进的多智能体架构，结合大语言模型技术，提供全方位的安全威胁分析能力。

#### 🌟 核心功能

**1. 🔍 告警分析**
- 智能路由决策，自动选择最合适的专家智能体
- 深度威胁分析，提供详细的攻击技术识别
- 多专家协同，覆盖Web攻击、漏洞利用、非法连接等场景

**2. 📊 分析历史**
- 完整的分析记录追溯
- 支持多维度过滤和搜索

**3.  系统仪表板**
- 实时统计信息
- 威胁趋势分析

#### 🚀 快速开始

请从左侧导航栏选择功能模块:

- **告警分析**: 提交新的安全告警进行分析
- **分析历史**: 查看历史分析记录
- **系统仪表板**: 查看系统统计和分析趋势

---

""")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("系统信息")
    
    # 动态导入：将项目根目录添加到 Python 路径
    # 这是因为 Streamlit 的工作目录可能不是项目根目录
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from frontend.utils.api_client import APIClient
    
    # 创建前端 API 客户端实例，连接到本地后端服务
    api_client = APIClient("http://localhost:8000")
    
    # 后端服务连接状态检测
    # 通过调用 /api/health 端点判断后端是否在线
    if api_client.health_check():
        st.success("✅ 后端服务已连接")
    else:
        st.error("❌ 后端服务未连接")
        st.info("请确保FastAPI后端服务正在运行: `python start_backend.py`")
    
    st.markdown("---")
    
    # 技术栈信息展示
    st.markdown("""
    **技术栈**
    - 🎯 Streamlit (前端)
    - ⚡ FastAPI (后端API)
    - 🤖 多智能体系统
    - 🧠 Qwen大语言模型
    """)
    
    st.markdown("---")
    st.caption("v1.0.0 | 多智能体安全分析系统")
