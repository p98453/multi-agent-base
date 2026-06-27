import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.config import BackendConfig


class DockerManager:
    def __init__(self):
        self.image = BackendConfig.DOCKER_IMAGE
        self.network = BackendConfig.DOCKER_NETWORK
        self.container_prefix = BackendConfig.USER_CONTAINER_PREFIX
        self._containers: Dict[str, Dict[str, Any]] = {}
        self._state_file = Path("data/docker_state.json")
        self._load_state()

    def _load_state(self):
        if self._state_file.exists():
            with open(self._state_file, "r", encoding="utf-8") as f:
                self._containers = json.load(f)

    def _save_state(self):
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(self._containers, f, ensure_ascii=False, indent=2)

    async def create_user_container(self, user_id: str) -> Dict[str, Any]:
        container_id = f"{self.container_prefix}{user_id}"
        if container_id in self._containers:
            existing = self._containers[container_id]
            if existing.get("status") == "running":
                return {
                    "success": True,
                    "container_id": container_id,
                    "status": "running",
                    "port": existing.get("port", 8000),
                    "message": "container already running"
                }
        port = 8000 + len(self._containers)
        container = {
            "container_id": container_id,
            "user_id": user_id,
            "status": "running",
            "port": port,
            "created_at": datetime.now().isoformat(),
            "image": self.image,
            "network": self.network,
        }
        self._containers[container_id] = container
        self._save_state()
        return {
            "success": True,
            "container_id": container_id,
            "status": "running",
            "port": port,
            "message": "container created successfully"
        }

    async def stop_user_container(self, user_id: str) -> Dict[str, Any]:
        container_id = f"{self.container_prefix}{user_id}"
        if container_id not in self._containers:
            return {"success": False, "container_id": None, "status": "not_found", "port": None, "message": "container not found"}
        self._containers[container_id]["status"] = "stopped"
        self._save_state()
        return {"success": True, "container_id": container_id, "status": "stopped", "port": None, "message": "container stopped"}

    async def remove_user_container(self, user_id: str) -> Dict[str, Any]:
        container_id = f"{self.container_prefix}{user_id}"
        if container_id not in self._containers:
            return {"success": False, "container_id": None, "status": "not_found", "port": None, "message": "container not found"}
        removed = self._containers.pop(container_id)
        self._save_state()
        return {"success": True, "container_id": container_id, "status": "removed", "port": None, "message": f"container removed, was on port {removed.get('port')}"}

    async def get_container_status(self, user_id: str) -> Dict[str, Any]:
        container_id = f"{self.container_prefix}{user_id}"
        if container_id not in self._containers:
            return {"success": False, "container_id": None, "status": "not_found", "port": None, "message": "container not found"}
        c = self._containers[container_id]
        return {"success": True, "container_id": container_id, "status": c.get("status"), "port": c.get("port"), "message": f"status: {c.get('status')}"}

    def list_containers(self) -> List[Dict[str, Any]]:
        return list(self._containers.values())


_global_docker_manager: Optional[DockerManager] = None


def get_docker_manager() -> DockerManager:
    global _global_docker_manager
    if _global_docker_manager is None:
        _global_docker_manager = DockerManager()
    return _global_docker_manager