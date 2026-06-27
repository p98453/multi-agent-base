import requests
from typing import Dict, Any, List


class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 180

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def chat(self, message: str, user_id: str = "", session_id: str = "", context: dict = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        payload = {"message": message, "user_id": user_id, "session_id": session_id, "context": context or {}}
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def submit_feedback(self, task_id: str, feedback: str, user_id: str = "", deviation_type: str = None, rating: int = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/feedback"
        payload = {
            "task_id": task_id,
            "feedback": feedback,
            "user_id": user_id,
            "deviation_type": deviation_type,
            "rating": rating
        }
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()

    def list_skills(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/skills"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_evolution_history(self, agent_type: str = None, skill_name: str = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/skills/evolution"
        params = {}
        if agent_type:
            params["agent_type"] = agent_type
        if skill_name:
            params["skill_name"] = skill_name
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def manage_container(self, user_id: str, action: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/docker/container"
        payload = {"user_id": user_id, "action": action}
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()