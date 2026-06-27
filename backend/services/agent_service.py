from typing import Optional
from loguru import logger

from src.agents.orchestrator import MultiAgentOrchestrator
from src.utils.docker_manager import get_docker_manager


class AgentService:
    def __init__(self):
        self.orchestrator: Optional[MultiAgentOrchestrator] = None
        self.is_initialized = False
        self.docker_manager = get_docker_manager()

    async def initialize(self):
        if self.is_initialized:
            logger.info("agent service already initialized")
            return
        try:
            logger.info("initializing agent service...")
            self.orchestrator = MultiAgentOrchestrator()
            await self.orchestrator.initialize()
            self.is_initialized = True
            logger.info("agent service initialized")
        except Exception as e:
            logger.error(f"agent service init failed: {e}")
            raise

    async def chat(self, message: str, user_id: str = "", session_id: str = "", context: dict = None) -> dict:
        if not self.is_initialized:
            raise RuntimeError("agent service not initialized")
        return await self.orchestrator.chat(message, user_id=user_id, session_id=session_id, context=context)

    async def process_feedback(self, feedback: str, task_id: str, user_id: str = "", deviation_type: str = None, rating: int = None) -> dict:
        if not self.is_initialized:
            raise RuntimeError("agent service not initialized")
        return await self.orchestrator.process_feedback(feedback, task_id, user_id, deviation_type, rating)

    def get_skills(self) -> list:
        if not self.is_initialized:
            return []
        return self.orchestrator.get_skills()

    def get_evolution_history(self, agent_type: str = None, skill_name: str = None) -> list:
        if not self.is_initialized:
            return []
        return self.orchestrator.get_evolution_history(agent_type, skill_name)

    async def create_user_container(self, user_id: str) -> dict:
        return await self.docker_manager.create_user_container(user_id)

    async def stop_user_container(self, user_id: str) -> dict:
        return await self.docker_manager.stop_user_container(user_id)

    async def remove_user_container(self, user_id: str) -> dict:
        return await self.docker_manager.remove_user_container(user_id)

    async def get_container_status(self, user_id: str) -> dict:
        return await self.docker_manager.get_container_status(user_id)

    def get_stats(self) -> dict:
        if not self.is_initialized:
            return {}
        return self.orchestrator.get_stats()


_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AgentService()
    return _service_instance