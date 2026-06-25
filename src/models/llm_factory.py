#!/usr/bin/env python3
"""
LangChain LLM 工厂模块（LLM Factory）

本模块提供 LangChain ChatOpenAI 实例的全局单例管理，替代原有的
api_client.py + llm_inference.py 两层封装。

LangChain 的 ChatOpenAI 已内置：
- OpenAI 兼容 API 通信（支持 SiliconFlow 等第三方服务）
- 异步调用支持（ainvoke）
- 自动重试和错误处理
- Token 统计

使用方式：
    from src.models.llm_factory import get_chat_llm
    llm = get_chat_llm()
    response = await llm.ainvoke("你的提示词")
"""
from langchain_openai import ChatOpenAI
from backend.config import BackendConfig

# ==================== 全局单例管理 ====================
_llm_instance = None


def get_chat_llm() -> ChatOpenAI:
    """获取全局 ChatOpenAI 实例（单例模式）

    创建一个配置好的 ChatOpenAI 实例，连接到 SiliconFlow API。
    使用 BackendConfig 中的配置值，与原有系统保持一致。

    Returns:
        ChatOpenAI: 全局唯一的 LangChain LLM 实例
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOpenAI(
            model=BackendConfig.MODEL_NAME,
            api_key=BackendConfig.LLM_API_KEY,
            base_url=BackendConfig.MODEL_URL,
            temperature=0.3,
            max_tokens=512,
        )
        print("[✓] LangChain ChatOpenAI 已初始化")
    return _llm_instance


def reset_llm():
    """重置全局 LLM 实例（用于测试或重新初始化）"""
    global _llm_instance
    _llm_instance = None
