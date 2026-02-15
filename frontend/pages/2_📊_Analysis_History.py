#!/usr/bin/env python3
"""
分析历史页面（Analysis History Page）- 简化版（无RAG增强）

本页面提供分析历史记录的查看和过滤功能：
1. 多维度过滤器：按威胁等级、攻击类型筛选
2. 统计概览：总记录数、高危告警数、平均风险评分
3. 历史记录数据表格：支持自定义列格式和排序

数据流：
  页面加载 → APIClient 调用 GET /api/history → 渲染过滤器 → 显示统计和表格
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.utils.api_client import APIClient

# 页面配置
st.set_page_config(page_title="分析历史", page_icon="📊", layout="wide")

st.title("📊 分析历史记录")
st.markdown("---")

# 初始化 API 客户端
api_client = APIClient("http://localhost:8000")

# 后端连接检查
if not api_client.health_check():
    st.error("⚠️ 无法连接到后端服务")
    st.stop()

# ==================== 过滤器区域 ====================
st.subheader("🔍 过滤器")
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    # 威胁等级过滤下拉框
    threat_level_filter = st.selectbox(
        "威胁等级",
        ["全部", "高危", "中危", "低危"]
    )

with filter_col2:
    # 攻击类型过滤下拉框
    attack_type_filter = st.selectbox(
        "攻击类型",
        ["全部", "SQL注入", "XSS攻击", "命令注入", "目录遍历", "C2通信", "Webshell"]
    )

with filter_col3:
    # 显示条数控制
    limit = st.number_input("显示条数", min_value=10, max_value=200, value=50, step=10)

# ==================== 数据加载和展示 ====================
try:
    with st.spinner("正在加载历史记录..."):
        # 调用后端 GET /api/history 接口
        # 将"全部"选项转换为 None（表示不过滤）
        history = api_client.get_analysis_history(
            limit=limit,
            offset=0,
            threat_level=None if threat_level_filter == "全部" else threat_level_filter,
            attack_type=None if attack_type_filter == "全部" else attack_type_filter,
        )

    if not history:
        # 无记录时显示友好提示
        st.info("📭 暂无分析记录，请先在「告警分析」页面提交告警进行分析")
    else:
        st.success(f"✅ 找到 {len(history)} 条记录")

        # 将历史记录列表转换为 Pandas DataFrame 便于展示
        df = pd.DataFrame(history)
        # 将 Unix 时间戳（秒）转换为 datetime 类型，unit='s' 指定时间戳单位
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

        # ---------- 统计概览（3列布局） ----------
        stat_cols = st.columns(3)
        with stat_cols[0]:
            st.metric("总记录数", len(df))
        with stat_cols[1]:
            # 统计高危告警数量
            high_risk_count = len(df[df['threat_level'] == '高危'])
            st.metric("高危告警", high_risk_count)
        with stat_cols[2]:
            # 计算所有记录的平均风险评分
            avg_risk = df['risk_score'].mean()
            st.metric("平均风险分", f"{avg_risk:.1f}/10")

        st.markdown("---")

        # ---------- 历史记录数据表格 ----------
        st.subheader("📋 历史记录列表")

        # 选取展示列，并创建副本避免修改原始数据
        display_df = df[['analysis_id', 'attack_type', 'threat_level', 'risk_score', 'timestamp']].copy()
        # 截断 UUID 只显示前 8 位 + "..."
        display_df['analysis_id'] = display_df['analysis_id'].str[:8] + "..."
        # 中文列名映射
        display_df.columns = ['分析ID', '攻击类型', '威胁等级', '风险评分', '时间']

        # 自定义列格式：数字格式和日期格式
        column_config = {
            "风险评分": st.column_config.NumberColumn("风险评分", format="%.1f/10"),
            "时间": st.column_config.DatetimeColumn("时间", format="YYYY-MM-DD HH:mm:ss")
        }

        # 使用 Streamlit 的 dataframe 组件渲染交互式表格
        st.dataframe(
            display_df,
            use_container_width=True,        # 表格宽度自适应容器
            hide_index=True,                 # 隐藏行索引
            column_config=column_config,     # 应用列格式
            height=400                       # 固定高度，超出时显示滚动条
        )

except Exception as e:
    st.error(f"❌ 加载历史记录失败: {str(e)}")
    st.exception(e)
