#!/usr/bin/env python3
"""
RAG 检索增强生成服务（RAG Service）- LangChain 重构版

使用 LangChain 生态组件替代手写的 RAG 实现：
- RecursiveCharacterTextSplitter 替代手写 _split_text()
- OpenAIEmbeddings 替代手写 _get_embeddings()
- langchain_chroma.Chroma 替代手写 ChromaDB 操作
- LCEL 链替代手写 query_and_generate()

所有对外接口保持不变：
    from backend.services.rag_service import get_rag_service
    rag = get_rag_service()
    rag.add_documents(["文本内容..."], source_name="文档名")
    result = await rag.query_and_generate("问题")
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from backend.config import BackendConfig

# ==================== 全局单例 ====================
_rag_service_instance: Optional["RAGService"] = None


def get_rag_service() -> "RAGService":
    """获取 RAGService 全局单例"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance


class RAGService:
    """RAG 检索增强生成服务 - LangChain 重构版

    职责：
    - 使用 LangChain Chroma 维护本地向量库
    - 通过 LangChain OpenAIEmbeddings 生成文本 Embedding
    - 使用 LangChain Retriever 检索相关文档片段
    - 使用 LCEL 链调用 LLM 基于检索结果回答问题
    """

    # 文档分块参数
    CHUNK_SIZE = 500        # 每块最大字符数
    CHUNK_OVERLAP = 50      # 相邻块的重叠字符数
    COLLECTION_NAME = "rag_documents"

    def __init__(self):
        """初始化 LangChain RAG 组件"""
        # 1. 初始化 LangChain OpenAIEmbeddings（替代手写 OpenAI 客户端）
        self._embeddings = OpenAIEmbeddings(
            model=BackendConfig.EMBEDDING_MODEL,
            api_key=BackendConfig.EMBEDDING_API_KEY,
            base_url=BackendConfig.EMBEDDING_URL,
        )
        logger.info(f"LangChain OpenAIEmbeddings 已初始化，模型: {BackendConfig.EMBEDDING_MODEL}")

        # 2. 初始化 LangChain Chroma 向量存储（替代手写 ChromaDB 操作）
        self._vectorstore = Chroma(
            collection_name=self.COLLECTION_NAME,
            embedding_function=self._embeddings,
            persist_directory=BackendConfig.CHROMA_DB_PATH,
            collection_metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"LangChain Chroma 已初始化，路径: {BackendConfig.CHROMA_DB_PATH}")

        # 3. 初始化 LangChain 文本分块器（替代手写 _split_text()）
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

        # 4. 初始化 LLM（用于问答生成）
        self._llm = ChatOpenAI(
            model=BackendConfig.MODEL_NAME,
            api_key=BackendConfig.LLM_API_KEY,
            base_url=BackendConfig.MODEL_URL,
            temperature=0.3,
            max_tokens=1024,
        )

        # 5. 构建问答提示词模板
        self._qa_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一个专业的知识库问答助手。请严格根据以下参考文档回答用户的问题。\n"
             "如果参考文档中没有足够的信息，请如实说明，不要编造答案。\n"
             "回答应该简洁、准确、有条理。"),
            ("human",
             "参考文档：\n{context}\n\n用户问题：{question}\n\n请基于上述参考文档回答问题："),
        ])

    # ==================== 文档入库 ====================
    def add_documents(self, texts: List[str], source_name: str = "unknown") -> int:
        """将文档文本分块、向量化后存入 Chroma（接口不变）

        使用 LangChain RecursiveCharacterTextSplitter 进行智能分块。

        Args:
            texts: 原始文本列表
            source_name: 文档来源名称

        Returns:
            int: 实际入库的文档块数量
        """
        # 使用 LangChain 文本分块器处理所有文本
        all_chunks = []
        for text in texts:
            chunks = self._text_splitter.split_text(text)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("没有有效的文档内容可以入库")
            return 0

        logger.info(f"正在对 {len(all_chunks)} 个文档块生成 Embedding（LangChain）...")

        # 为每个块创建元数据
        metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(all_chunks))]

        # 使用 LangChain Chroma 的 add_texts 方法（内部自动调用 embedding + 存储）
        self._vectorstore.add_texts(
            texts=all_chunks,
            metadatas=metadatas,
        )

        logger.info(f"成功入库 {len(all_chunks)} 个文档块，来源: {source_name}")
        return len(all_chunks)

    # ==================== 检索 ====================
    def retrieve(self, question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """检索与问题最相关的文档块（接口不变）

        使用 LangChain Chroma 的 similarity_search_with_score 方法。

        Args:
            question: 用户查询问题
            top_k: 返回最相关的 top_k 个文档块

        Returns:
            List[dict]: 检索结果，每项包含 text、source、score 字段
        """
        # 检查向量库是否为空
        collection = self._vectorstore._collection
        if collection.count() == 0:
            return []

        # 使用 LangChain 的相似度检索（带分数）
        results = self._vectorstore.similarity_search_with_score(
            query=question,
            k=min(top_k, collection.count()),
        )

        retrieved = []
        for doc, distance in results:
            retrieved.append({
                "text": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "score": round(1 - distance, 4),  # 余弦距离转相似度分数
            })

        return retrieved

    # ==================== 生成答案 ====================
    async def query_and_generate(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """RAG 完整流程：检索 → 构建 Context → LLM 生成答案（接口不变）

        使用 LangChain LCEL 链式调用替代手写的流程。

        Args:
            question: 用户问题
            top_k: 检索的最大文档块数量

        Returns:
            dict: 包含 answer, sources, has_context 字段
        """
        # 1. 检索相关文档
        sources = self.retrieve(question, top_k=top_k)

        if not sources:
            return {
                "answer": "知识库中暂无相关文档，请先上传文档后再提问。",
                "sources": [],
                "has_context": False,
            }

        # 2. 构建上下文
        context_parts = []
        for i, src in enumerate(sources, 1):
            context_parts.append(f"[片段{i}（来自: {src['source']}）]\n{src['text']}")
        context = "\n\n".join(context_parts)

        # 3. 使用 LCEL 链生成答案
        chain = self._qa_prompt | self._llm | StrOutputParser()
        answer = await chain.ainvoke({
            "context": context,
            "question": question,
        })

        return {
            "answer": answer,
            "sources": sources,
            "has_context": True,
        }

    # ==================== 管理操作 ====================
    def clear(self) -> int:
        """清空向量库中的所有文档（接口不变）

        Returns:
            int: 清空前的文档块数量
        """
        collection = self._vectorstore._collection
        count = collection.count()

        # 删除并重建 collection
        self._vectorstore._client.delete_collection(self.COLLECTION_NAME)
        # 重新创建向量存储
        self._vectorstore = Chroma(
            collection_name=self.COLLECTION_NAME,
            embedding_function=self._embeddings,
            persist_directory=BackendConfig.CHROMA_DB_PATH,
            collection_metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"知识库已清空，共删除 {count} 个文档块")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息（接口不变）

        Returns:
            dict: 包含 total_chunks 字段的统计信息
        """
        collection = self._vectorstore._collection
        return {
            "total_chunks": collection.count(),
            "embedding_model": BackendConfig.EMBEDDING_MODEL,
            "db_path": BackendConfig.CHROMA_DB_PATH,
        }
