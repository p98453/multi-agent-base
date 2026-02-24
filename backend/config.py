#!/usr/bin/env python3
"""
后端配置管理模块（Backend Config）

本模块集中管理后端服务的所有配置项，包括：
- API 服务配置（主机地址、端口、热重载）
- CORS 跨域配置（允许的前端来源地址）
- LLM 模型配置（从 .env 文件读取的 API Key 和模型参数）
- 日志配置

配置读取优先级：
  环境变量（.env 文件） > 代码中的默认值

使用方式：
    from backend.config import BackendConfig
    BackendConfig.validate()        # 启动时验证配置
    port = BackendConfig.API_PORT   # 读取配置值
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

class BackendConfig:
    """后端配置类
    
    使用类属性存储所有配置项，通过 BackendConfig.XXX 直接访问。
    所有配置在模块加载时初始化，运行期间不会改变。
    """
    
    # 项目根目录路径（config.py 的上两级目录）
    # 用于构建其他文件的绝对路径
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # ===== API 服务配置 =====
    API_HOST = os.getenv("API_HOST", "0.0.0.0")                             # 监听地址，0.0.0.0 表示接受所有网络接口的连接
    API_PORT = int(os.getenv("API_PORT", "8000"))                            # 监听端口，默认 8000
    API_RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"          # 是否启用热重载（代码修改后自动重启，开发环境使用）
    
    # ===== CORS 跨域配置 =====
    # 允许跨域请求的来源列表
    # Streamlit 前端默认运行在 8501 端口，需要允许其跨域调用后端 API
    CORS_ORIGINS = [
        "http://localhost:8501",    # Streamlit 默认端口
        "http://localhost:3000",    # 备用前端端口（如 React/Vue 开发服务器）
        "http://127.0.0.1:8501",   # localhost 的 IP 形式
    ]
    
    # ===== LLM 模型配置（从 .env 文件读取）=====
    LLM_API_KEY = os.getenv("LLM_API_KEY")      # SiliconFlow API 密钥
    MODEL_NAME = os.getenv("MODEL_NAME")          # 对话模型名称
    MODEL_URL = os.getenv("MODEL_URL")            # API 基础 URL
    
    # ===== Embedding 配置（RAG 功能使用）=====
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY"))   # 默认复用 LLM Key
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
    EMBEDDING_URL = os.getenv("EMBEDDING_URL", "https://api.siliconflow.cn/v1")
    
    # ChromaDB 本地持久化路径（相对于项目根目录）
    CHROMA_DB_PATH = str(BASE_DIR / "chroma_db")
    
    # ===== 日志配置 =====
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")    # 日志级别：DEBUG, INFO, WARNING, ERROR
    
    @classmethod
    def validate(cls):
        """验证必需的配置项是否已设置
        
        在应用启动时调用，检查所有必需的环境变量是否存在。
        缺少任何一个关键配置都会导致系统无法正常工作。
        
        Returns:
            bool: 验证通过返回 True
            
        Raises:
            ValueError: 当有必需的环境变量缺失时抛出，列出所有缺失项
        """
        # 定义必需的配置字段列表
        required_fields = ["LLM_API_KEY", "MODEL_NAME", "MODEL_URL"]
        missing = []
        
        # 逐一检查字段值是否为空
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)
        
        # 有缺失字段时抛出异常，列出所有缺失的配置名
        if missing:
            raise ValueError(f"缺少必需的环境变量: {', '.join(missing)}")
        
        return True
