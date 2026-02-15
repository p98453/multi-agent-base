"""
应用配置模块（Config）

本模块通过 python-dotenv 从项目根目录的 .env 文件加载环境变量，
提供全局统一的配置访问接口。

配置项说明：
- LLM_API_KEY: SiliconFlow 平台的 API 访问密钥
- MODEL_NAME: 用于文本生成的 LLM 模型名称（如 Qwen2.5-32B-Instruct）
- MODEL_URL: LLM API 的基础 URL
- EMBEDDING_MODEL_NAME: 用于文本向量化的 Embedding 模型名称

使用方式：
    from src.utils.config import Config
    Config.validate()  # 验证必需配置
    key = Config.LLM_API_KEY
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量到 os.environ
# load_dotenv() 会自动在当前目录及上层目录中查找 .env 文件
load_dotenv()

class Config:
    """应用配置类
    
    使用类属性的方式提供配置值，所有属性在模块加载时从环境变量中读取。
    这种设计允许通过 Config.LLM_API_KEY 的方式直接访问配置，无需实例化。
    """
    
    # ===== LLM 模型配置 =====
    LLM_API_KEY = os.getenv("LLM_API_KEY")                                         # API 访问密钥（必须）
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-32B-Instruct")              # 对话模型名称
    MODEL_URL = os.getenv("MODEL_URL", "https://api.siliconflow.cn/v1")             # API 基础 URL
    
    # ===== Embedding 模型配置 =====
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "Qwen/Qwen3-Embedding-0.6B")  # 向量化模型名称
    
    @classmethod
    def validate(cls):
        """验证关键配置项是否已设置
        
        检查 LLM_API_KEY 是否存在，这是系统运行的必要条件。
        应在应用启动时调用此方法，尽早发现配置缺失问题。
        
        Raises:
            ValueError: 当 LLM_API_KEY 未设置时抛出
        """
        if not cls.LLM_API_KEY:
            raise ValueError("LLM_API_KEY not found in environment variables")
