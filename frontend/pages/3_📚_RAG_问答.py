#!/usr/bin/env python3
"""
RAG 知识库问答页面（RAG Q&A Page）

功能：
1. 文档上传区：粘贴文本 或 上传 .txt/.md 文件，点击"入库"
2. 知识库状态：显示当前已存储的文档块数量
3. 问答区：输入问题，LLM 基于知识库内容作答，并展示检索到的原文片段
4. 清库按钮：清空所有已存储的文档
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.utils.api_client import APIClient

st.set_page_config(page_title="RAG 知识库问答", page_icon="📚", layout="wide")

st.title("📚 RAG 知识库问答")
st.markdown("基于本地向量库的检索增强生成（RAG）问答系统，使用 `Qwen/Qwen3-Embedding-8B` 进行语义检索。")
st.markdown("---")

api_client = APIClient("http://localhost:8000")

# 后端连接检查
if not api_client.health_check():
    st.error("⚠️ 无法连接到后端服务，请确保 FastAPI 服务正在运行")
    st.info("启动命令: `python start_backend.py`")
    st.stop()

# ==================== 侧边栏：知识库状态 + 清库 ====================
with st.sidebar:
    st.header("📊 知识库状态")

    try:
        stats = api_client.rag_stats()
        total = stats.get("total_chunks", 0)
        model = stats.get("embedding_model", "N/A")

        if total == 0:
            st.warning("🗂️ 知识库为空")
        else:
            st.success(f"✅ 已存储 **{total}** 个文档块")

        st.caption(f"Embedding 模型：`{model}`")
    except Exception as e:
        st.error(f"无法获取知识库状态: {e}")

    st.markdown("---")

    st.subheader("⚠️ 危险操作")
    if st.button("🗑️ 清空知识库", type="secondary", use_container_width=True):
        with st.spinner("正在清空..."):
            try:
                result = api_client.rag_clear()
                st.success(result.get("message", "已清空"))
                st.rerun()
            except Exception as e:
                st.error(f"清空失败: {e}")

# ==================== 主区域：两列布局 ====================
col_upload, col_qa = st.columns([1, 1], gap="large")

# ---------- 左列：文档上传 ----------
with col_upload:
    st.header("📤 上传文档")

    tab_paste, tab_file = st.tabs(["✏️ 粘贴文本", "📁 上传文件"])

    with tab_paste:
        source_name_paste = st.text_input(
            "文档名称",
            value="手动输入",
            key="source_paste",
            placeholder="给这段文档起个名字"
        )
        text_input = st.text_area(
            "粘贴文档内容",
            height=300,
            placeholder="在此粘贴需要入库的文档内容...\n\n例如：一段产品介绍、技术文档、论文摘要等。",
            key="text_paste"
        )

        if st.button("📥 入库（文本）", type="primary", use_container_width=True):
            if not text_input.strip():
                st.warning("请先输入文本内容")
            else:
                with st.spinner("正在分块、生成 Embedding 并存入向量库..."):
                    try:
                        result = api_client.rag_upload(
                            texts=[text_input],
                            source_name=source_name_paste or "手动输入"
                        )
                        st.success(f"✅ {result.get('message', '入库成功')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 入库失败: {e}")

    with tab_file:
        source_name_file = st.text_input(
            "文档名称（留空则使用文件名）",
            value="",
            key="source_file",
            placeholder="自定义文档名称"
        )
        uploaded_file = st.file_uploader(
            "上传 .txt 或 .md 文件",
            type=["txt", "md"],
            help="支持 UTF-8 编码的文本文件"
        )

        if uploaded_file is not None:
            try:
                file_content = uploaded_file.read().decode("utf-8")
                st.text_area(
                    "文件预览（前 500 字符）",
                    value=file_content[:500] + ("..." if len(file_content) > 500 else ""),
                    height=200,
                    disabled=True
                )

                btn_label = "📥 入库（文件）"
                if st.button(btn_label, type="primary", use_container_width=True):
                    display_name = source_name_file.strip() or uploaded_file.name
                    with st.spinner("正在处理文件并存入向量库..."):
                        try:
                            result = api_client.rag_upload(
                                texts=[file_content],
                                source_name=display_name
                            )
                            st.success(f"✅ {result.get('message', '入库成功')}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 入库失败: {e}")
            except UnicodeDecodeError:
                st.error("文件编码错误，请确保文件为 UTF-8 编码")

    # 使用提示
    with st.expander("💡 使用说明"):
        st.markdown("""
        **文档入库流程：**
        1. 粘贴文本或上传文件
        2. 点击"入库"，系统会自动将长文本分块（每块约 500 字）
        3. 调用硅基流动 `Qwen3-Embedding-8B` 生成向量并存入本地 ChromaDB

        **注意事项：**
        - 文档会被分块存储，因此可以处理任意长度的文本
        - 多次入库的文档会累积，不会覆盖，需要清空请点击左侧"清空知识库"
        - 入库后刷新页面可看到左侧文档块数量更新
        """)

# ---------- 右列：问答 ----------
with col_qa:
    st.header("💬 知识库问答")

    # 初始化对话历史
    if "rag_messages" not in st.session_state:
        st.session_state.rag_messages = []

    # 问题输入
    top_k = st.slider("检索文档块数量（top_k）", min_value=1, max_value=8, value=3)

    question = st.text_input(
        "输入你的问题",
        placeholder="基于上传的文档提问...",
        key="rag_question"
    )

    ask_btn = st.button("🔍 提问", type="primary", use_container_width=True)

    # 执行问答
    if ask_btn:
        if not question.strip():
            st.warning("请先输入问题")
        else:
            with st.spinner("正在检索知识库并生成答案..."):
                try:
                    result = api_client.rag_query(question=question, top_k=top_k)

                    # 追加到对话历史
                    st.session_state.rag_messages.append({
                        "question": question,
                        "answer": result["answer"],
                        "sources": result["sources"],
                        "has_context": result["has_context"]
                    })
                except Exception as e:
                    st.error(f"❌ 问答失败: {e}")
                    st.exception(e)

    # 展示对话历史（最新的在上方）
    if st.session_state.rag_messages:
        st.markdown("---")
        st.subheader("📝 问答记录")

        for i, msg in enumerate(reversed(st.session_state.rag_messages)):
            with st.container(border=True):
                st.markdown(f"**🙋 问：** {msg['question']}")

                if msg["has_context"]:
                    st.markdown(f"**🤖 答：**\n\n{msg['answer']}")

                    # 折叠展示检索到的原文片段
                    with st.expander(f"📄 查看参考文档（{len(msg['sources'])} 个片段）"):
                        for j, src in enumerate(msg["sources"], 1):
                            score_pct = f"{src['score'] * 100:.1f}%"
                            st.markdown(
                                f"**片段 {j}** · 来源: `{src['source']}` · 相似度: `{score_pct}`"
                            )
                            st.text(src["text"])
                            if j < len(msg["sources"]):
                                st.divider()
                else:
                    st.info(msg["answer"])

        # 清空对话记录按钮
        if st.button("🔄 清空对话记录", use_container_width=True):
            st.session_state.rag_messages = []
            st.rerun()
    else:
        st.info("📋 暂无问答记录。上传文档后，在上方输入问题开始问答。")
