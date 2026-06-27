import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from frontend.utils.api_client import APIClient

st.set_page_config(
    page_title="bid intelligence multi-agent system",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("bid intelligence multi-agent system")
st.caption("gateway + sub-agent + loop | crawler | document | presentation | distribution | skill evolution")
st.markdown("---")

api_client = APIClient("http://localhost:8000")

with st.sidebar:
    st.header("system status")
    if api_client.health_check():
        st.success("backend connected")
    else:
        st.error("backend not connected")
        st.info("start backend first: `python start_backend.py`")
        st.stop()

    st.markdown("---")
    st.markdown("**architecture**")
    st.markdown("""
    1. gateway - intent recognition + routing + quality control
    2. crawler agent - multi-platform data crawling
    3. document agent - parse + summarize + search + compare
    4. presentation agent - PPT + charts + export
    5. distribution agent - email + multi-channel push + scheduled tasks
    6. loop - quality evaluation -> feedback -> retry (max 3)
    7. skill evolution - feedback analysis -> root cause -> auto update
    """)

    st.markdown("---")
    st.subheader("quick actions")
    if st.button("refresh system info"):
        st.rerun()

    st.markdown("---")
    st.caption("v2.0 | bid intelligence system")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "task_feedback" not in st.session_state:
    st.session_state.task_feedback = {}

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            with st.expander("details"):
                st.json(msg["meta"])

if prompt := st.chat_input("describe your bid intelligence needs..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("gateway analyzing intent..."):
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

                with st.expander("processing details + feedback"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**route**: `{route.get('route', 'N/A')}` ({route.get('confidence', 0):.0%})")
                        st.markdown(f"**reason**: {route.get('reason', 'N/A')}")
                        st.markdown(f"**intent**: {route.get('user_intent_summary', 'N/A')}")
                    with col2:
                        st.markdown(f"**agent**: {agent.get('agent_type', 'N/A')}")
                        st.markdown(f"**skill chain**: {' -> '.join(skill_chain) if skill_chain else 'N/A'}")
                        st.markdown(f"**retries**: {agent.get('loop_count', 0)}")
                    with col3:
                        satisfaction = "passed" if eval_info.get('satisfied') else "failed"
                        st.markdown(f"**quality**: {satisfaction} (score: {eval_info.get('weighted_score', 0):.1f})")
                        st.markdown(f"**coverage**: {eval_info.get('coverage', 0)}/10")
                        st.markdown(f"**accuracy**: {eval_info.get('accuracy', 0)}/10")
                        st.markdown(f"**total time**: {perf.get('total_time_ms', 0)}ms")

                    if loop_history and len(loop_history) > 1:
                        st.markdown("**loop history**:")
                        for lh in loop_history:
                            loop_eval = lh.get("evaluation", {})
                            st.markdown(f"- loop {lh.get('loop')}: score {loop_eval.get('weighted_score', 0):.1f} - {'passed' if loop_eval.get('satisfied') else 'feedback: ' + str(loop_eval.get('feedback', ''))[:100]}")

                    st.markdown("---")
                    st.markdown("**submit feedback for skill evolution**")
                    fb_col1, fb_col2 = st.columns([3, 1])
                    with fb_col1:
                        feedback_text = st.text_area("feedback (tell us what went wrong):", key=f"fb_{result.get('task_id', '')}", placeholder="e.g. crawling results missing Jiangsu province data")
                    with fb_col2:
                        deviation = st.selectbox("deviation type:", ["", "content", "format", "accuracy", "completeness"], key=f"dev_{result.get('task_id', '')}")
                        rating = st.slider("rating:", 1, 10, 5, key=f"rat_{result.get('task_id', '')}")
                    if st.button("submit feedback -> trigger skill evolution", key=f"btn_{result.get('task_id', '')}"):
                        if feedback_text.strip():
                            with st.spinner("analyzing feedback and evolving skills..."):
                                fb_result = api_client.submit_feedback(
                                    result.get("task_id", ""),
                                    feedback_text,
                                    deviation_type=deviation if deviation else None,
                                    rating=rating
                                )
                                if fb_result.get("evolution_applied"):
                                    st.success(f"skill evolved: {fb_result.get('updated_skills', [])}")
                                    st.info(f"root cause: {fb_result.get('root_cause', 'N/A')}")
                                else:
                                    st.warning(fb_result.get("message", "feedback received"))
                        else:
                            st.warning("please enter feedback text")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"],
                    "meta": meta
                })

            except Exception as e:
                st.error(f"processing failed: {e}")

with st.sidebar:
    st.markdown("---")
    st.subheader("skill management")
    tab1, tab2 = st.tabs(["all skills", "evolution history"])
    with tab1:
        if st.button("load skills"):
            try:
                skills_data = api_client.list_skills()
                skills = skills_data.get("skills", [])
                for s in skills:
                    st.markdown(f"**{s['name']}** ({s['agent_type']}) v{s['version']}")
                    st.caption(f"{s['description'][:100]}")
                    st.caption(f"evolutions: {s['evolution_count']} | params: {len(s.get('parameters', {}))}")
                    st.markdown("---")
            except Exception as e:
                st.error(f"failed: {e}")
    with tab2:
        if st.button("load evolution history"):
            try:
                evo_data = api_client.get_evolution_history()
                for e in evo_data.get("history", [])[-10:]:
                    st.markdown(f"**{e.get('skill_name')}** v{e.get('old_version')} -> v{e.get('new_version', e.get('old_version', 1)+1)}")
                    st.caption(f"reason: {e.get('reason', '')[:100]}")
                    st.caption(f"time: {e.get('timestamp', '')}")
                    st.markdown("---")
            except Exception as e:
                st.error(f"failed: {e}")