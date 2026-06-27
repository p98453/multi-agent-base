import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.models.memory import get_memory_manager
from backend.config import BackendConfig


class CDPClient:
    def __init__(self):
        self.api_url = BackendConfig.CDP_API_URL
        self.api_key = BackendConfig.CDP_API_KEY
        self.crm_system = BackendConfig.CRM_SYSTEM
        self.memory_manager = get_memory_manager()

    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        user_memory = self.memory_manager.get_user_memory(user_id)
        cached_context = user_memory.get_context()
        crm_data = await self._fetch_crm_data(user_id)
        merged = {
            "user_id": user_id,
            "crm_data": crm_data,
            "system_preferences": {
                "industry": crm_data.get("industry", "") or cached_context.get("industry", ""),
                "region": crm_data.get("region", "") or cached_context.get("region", ""),
                "company_name": crm_data.get("company_name", ""),
                "company_type": crm_data.get("company_type", ""),
                "focus_categories": crm_data.get("focus_categories", []) or cached_context.get("focus_keywords", []),
                "budget_range": crm_data.get("typical_budget_range", {}),
            },
            "recent_activities": {
                "conversations": user_memory.get_recent_conversations(5),
                "tasks": user_memory.get_recent_tasks(5),
            },
            "user_profile": user_memory.get_user_profile(),
            "last_active": cached_context.get("last_active", datetime.now().isoformat()),
        }
        user_memory.update_context("last_active", datetime.now().isoformat())
        return merged

    async def _fetch_crm_data(self, user_id: str) -> Dict[str, Any]:
        if not self.api_url:
            return {}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/api/customers/{user_id}",
                    headers={"Authorization": f"Bearer {self.api_key}", "X-CRM-System": self.crm_system}
                )
                if response.status_code == 200:
                    return response.json().get("data", {})
        except Exception:
            pass
        return {}

    async def sync_to_crm(self, user_id: str, activity: Dict[str, Any]) -> bool:
        if not self.api_url:
            return False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/customers/{user_id}/activities",
                    headers={"Authorization": f"Bearer {self.api_key}", "X-CRM-System": self.crm_system},
                    json={
                        "activity_type": "ai_interaction",
                        "timestamp": datetime.now().isoformat(),
                        "details": activity
                    }
                )
                return response.status_code == 200
        except Exception:
            return False

    async def update_crm_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        if not self.api_url:
            return False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    f"{self.api_url}/api/customers/{user_id}",
                    headers={"Authorization": f"Bearer {self.api_key}", "X-CRM-System": self.crm_system},
                    json=updates
                )
                return response.status_code == 200
        except Exception:
            return False


def get_cdp_client() -> CDPClient:
    return CDPClient()