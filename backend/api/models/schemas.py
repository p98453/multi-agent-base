#!/usr/bin/env python3
"""
API 数据模型定义 - 简化版（无RAG增强）

本模块使用 Pydantic 定义 API 的请求和响应数据模型。
Pydantic 提供运行时数据验证和自动生成 JSON Schema，
使得 FastAPI 能够自动校验请求参数并生成 Swagger 文档。

模型层级关系：
  AlertData（请求） → 后端处理 → AnalysisResult（响应）
                                    ├── RoutingInfo（路由信息）
                                    ├── ExpertAnalysis（专家分析）
                                    └── PerformanceMetrics（性能指标）

其他模型：
  - AnalysisHistory: 历史记录列表项
  - SystemStats: 系统统计信息
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AlertData(BaseModel):
    """告警输入数据模型 - 对应前端提交的告警表单
    
    定义了前端发送分析请求时必须和可选提供的字段。
    使用 Pydantic 的 Field 进行字段描述和默认值设置。
    
    Attributes:
        attack_type: 攻击类型描述（必填），如 "SQL注入"、"XSS攻击"
        payload: 攻击载荷内容（必填），包含具体的攻击代码或数据
        source_ip: 攻击来源 IP 地址（可选，默认 "0.0.0.0"）
        dest_ip: 攻击目标 IP 地址（可选，默认 "0.0.0.0"）
        protocol: 网络协议类型（可选，默认 "HTTP"）
        additional_info: 附加信息字典（可选），存放自定义扩展数据
    """
    attack_type: str = Field(..., description="攻击类型")                     # ... 表示必填字段
    payload: str = Field(..., description="攻击载荷")
    source_ip: str = Field("0.0.0.0", description="源IP地址")
    dest_ip: str = Field("0.0.0.0", description="目标IP地址")
    protocol: Optional[str] = Field("HTTP", description="协议类型")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="附加信息")

    class Config:
        """Pydantic 模型配置 - 提供 Swagger 文档中的请求示例"""
        json_schema_extra = {
            "example": {
                "attack_type": "SQL注入",
                "payload": "SELECT * FROM users WHERE id='1' UNION SELECT username, password FROM admin--",
                "source_ip": "192.168.1.100",
                "dest_ip": "10.0.0.5",
                "protocol": "HTTP"
            }
        }


class RoutingInfo(BaseModel):
    """路由信息模型 - 路由智能体的决策结果
    
    Attributes:
        selected_route: 选择的路由目标（专家类型），如 'web_attack'
        confidence: 路由置信度，范围 0.0~1.0
    """
    selected_route: str
    confidence: float


class ExpertAnalysis(BaseModel):
    """专家分析结果模型 - 专家智能体的分析输出
    
    Attributes:
        attack_technique: 识别出的攻击技术名称，如 "SQL注入"
        risk_score: 风险评分，范围 0.0~10.0
        threat_level: 威胁等级，"高危"/"中危"/"低危"
        recommendations: 防御/修复建议列表
        analysis: 详细分析文本
    """
    attack_technique: str
    risk_score: float
    threat_level: str
    recommendations: List[str]
    analysis: str


class PerformanceMetrics(BaseModel):
    """性能指标模型 - 记录分析各阶段的耗时
    
    Attributes:
        total_time_ms: 端到端总耗时（毫秒）
        routing_time_ms: 路由决策阶段耗时（毫秒）
        expert_time_ms: 专家分析阶段耗时（毫秒）
    """
    total_time_ms: int
    routing_time_ms: int
    expert_time_ms: int


class AnalysisResult(BaseModel):
    """完整分析结果模型 - /api/analyze 端点的响应格式
    
    整合路由信息、专家分析和性能指标的完整响应结构。
    
    Attributes:
        success: 分析是否成功
        task_id: 任务唯一标识（UUID）
        analysis_id: 分析记录 ID（由内存存储生成）
        timestamp: 分析完成时间戳
        routing: 路由决策信息
        expert_analysis: 专家分析结果
        performance: 性能指标
        message: 附加消息（如 "分析完成"）
    """
    success: bool
    task_id: str = Field(..., description="任务ID")
    analysis_id: Optional[str] = Field(None, description="分析记录ID")
    timestamp: float
    routing: RoutingInfo
    expert_analysis: ExpertAnalysis
    performance: PerformanceMetrics
    message: Optional[str] = None


class AnalysisHistory(BaseModel):
    """分析历史记录模型 - /api/history 端点的列表项格式
    
    用于历史记录查询接口，只包含摘要字段，不返回完整分析详情。
    
    Attributes:
        analysis_id: 分析记录唯一标识
        attack_type: 攻击类型
        threat_level: 威胁等级
        risk_score: 风险评分
        timestamp: 分析时间戳
    """
    analysis_id: str
    attack_type: str
    threat_level: str
    risk_score: float
    timestamp: float


class SystemStats(BaseModel):
    """系统统计信息模型 - /api/stats 端点的响应格式
    
    提供系统整体运行状况的统计数据。
    
    Attributes:
        total_analyses: 系统启动以来的总分析次数
        threat_level_distribution: 威胁等级分布，如 {"高危": 5, "中危": 3, "低危": 2}
        attack_type_distribution: 攻击类型分布，如 {"SQL注入": 4, "XSS攻击": 3}
    """
    total_analyses: int
    threat_level_distribution: Dict[str, int]
    attack_type_distribution: Dict[str, int]
