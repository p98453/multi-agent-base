#!/usr/bin/env python3
"""
远程 API LLM 推理包装器（Async Version）

本模块是 LLM 推理的上层封装，位于 APIClient 之上，提供更友好的接口。
将 APIClient 的原始 HTTP 调用包装为面向业务的推理方法。

设计模式：
- 单例模式（Singleton）：全局只创建一个 LLMInference 实例，避免重复初始化 APIClient
- 全局变量管理：使用模块级全局变量 _GLOBAL_CLIENT 和 _CLIENT_INITIALIZED 
  追踪 APIClient 的初始化状态

调用关系：
  专家智能体 → get_llm_inference() → LLMInference.generate_response() → APIClient.generate()
"""
import time
import logging
from src.models.api_client import APIClient

# 标准库日志记录器，用于记录推理过程中的错误信息
logger = logging.getLogger(__name__)

# ==================== 全局单例管理 ====================
# 使用模块级全局变量实现 APIClient 的单例模式
# _GLOBAL_CLIENT: 全局 APIClient 实例，所有 LLMInference 共享同一个客户端
# _CLIENT_INITIALIZED: 标志位，确保 APIClient 只被初始化一次
_GLOBAL_CLIENT = None
_CLIENT_INITIALIZED = False

class LLMInference:
    """远程模型推理引擎包装器（异步版本）
    
    封装 APIClient，提供面向业务的推理接口：
    - generate_response(): 文本生成（用于安全威胁分析）
    - get_embedding(): 向量生成（用于语义搜索）
    
    单例行为说明：
    - 首次创建时初始化 APIClient 并缓存到全局变量
    - 后续创建时直接复用已有的 APIClient 实例
    """

    def __init__(self):
        """初始化 LLM 推理引擎
        
        检查全局 APIClient 是否已初始化：
        - 已初始化：直接复用全局实例，跳过重复初始化
        - 未初始化：创建新的 APIClient 实例并缓存到全局变量
        
        Raises:
            RuntimeError: APIClient 初始化失败时抛出
        """
        global _GLOBAL_CLIENT, _CLIENT_INITIALIZED

        # 如果 APIClient 已经初始化过，直接复用全局实例
        if _CLIENT_INITIALIZED:
            print("[正常] 使用已初始化的API客户端")
            self.client = _GLOBAL_CLIENT
            return

        # 首次初始化：创建 APIClient 实例
        print("\n" + "="*70)
        print("[启动] 初始化异步远程API客户端")
        print("="*70)

        try:
            # 创建 APIClient 实例（会读取 .env 中的 API Key 和模型配置）
            self.client = APIClient()
            _GLOBAL_CLIENT = self.client          # 缓存到全局变量
            _CLIENT_INITIALIZED = True            # 标记为已初始化
            
            print("      [正常] 异步API客户端已初始化")
            print("="*70)
            print("[成功] 系统已就绪，可进行异步远程推理！")
            print("="*70 + "\n")

        except Exception as e:
            print(f"[错误] API客户端初始化失败: {e}")
            raise RuntimeError(f"API Client initialization failed: {e}")

    async def generate_response(self, prompt: str, max_new_tokens: int = 512, temperature: float = 0.7) -> str:
        """调用远程 LLM 生成文本响应（异步方法）
        
        这是专家智能体调用的核心方法，将 Prompt 发送到远程 LLM API 并获取分析结果。
        
        参数命名说明：
        - max_new_tokens 对应 APIClient.generate() 中的 max_tokens 参数
        - 命名差异是为了与 HuggingFace Transformers 的接口风格保持一致
        
        Args:
            prompt: 发送给 LLM 的提示文本（由专家智能体生成）
            max_new_tokens: 最大生成 token 数（默认 512）
            temperature: 生成温度（默认 0.7），安全分析场景建议使用较低值（如 0.3）
            
        Returns:
            str: LLM 生成的文本响应（已去除首尾空白字符）
            
        Raises:
            RuntimeError: APIClient 未初始化时抛出
            Exception: API 调用失败时抛出（由调用方处理降级逻辑）
        """
        global _CLIENT_INITIALIZED

        # 前置检查：确保 APIClient 已成功初始化
        if not _CLIENT_INITIALIZED or self.client is None:
            raise RuntimeError("API Client not initialized!")

        try:
            # 调用底层 APIClient 的 generate() 方法发送 API 请求
            response = await self.client.generate(
                prompt=prompt, 
                max_tokens=max_new_tokens, 
                temperature=temperature
            )

            # 返回去除首尾空白的响应文本
            return response.strip()

        except Exception as e:
            logger.error(f"Async inference failed: {e}")
            raise  # 将异常向上抛出，由专家智能体的 analyze() 方法处理降级
    
    async def get_embedding(self, text: str) -> list:
        """获取文本的向量表示（异步方法）
        
        将文本转换为高维向量，可用于语义搜索和相似度计算。
        
        Args:
            text: 需要向量化的文本
            
        Returns:
            list: 文本向量（浮点数列表）
            
        Raises:
            RuntimeError: APIClient 未初始化时抛出
        """
        global _CLIENT_INITIALIZED
        
        # 前置检查
        if not _CLIENT_INITIALIZED or self.client is None:
            raise RuntimeError("API Client not initialized!")
        
        try:
            # 调用底层 APIClient 的 get_embedding() 方法
            embedding = await self.client.get_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Async embedding generation failed: {e}")
            raise


# ==================== 全局实例工厂函数 ====================
# 进一步的单例封装：确保整个应用中只存在一个 LLMInference 实例
_llm_instance = None

def get_llm_inference():
    """获取全局 LLM 推理实例（工厂函数 + 单例模式）
    
    整个系统共享同一个 LLMInference 实例，避免重复创建：
    - 首次调用：创建 LLMInference 实例（内部会初始化 APIClient）
    - 后续调用：直接返回已缓存的实例
    
    Returns:
        LLMInference: 全局唯一的 LLM 推理引擎实例
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMInference()
    return _llm_instance


# ==================== 测试入口 ====================
# 直接运行本文件时执行测试（python -m src.models.llm_inference）
if __name__ == "__main__":
    import asyncio
    
    async def test_main():
        """测试远程 API 推理功能
        
        创建 LLMInference 实例，发送一个 SQL 注入分析请求，
        验证 API 连接和模型推理是否正常工作。
        """
        print("[测试] 测试远程API推理")
        print("="*70)

        try:
            llm = LLMInference()
            test_prompt = "Analyze SQL injection: ' OR '1'='1"
            print(f"\n[INPUT] Test input: {test_prompt}")

            result = await llm.generate_response(test_prompt, max_new_tokens=50)

            print(f"\n[OUTPUT] Model output:")
            print(result)
            print("\n" + "="*70)
            print("[完成] 测试结束")
        except Exception as e:
            print(f"[TEST FAILED] {e}")
    
    asyncio.run(test_main())