#!/usr/bin/env python3
"""
前端 API 客户端 - 简化版（无RAG增强）

本模块封装了 Streamlit 前端与 FastAPI 后端之间的 HTTP 通信。
使用同步的 requests 库（Streamlit 本身就是同步框架）。

提供的 API 方法：
1. health_check(): 健康检查，检测后端是否在线
2. analyze_alert(): 提交告警进行分析
3. get_analysis_history(): 获取分析历史记录
4. get_stats(): 获取系统统计数据

错误处理策略：
- HTTP 5xx 错误：抛出"服务器错误"异常
- HTTP 4xx 错误：提取 detail 字段抛出"请求错误"异常
- 网络连接失败：health_check 返回 False，其他方法向上抛出异常
"""
import requests
from typing import Dict, Any, List, Optional
from loguru import logger


class APIClient:
    """FastAPI 后端客户端
    
    封装所有与后端 API 的 HTTP 交互，为 Streamlit 页面提供简洁的调用接口。
    所有方法都是同步的，适配 Streamlit 的同步运行模型。
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化 API 客户端
        
        Args:
            base_url: 后端服务的基础 URL（默认本地 8000 端口）
        """
        self.base_url = base_url.rstrip("/")   # 去除尾部斜杠，避免拼接 URL 时出现双斜杠
        self.timeout = 60                       # 请求超时时间（秒），分析可能需要较长时间
    
    def _handle_response(self, response: requests.Response) -> Any:
        """统一处理 API 响应
        
        检查 HTTP 状态码，成功时返回 JSON 数据，失败时抛出友好的异常信息。
        
        错误处理逻辑：
        - 2xx 状态码：返回 response.json()
        - 5xx 状态码：抛出"服务器错误"，说明是后端问题
        - 4xx 状态码：从响应体中提取 detail 字段，提供更具体的错误信息
        
        Args:
            response: requests 库的响应对象
            
        Returns:
            响应体的 JSON 数据（字典或列表）
            
        Raises:
            Exception: HTTP 错误或响应解析失败时抛出
        """
        try:
            response.raise_for_status()      # 非 2xx 状态码时抛出 HTTPError
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"API请求失败: {e}")
            if response.status_code >= 500:
                raise Exception(f"服务器错误: {response.status_code}")
            elif response.status_code >= 400:
                # 尝试从响应体中提取 FastAPI 的 detail 错误信息
                detail = response.json().get("detail", "未知错误")
                raise Exception(f"请求错误: {detail}")
            raise
        except Exception as e:
            logger.error(f"处理响应失败: {e}")
            raise
    
    def health_check(self) -> bool:
        """健康检查 - 检测后端服务是否在线
        
        调用 GET /api/health 端点，通过状态码判断后端是否正常运行。
        使用较短的超时时间（5秒），快速返回结果。
        
        Returns:
            bool: 后端在线返回 True，否则返回 False
        """
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            return response.status_code == 200
        except:
            # 连接失败（超时、拒绝连接等）直接返回 False
            return False
    
    def analyze_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """提交安全告警进行分析
        
        发送 POST 请求到 /api/analyze，将告警数据作为 JSON 请求体。
        
        Args:
            alert_data: 告警数据字典，包含 attack_type, payload, source_ip, dest_ip 等
            
        Returns:
            dict: 完整的分析结果（AnalysisResult 格式）
        """
        url = f"{self.base_url}/api/analyze"
        response = requests.post(url, json=alert_data, timeout=self.timeout)
        return self._handle_response(response)
    
    def get_analysis_history(
        self,
        limit: int = 50,
        offset: int = 0,
        threat_level: Optional[str] = None,
        attack_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取分析历史记录
        
        发送 GET 请求到 /api/history，支持通过 Query 参数进行过滤。
        
        Args:
            limit: 返回的最大记录数
            offset: 分页偏移量
            threat_level: 按威胁等级过滤（可选）
            attack_type: 按攻击类型过滤（可选）
            
        Returns:
            List[dict]: 历史记录列表（AnalysisHistory 格式）
        """
        url = f"{self.base_url}/api/history"
        # 构建查询参数，只在有值时才添加过滤参数
        params = {"limit": limit, "offset": offset}
        if threat_level:
            params["threat_level"] = threat_level
        if attack_type:
            params["attack_type"] = attack_type
        
        response = requests.get(url, params=params, timeout=self.timeout)
        return self._handle_response(response)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息
        
        发送 GET 请求到 /api/stats，获取威胁等级分布、攻击类型分布等统计数据。
        
        Returns:
            dict: 系统统计数据（SystemStats 格式）
        """
        url = f"{self.base_url}/api/stats"
        response = requests.get(url, timeout=self.timeout)
        return self._handle_response(response)
