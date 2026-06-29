import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from frontend.utils.api_client import APIClient

st.set_page_config(
    page_title="招投标情报分析多智能体系统",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("招投标情报分析多智能体系统")
st.caption("网关 + 子智能体 + 循环反馈 | 爬虫管理 | 文档处理 | 智能演示 | 多端分发 | Skill进化")
st.markdown("---")

api_client = APIClient("http://localhost:8000")

with st.sidebar:
    st.header("系统状态")
    if api_client.health_check():
        st.success("后端已连接")
    else:
        st.error("后端未连接")
        st.info("请先启动后端: `python start_backend.py`")
        st.stop()

    st.markdown("---")
    st.markdown("**系统架构**")
    st.markdown("""
    1. 网关 - 意图识别 + 动态路由 + 质量管控
    2. 爬虫管理智能体 - 多平台数据爬取
    3. 文档处理智能体 - 解析 + 摘要 + 搜索 + 对比
    4. 智能演示智能体 - PPT + 图表 + 导出
    5. 多端分发智能体 - 邮件 + 多渠道推送 + 定时任务
    6. 循环反馈 - 质量评估 → 改进反馈 → 重试 (最多3次)
    7. Skill进化 - 用户反馈 → 根因分析 → 自动更新
    """)

    st.markdown("---")
    st.subheader("快捷操作")
    if st.button("刷新系统信息"):
        st.rerun()

    st.markdown("---")
    st.caption("v2.0 | 招投标情报分析多智能体系统")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "task_feedback" not in st.session_state:
    st.session_state.task_feedback = {}

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            with st.expander("处理详情"):
                st.json(msg["meta"])

if prompt := st.chat_input("描述你的招投标情报需求..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("网关正在分析意图..."):
            try:
                result = api_client.chat(prompt)

                st.markdown(result["response"])

                route = result.get("routing", {})
                agent = result.get("agent_info", {})
                eval_info = result.get("evaluation", {})
                perf = result.get("performance", {})
                loop_history = result.get("loop_history", [])
                skill_chain = result.get("skill_chain", [])

                meta = {
                    "task_id": result.get("task_id", ""),
                    "routing": route,
                    "agent": agent,
                    "evaluation": eval_info,
                    "performance": perf,
                    "skill_chain": skill_chain,
                    "loop_history": loop_history,
                }

                with st.expander("处理详情 + 反馈"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**路由**: `{route.get('route', 'N/A')}` (置信度: {route.get('confidence', 0):.0%})")
                        st.markdown(f"**理由**: {route.get('reason', 'N/A')}")
                        st.markdown(f"**意图**: {route.get('user_intent_summary', 'N/A')}")
                    with col2:
                        st.markdown(f"**智能体**: {agent.get('agent_type', 'N/A')}")
                        st.markdown(f"**技能链**: {' -> '.join(skill_chain) if skill_chain else 'N/A'}")
                        st.markdown(f"**重试次数**: {agent.get('loop_count', 0)}")
                    with col3:
                        satisfaction = "通过" if eval_info.get('satisfied') else "未通过"
                        st.markdown(f"**质量评估**: {satisfaction} (评分: {eval_info.get('weighted_score', 0):.1f})")
                        st.markdown(f"**覆盖度**: {eval_info.get('coverage', 0)}/10")
                        st.markdown(f"**准确性**: {eval_info.get('accuracy', 0)}/10")
                        st.markdown(f"**总耗时**: {perf.get('total_time_ms', 0)}ms")

                    if loop_history and len(loop_history) > 1:
                        st.markdown("**循环历史**:")
                        for lh in loop_history:
                            loop_eval = lh.get("evaluation", {})
                            st.markdown(f"- 第{lh.get('loop')}轮: 评分 {loop_eval.get('weighted_score', 0):.1f} - {'通过' if loop_eval.get('satisfied') else '反馈: ' + str(loop_eval.get('feedback', ''))[:100]}")

                    st.markdown("---")
                    st.markdown("**提交反馈触发Skill进化**")
                    fb_col1, fb_col2 = st.columns([3, 1])
                    with fb_col1:
                        feedback_text = st.text_area("反馈内容（告诉我们哪里出了问题）:", key=f"fb_{result.get('task_id', '')}", placeholder="例如: 爬取结果缺少了江苏省的数据")
                    with fb_col2:
                        deviation = st.selectbox("偏差类型:", ["", "内容(content)", "格式(format)", "准确性(accuracy)", "完整性(completeness)"], key=f"dev_{result.get('task_id', '')}")
                        rating = st.slider("满意度评分:", 1, 10, 5, key=f"rat_{result.get('task_id', '')}")
                    if st.button("提交反馈 → 触发Skill进化", key=f"btn_{result.get('task_id', '')}"):
                        if feedback_text.strip():
                            with st.spinner("正在分析反馈并进化Skill..."):
                                fb_result = api_client.submit_feedback(
                                    result.get("task_id", ""),
                                    feedback_text,
                                    deviation_type=deviation.split("(")[0].strip() if deviation else None,
                                    rating=rating
                                )
                                if fb_result.get("evolution_applied"):
                                    st.success(f"Skill已进化: {fb_result.get('updated_skills', [])}")
                                    st.info(f"根因: {fb_result.get('root_cause', 'N/A')}")
                                else:
                                    st.warning(fb_result.get("message", "反馈已收到"))
                        else:
                            st.warning("请输入反馈内容")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"],
                    "meta": meta
                })

            except Exception as e:
                st.error(f"处理失败: {e}")

with st.sidebar:
    st.markdown("---")
    st.subheader("Skill管理")
    tab1, tab2 = st.tabs(["全部技能", "进化历史"])
    with tab1:
        if st.button("加载技能列表"):
            try:
                skills_data = api_client.list_skills()
                skills = skills_data.get("skills", [])
                for s in skills:
                    st.markdown(f"**{s['name']}** ({s['agent_type']}) v{s['version']}")
                    st.caption(f"{s['description'][:100]}")
                    st.caption(f"进化次数: {s['evolution_count']} | 参数数: {len(s.get('parameters', {}))}")
                    st.markdown("---")
            except Exception as e:
                st.error(f"加载失败: {e}")
    with tab2:
        if st.button("加载进化历史"):
            try:
                evo_data = api_client.get_evolution_history()
                for e in evo_data.get("history", [])[-10:]:
                    st.markdown(f"**{e.get('skill_name')}** v{e.get('old_version')} → v{e.get('new_version', e.get('old_version', 1)+1)}")
                    st.caption(f"原因: {e.get('reason', '')[:100]}")
                    st.caption(f"时间: {e.get('timestamp', '')}")
                    st.markdown("---")
            except Exception as e:
                st.error(f"加载失败: {e}")