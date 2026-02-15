#!/usr/bin/env python3
"""
远程 LLM API 客户端（API Client）

本模块封装了与 SiliconFlow/Qwen 远程 API 的 HTTP 通信逻辑。
提供两个核心异步方法：
1. generate(): 调用 Chat Completions API 生成文本（用于告警分析）
2. get_embedding(): 调用 Embeddings API 生成文本向量（用于语义搜索等场景）

配置说明：
- 所有 API 配置（API Key、模型名称、API 地址）均从 .env 环境变量读取
- 使用 httpx 异步 HTTP 客户端，支持高效的非阻塞网络请求
- 请求超时时间：文本生成 60 秒，向量生成 30 秒
"""
import os
import httpx
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件中的环境变量
# .env 文件包含 LLM_API_KEY、MODEL_NAME、MODEL_URL 等敏感配置
load_dotenv()


class APIClient:
    """异步 API 客户端 - 用于远程 LLM 服务调用
    
    负责与 SiliconFlow 平台上的 Qwen 大语言模型进行 API 通信。
    使用 OpenAI 兼容的 API 格式（/v1/chat/completions 和 /v1/embeddings）。
    """
    
    def __init__(self):
        """初始化 API 客户端
        
        从环境变量中读取以下配置：
        - LLM_API_KEY: API 访问密钥（必须）
        - MODEL_NAME: 对话模型名称（默认 Qwen/Qwen3-30B-A3B-Thinking-2507）
        - MODEL_URL: API 基础 URL（默认 https://api.siliconflow.cn/v1）
        - EMBEDDING_MODEL_NAME: 向量模型名称（默认 Qwen/Qwen3-Embedding-0.6B）
        
        Raises:
            ValueError: 当 LLM_API_KEY 未设置时抛出异常
        """
        # 从环境变量读取 API 配置
        self.api_key = os.getenv("LLM_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "Qwen/Qwen3-30B-A3B-Thinking-2507")
        self.base_url = os.getenv("MODEL_URL", "https://api.siliconflow.cn/v1")
        self.embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "Qwen/Qwen3-Embedding-0.6B")
        
        # API Key 是必需的，缺失时立即报错
        if not self.api_key:
            raise ValueError("LLM_API_KEY environment variable is not set")
        
        # 构建 HTTP 请求头，包含 Bearer Token 认证和 JSON 内容类型
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """调用远程 LLM API 生成文本响应（异步方法）
        
        使用 OpenAI 兼容的 Chat Completions API 格式发送请求。
        将用户 Prompt 包装为 messages 数组中的 user 角色消息。
        
        Args:
            prompt: 发送给 LLM 的提示文本
            max_tokens: 最大生成 token 数（默认 512），控制响应长度
            temperature: 生成温度（默认 0.7），值越低输出越确定，值越高越随机
            
        Returns:
            str: LLM 生成的文本内容
            
        Raises:
            httpx.HTTPStatusError: API 返回非 2xx 状态码时抛出
        """
        # 构建 Chat Completions API 的请求 URL
        url = f"{self.base_url}/chat/completions"
        
        # 构建请求体：采用 OpenAI 兼容格式
        # messages 数组中只包含一个 user 角色的消息（单轮对话）
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 使用 httpx 异步客户端发送 POST 请求
        # timeout=60.0: 文本生成可能较慢，设置 60 秒超时
        # async with 确保请求完成后自动关闭连接
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()  # 非 2xx 状态码时抛出异常
            
            # 从 API 响应中提取生成的文本内容
            # 响应格式：{"choices": [{"message": {"content": "..."}}]}
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def get_embedding(self, text: str) -> list:
        """调用远程 API 获取文本的向量表示（异步方法）
        
        使用 OpenAI 兼容的 Embeddings API 格式，将文本转换为高维向量。
        生成的向量可用于语义搜索、相似度计算等下游任务。
        
        Args:
            text: 需要向量化的文本内容
            
        Returns:
            list: 文本的向量表示（浮点数列表）
            
        Raises:
            httpx.HTTPStatusError: API 返回非 2xx 状态码时抛出
        """
        # 构建 Embeddings API 的请求 URL
        url = f"{self.base_url}/embeddings"
        
        # 构建请求体
        payload = {
            "model": self.embedding_model,
            "input": text
        }
        
        # 使用 httpx 异步客户端发送 POST 请求
        # timeout=30.0: 向量生成相对较快，30 秒超时即可
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            # 从 API 响应中提取向量数据
            # 响应格式：{"data": [{"embedding": [0.1, 0.2, ...]}]}
            result = response.json()
            return result["data"][0]["embedding"]
