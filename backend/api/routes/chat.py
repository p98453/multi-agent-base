from fastapi import APIRouter, HTTPException
from loguru import logger

from backend.api.models.schemas import (
    ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse,
    SkillListResponse, SkillUpdateRequest, SkillInfo,
    DockerContainerRequest, DockerContainerResponse, HealthResponse
)
from backend.services.agent_service import get_agent_service

router = APIRouter(prefix="/api", tags=["Bid Intelligence"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"message received: {request.message[:100]}")
        service = get_agent_service()
        result = await service.chat(
            request.message,
            user_id=request.user_id or "",
            session_id=request.session_id or "",
            context=request.context
        )
        logger.info(f"task completed: {result['task_id']}")
        return ChatResponse(
            success=result.get("success", True),
            task_id=result["task_id"],
            response=result["response"],
            routing=result.get("routing"),
            agent_info=result.get("agent_info"),
            evaluation=result.get("evaluation"),
            performance=result.get("performance"),
            loop_history=result.get("loop_history"),
            skill_chain=result.get("skill_chain"),
        )
    except Exception as e:
        logger.error(f"processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"processing failed: {str(e)}")


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    try:
        logger.info(f"feedback received for task: {request.task_id}")
        service = get_agent_service()
        result = await service.process_feedback(
            request.feedback,
            request.task_id,
            user_id=request.user_id or "",
            deviation_type=request.deviation_type,
            rating=request.rating
        )
        return FeedbackResponse(
            success=result.get("success", True),
            message=result.get("evolution", {}).get("message", "feedback processed"),
            evolution_applied=result.get("evolution", {}).get("applied", False),
            updated_skills=result.get("evolution", {}).get("updated_skills", []),
            root_cause=result.get("evolution", {}).get("root_cause"),
        )
    except Exception as e:
        logger.error(f"feedback processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"feedback processing failed: {str(e)}")


@router.get("/skills", response_model=SkillListResponse)
async def list_skills():
    try:
        service = get_agent_service()
        skills = service.get_skills()
        skill_infos = [
            SkillInfo(
                name=s.get("name", ""),
                agent_type=s.get("agent_type", ""),
                description=s.get("description", ""),
                version=s.get("version", 1),
                evolution_count=s.get("evolution_count", 0),
                last_evolved=s.get("last_evolved"),
                parameters=s.get("parameters", {}),
                prompt_template=s.get("prompt_template"),
            )
            for s in skills
        ]
        return SkillListResponse(success=True, skills=skill_infos, total_count=len(skill_infos))
    except Exception as e:
        logger.error(f"skill listing failed: {e}")
        raise HTTPException(status_code=500, detail=f"skill listing failed: {str(e)}")


@router.get("/skills/evolution")
async def get_evolution_history(agent_type: str = None, skill_name: str = None):
    try:
        service = get_agent_service()
        history = service.get_evolution_history(agent_type, skill_name)
        return {"success": True, "history": history, "total": len(history)}
    except Exception as e:
        logger.error(f"evolution history query failed: {e}")
        raise HTTPException(status_code=500, detail=f"evolution history query failed: {str(e)}")


@router.post("/docker/container")
async def manage_docker_container(request: DockerContainerRequest):
    try:
        service = get_agent_service()
        action = request.action
        user_id = request.user_id
        if action == "create":
            result = await service.create_user_container(user_id)
        elif action == "stop":
            result = await service.stop_user_container(user_id)
        elif action == "remove":
            result = await service.remove_user_container(user_id)
        elif action == "status":
            result = await service.get_container_status(user_id)
        else:
            return DockerContainerResponse(success=False, message=f"unknown action: {action}")
        return DockerContainerResponse(
            success=result.get("success", False),
            container_id=result.get("container_id"),
            status=result.get("status"),
            port=result.get("port"),
            message=result.get("message", ""),
        )
    except Exception as e:
        logger.error(f"docker container management failed: {e}")
        raise HTTPException(status_code=500, detail=f"docker management failed: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()