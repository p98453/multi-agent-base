from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., description="user message", min_length=1)
    user_id: Optional[str] = Field(None, description="user identifier for CDP/CRM integration")
    session_id: Optional[str] = Field(None, description="conversation session id")
    context: Optional[Dict[str, Any]] = Field(None, description="additional context from CRM")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "帮我爬取中国政府采购网最近一周关于医疗设备的招标公告",
                "user_id": "user_001",
                "session_id": "sess_abc123"
            }
        }


class ChatResponse(BaseModel):
    success: bool
    task_id: str
    response: str = Field(..., description="agent full response content")
    routing: Optional[dict] = Field(None, description="gateway routing decision details")
    agent_info: Optional[dict] = Field(None, description="agent execution details including skill chain")
    evaluation: Optional[dict] = Field(None, description="quality evaluation results")
    performance: Optional[dict] = Field(None, description="performance metrics per stage")
    loop_history: Optional[List[dict]] = Field(None, description="history of each loop iteration")
    skill_chain: Optional[List[str]] = Field(None, description="chain of skills used in this task")


class FeedbackRequest(BaseModel):
    task_id: str = Field(..., description="task to provide feedback for")
    user_id: Optional[str] = Field(None, description="user identifier")
    feedback: str = Field(..., description="user feedback text describing what was wrong")
    deviation_type: Optional[str] = Field(None, description="type of deviation: content|format|accuracy|completeness")
    rating: Optional[int] = Field(None, ge=1, le=10, description="user satisfaction rating 1-10")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "uuid-123",
                "feedback": "爬取结果缺少了江苏省的数据，需要补充",
                "deviation_type": "completeness",
                "rating": 5
            }
        }


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    evolution_applied: bool = False
    updated_skills: List[str] = Field(default_factory=list)
    root_cause: Optional[str] = None


class SkillInfo(BaseModel):
    name: str = Field(..., description="skill name")
    agent_type: str = Field(..., description="agent that owns this skill")
    description: str = Field(..., description="skill description")
    version: int = Field(1, description="skill version number")
    evolution_count: int = Field(0, description="times this skill has been evolved")
    last_evolved: Optional[str] = Field(None, description="last evolution timestamp")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="skill parameters schema")
    prompt_template: Optional[str] = Field(None, description="skill prompt template")


class SkillListResponse(BaseModel):
    success: bool
    skills: List[SkillInfo]
    total_count: int


class SkillUpdateRequest(BaseModel):
    skill_name: str = Field(..., description="skill to update")
    new_prompt_template: Optional[str] = Field(None)
    new_parameters: Optional[Dict[str, Any]] = Field(None)
    evolution_reason: str = Field(..., description="reason for this evolution")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "招投标情报分析多智能体系统"
    version: str = "2.0.0"


class DockerContainerRequest(BaseModel):
    user_id: str = Field(..., description="user identifier for dedicated container")
    action: str = Field(..., description="action: create|stop|remove|status")


class DockerContainerResponse(BaseModel):
    success: bool
    container_id: Optional[str] = None
    status: Optional[str] = None
    port: Optional[int] = None
    message: str