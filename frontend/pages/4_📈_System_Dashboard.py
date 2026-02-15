#!/usr/bin/env python3
"""
系统仪表板页面（System Dashboard）- 简化版（无RAG增强）

本页面提供系统运行状况的可视化仪表板：
1. 关键指标卡片：总分析次数、高危告警占比、攻击类型数
2. 交互式图表：
   - 威胁等级分布饼图（Plotly 环形图）
   - 攻击类型分布柱状图（Plotly 柱状图）
3. 原始统计数据查看（可展开的 JSON 视图）

可视化工具：
- 使用 Plotly Express 和 Plotly Graph Objects 创建交互式图表
- 饼图使用预定义的颜色方案（严重→红色，低危→绿色）
- 柱状图使用 Reds 色阶表示数量
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.utils.api_client import APIClient

# 页面配置
st.set_page_config(page_title="系统仪表板", page_icon="📈", layout="wide")

st.title("📈 系统仪表板")
st.markdown("---")

# 初始化 API 客户端
api_client = APIClient("http://localhost:8000")

# 后端连接检查
if not api_client.health_check():
    st.error("⚠️ 无法连接到后端服务")
    st.stop()

# 手动刷新按钮：点击后触发页面重渲染，重新获取最新数据
if st.button("🔄 刷新数据", use_container_width=False):
    st.rerun()

# ==================== 数据加载和展示 ====================
try:
    with st.spinner("正在加载统计数据..."):
        # 调用后端 GET /api/stats 接口获取统计数据
        stats = api_client.get_stats()
    
    # ---------- 关键指标卡片（3列布局） ----------
    st.header("📊 关键指标")
    metric_cols = st.columns(3)
    
    with metric_cols[0]:
        st.metric(
            "总分析次数",
            stats['total_analyses'],
            help="系统启动以来的总分析次数"
        )
    
    with metric_cols[1]:
        # 计算高危告警占比：高危数量 / 总数 × 100%
        total = stats['total_analyses']
        high_risk = stats['threat_level_distribution'].get('高危', 0)
        high_risk_pct = (high_risk / total * 100) if total > 0 else 0
        st.metric(
            "高危告警占比",
            f"{high_risk_pct:.1f}%",
            help="高危级别告警的占比"
        )
    
    with metric_cols[2]:
        # 统计检测到的不同攻击类型数量
        attack_types_count = len(stats['attack_type_distribution'])
        st.metric(
            "攻击类型数",
            attack_types_count,
            help="检测到的不同攻击类型数量"
        )
    
    st.markdown("---")
    
    # ---------- 图表区域（2列布局） ----------
    chart_col1, chart_col2 = st.columns(2)
    
    # ===== 左列：威胁等级分布饼图 =====
    with chart_col1:
        st.subheader("威胁等级分布")
        
        threat_dist = stats['threat_level_distribution']
        if threat_dist:
            # 预定义各威胁等级的颜色方案
            # 从红色（严重）到绿色（低危），直观表达风险程度
            colors = {
                '严重': '#D32F2F',    # 深红色
                '高危': '#F57C00',    # 橙色
                '中危': '#FBC02D',    # 黄色
                '低危': '#388E3C',    # 绿色
                '未知': '#757575'     # 灰色
            }
            
            labels = list(threat_dist.keys())
            values = list(threat_dist.values())
            # 根据威胁等级匹配预定义颜色
            pie_colors = [colors.get(label, '#757575') for label in labels]
            
            # 使用 Plotly Graph Objects 创建环形饼图
            # hole=0.3 表示中心留30%的空洞（环形图效果）
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=pie_colors),
                hole=0.3        # 中心空洞比例，0为普通饼图，>0为环形图
            )])
            
            fig.update_layout(
                height=350,
                showlegend=True,
                margin=dict(t=30, b=0, l=0, r=0)    # 紧凑的边距
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无数据")
    
    # ===== 右列：攻击类型分布柱状图 =====
    with chart_col2:
        st.subheader("攻击类型分布")
        
        attack_dist = stats['attack_type_distribution']
        if attack_dist:
            # 使用 Plotly Express 创建柱状图
            # color 使用数值映射颜色深浅，color_continuous_scale='Reds' 使用红色色阶
            fig = px.bar(
                x=list(attack_dist.keys()),
                y=list(attack_dist.values()),
                labels={'x': '攻击类型', 'y': '数量'},
                color=list(attack_dist.values()),
                color_continuous_scale='Reds'    # 红色渐变色阶：值越大颜色越深
            )
            
            fig.update_layout(
                height=350,
                showlegend=False,                     # 隐藏图例（颜色条已经表达了信息）
                xaxis_tickangle=-45,                  # X轴标签旋转-45度，防止重叠
                margin=dict(t=30, b=80, l=0, r=0)    # 底部留更多空间给旋转的标签
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无数据")
    
    # ---------- 原始统计数据（可展开） ----------
    with st.expander("查看原始统计数据"):
        st.json(stats)

except Exception as e:
    st.error(f"❌ 加载统计数据失败: {str(e)}")
    st.exception(e)
