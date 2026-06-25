#!/usr/bin/env python3
"""
RAG API 路由（RAG Routes）

提供 RAG 知识库的 RESTful API 端点：
- POST /api/rag/upload  : 上传文档文本，分块入库
- POST /api/rag/query   : 提问，检索 + LLM 生成答案
- DELETE /api/rag/clear : 清空知识库
- GET /api/rag/stats    : 查看知识库统计信息
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from loguru import logger

from backend.services.rag_service import get_rag_service

router = APIRouter(prefix="/api/rag", tags=["RAG"])


# ==================== 请求/响应数据模型 ====================

class UploadRequest(BaseModel):
    """文档上传请求"""
    texts: List[str] = Field(..., description="文档文本列表")
    source_name: str = Field(default="用户上传", description="文档来源名称")


class UploadResponse(BaseModel):
    """文档上传响应"""
    success: bool
    chunks_added: int
    message: str


class QueryRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., description="用户问题", min_length=1)
    top_k: int = Field(default=3, ge=1, le=10, description="检索文档块数量")


class SourceChunk(BaseModel):
    """检索到的文档片段"""
    text: str
    source: str
    score: float


class QueryResponse(BaseModel):
    """问答响应"""
    answer: str
    sources: List[SourceChunk]
    has_context: bool


class ClearResponse(BaseModel):
    """清库响应"""
    success: bool
    deleted_chunks: int
    message: str


# ==================== API 路由 ====================

@router.post("/upload", response_model=UploadResponse)
async def upload_documents(request: UploadRequest):
    """上传文档文本到知识库（POST /api/rag/upload）

    接收文本列表，自动分块并生成 Embedding 存入 ChromaDB。
    """
    try:
        logger.info(f"收到文档上传请求，共 {len(request.texts)} 段文本，来源: {request.source_name}")
        rag = get_rag_service()
        chunks_added = rag.add_documents(request.texts, source_name=request.source_name)
        return UploadResponse(
            success=True,
            chunks_added=chunks_added,
            message=f"成功入库 {chunks_added} 个文档块"
        )
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """知识库问答（POST /api/rag/query）

    检索最相关文档块，调用 LLM 生成基于文档的答案。
    """
    try:
        logger.info(f"收到 RAG 查询: {request.question[:50]}...")
        rag = get_rag_service()
        result = await rag.query_and_generate(request.question, top_k=request.top_k)
        return QueryResponse(
            answer=result["answer"],
            sources=[SourceChunk(**s) for s in result["sources"]],
            has_context=result["has_context"]
        )
    except Exception as e:
        logger.error(f"RAG 查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 查询失败: {str(e)}")


@router.delete("/clear", response_model=ClearResponse)
async def clear_knowledge_base():
    """清空知识库（DELETE /api/rag/clear）

    删除所有已存储的文档块，知识库重置为空。
    """
    try:
        rag = get_rag_service()
        deleted = rag.clear()
        return ClearResponse(
            success=True,
            deleted_chunks=deleted,
            message=f"已清空知识库，共删除 {deleted} 个文档块"
        )
    except Exception as e:
        logger.error(f"清空知识库失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空知识库失败: {str(e)}")


@router.get("/stats")
async def get_rag_stats() -> Dict[str, Any]:
    """获取知识库统计信息（GET /api/rag/stats）

    返回当前知识库中的文档块数量、Embedding 模型等信息。
    """
    try:
        rag = get_rag_service()
        return rag.get_stats()
    except Exception as e:
        logger.error(f"获取 RAG 统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
