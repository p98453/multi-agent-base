#!/usr/bin/env python3
"""
RAG 检索增强生成服务（RAG Service）

为系统提供基于本地向量库的文档检索和问答能力：
1. 文档入库：接收文本 → 分块 → 调用 SiliconFlow Embedding API → 存入 ChromaDB
2. 检索：接收问题 → Embedding → 向量相似度检索 → 返回最相关文档块
3. 生成：将检索结果拼接为 Context → 调用 LLM 生成答案

使用方式：
    from backend.services.rag_service import get_rag_service
    rag = get_rag_service()
    rag.add_documents(["文本内容..."], source_name="文档名")
    result = await rag.query_and_generate("问题")
"""
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from openai import OpenAI
import chromadb
from chromadb.config import Settings

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
    """RAG 检索增强生成服务

    职责：
    - 维护 ChromaDB 本地向量库
    - 通过 SiliconFlow API 生成文本 Embedding
    - 检索相关文档片段
    - 调用 LLM 基于检索结果回答问题
    """

    # 文档分块参数
    CHUNK_SIZE = 500        # 每块最大字符数
    CHUNK_OVERLAP = 50      # 相邻块的重叠字符数（保证上下文连续性）
    COLLECTION_NAME = "rag_documents"

    def __init__(self):
        """初始化向量库客户端和 API 客户端"""
        # 初始化 ChromaDB（本地持久化）
        self._chroma_client = chromadb.PersistentClient(
            path=BackendConfig.CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self._collection = self._chroma_client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}   # 使用余弦相似度
        )
        logger.info(f"ChromaDB 已初始化，路径: {BackendConfig.CHROMA_DB_PATH}")

        # 初始化 SiliconFlow Embedding 客户端
        self._embed_client = OpenAI(
            api_key=BackendConfig.EMBEDDING_API_KEY,
            base_url=BackendConfig.EMBEDDING_URL
        )

        # 初始化 LLM 客户端（复用已有配置）
        self._llm_client = OpenAI(
            api_key=BackendConfig.LLM_API_KEY,
            base_url=BackendConfig.MODEL_URL
        )
        logger.info(f"Embedding 模型: {BackendConfig.EMBEDDING_MODEL}")

    # ==================== 文档分块 ====================
    def _split_text(self, text: str) -> List[str]:
        """将长文本按字符数分块，相邻块有重叠

        Args:
            text: 待分块的原始文本

        Returns:
            List[str]: 文本块列表
        """
        chunks = []
        start = 0
        text = text.strip()
        while start < len(text):
            end = min(start + self.CHUNK_SIZE, len(text))
            chunks.append(text[start:end])
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP
        return [c for c in chunks if c.strip()]

    # ==================== Embedding ====================
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量调用 SiliconFlow API 获取文本向量

        Args:
            texts: 待向量化的文本列表

        Returns:
            List[List[float]]: 每条文本的 embedding 向量
        """
        response = self._embed_client.embeddings.create(
            model=BackendConfig.EMBEDDING_MODEL,
            input=texts
        )
        return [item.embedding for item in response.data]

    # ==================== 文档入库 ====================
    def add_documents(self, texts: List[str], source_name: str = "unknown") -> int:
        """将文档文本分块、向量化后存入 ChromaDB

        Args:
            texts: 原始文本列表（可以是多个文档）
            source_name: 文档来源名称（用于元数据记录）

        Returns:
            int: 实际入库的文档块数量
        """
        all_chunks = []
        for text in texts:
            chunks = self._split_text(text)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("没有有效的文档内容可以入库")
            return 0

        logger.info(f"正在对 {len(all_chunks)} 个文档块生成 Embedding...")
        embeddings = self._get_embeddings(all_chunks)

        # 生成唯一 ID（基于现有数量 + 序号，避免冲突）
        existing_count = self._collection.count()
        ids = [f"doc_{existing_count + i}" for i in range(len(all_chunks))]
        metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(all_chunks))]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=metadatas
        )

        logger.info(f"成功入库 {len(all_chunks)} 个文档块，来源: {source_name}")
        return len(all_chunks)

    # ==================== 检索 ====================
    def retrieve(self, question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """检索与问题最相关的文档块

        Args:
            question: 用户查询问题
            top_k: 返回最相关的 top_k 个文档块

        Returns:
            List[dict]: 检索结果，每项包含 text、source、score 字段
        """
        if self._collection.count() == 0:
            return []

        # 对问题向量化
        question_embedding = self._get_embeddings([question])[0]

        # 向量相似度检索
        results = self._collection.query(
            query_embeddings=[question_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        retrieved = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            retrieved.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1 - dist, 4)   # 余弦距离转相似度分数
            })

        return retrieved

    # ==================== 生成答案 ====================
    async def query_and_generate(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """RAG 完整流程：检索 → 构建 Context → LLM 生成答案

        Args:
            question: 用户问题
            top_k: 检索的最大文档块数量

        Returns:
            dict: {
                "answer": str,          # LLM 生成的答案
                "sources": List[dict],  # 检索到的原文片段
                "has_context": bool     # 是否找到相关文档
            }
        """
        # 1. 检索相关文档
        sources = self.retrieve(question, top_k=top_k)

        if not sources:
            return {
                "answer": "知识库中暂无相关文档，请先上传文档后再提问。",
                "sources": [],
                "has_context": False
            }

        # 2. 构建上下文提示词
        context_parts = []
        for i, src in enumerate(sources, 1):
            context_parts.append(f"[片段{i}（来自: {src['source']}）]\n{src['text']}")
        context = "\n\n".join(context_parts)

        system_prompt = (
            "你是一个专业的知识库问答助手。请严格根据以下参考文档回答用户的问题。\n"
            "如果参考文档中没有足够的信息，请如实说明，不要编造答案。\n"
            "回答应该简洁、准确、有条理。"
        )

        user_prompt = f"""参考文档：
{context}

用户问题：{question}

请基于上述参考文档回答问题："""

        # 3. 调用 LLM 生成答案（在线程池中运行同步 API 调用，避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._llm_client.chat.completions.create(
                model=BackendConfig.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1024
            )
        )

        answer = response.choices[0].message.content

        return {
            "answer": answer,
            "sources": sources,
            "has_context": True
        }

    # ==================== 管理操作 ====================
    def clear(self) -> int:
        """清空向量库中的所有文档

        Returns:
            int: 清空前的文档块数量
        """
        count = self._collection.count()
        # 删除 collection 并重建（ChromaDB 没有直接的 clear 接口）
        self._chroma_client.delete_collection(self.COLLECTION_NAME)
        self._collection = self._chroma_client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"知识库已清空，共删除 {count} 个文档块")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息

        Returns:
            dict: 包含 total_chunks 字段的统计信息
        """
        return {
            "total_chunks": self._collection.count(),
            "embedding_model": BackendConfig.EMBEDDING_MODEL,
            "db_path": BackendConfig.CHROMA_DB_PATH
        }
