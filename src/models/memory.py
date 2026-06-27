import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict


class UserMemory:
    def __init__(self, user_id: str, memory_path: str = "data/memory"):
        self.user_id = user_id
        self.memory_path = Path(memory_path) / user_id
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.conversations: List[Dict[str, Any]] = []
        self.preferences: Dict[str, Any] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.skill_feedback: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.context: Dict[str, Any] = {}
        self._load()

    def _load(self):
        pref_file = self.memory_path / "preferences.json"
        if pref_file.exists():
            with open(pref_file, "r", encoding="utf-8") as f:
                self.preferences = json.load(f)
        ctx_file = self.memory_path / "context.json"
        if ctx_file.exists():
            with open(ctx_file, "r", encoding="utf-8") as f:
                self.context = json.load(f)
        conv_file = self.memory_path / "conversations.jsonl"
        if conv_file.exists():
            with open(conv_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.conversations.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        task_file = self.memory_path / "task_history.jsonl"
        if task_file.exists():
            with open(task_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.task_history.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

    def _save_preferences(self):
        with open(self.memory_path / "preferences.json", "w", encoding="utf-8") as f:
            json.dump(self.preferences, f, ensure_ascii=False, indent=2)

    def _save_context(self):
        with open(self.memory_path / "context.json", "w", encoding="utf-8") as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)

    def add_conversation(self, role: str, content: str, metadata: Dict[str, Any] = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content[:500],
            "metadata": metadata or {}
        }
        self.conversations.append(entry)
        with open(self.memory_path / "conversations.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def add_task_record(self, task_id: str, summary: Dict[str, Any]):
        record = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "route": summary.get("routing", {}).get("route", ""),
            "skill_chain": summary.get("skill_chain", []),
            "satisfied": summary.get("evaluation", {}).get("satisfied", False),
            "score": summary.get("evaluation", {}).get("overall_score", 0),
            "user_feedback": summary.get("user_feedback", ""),
            "summary": summary.get("response", "")[:200]
        }
        self.task_history.append(record)
        with open(self.memory_path / "task_history.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def update_preferences(self, key: str, value: Any):
        self.preferences[key] = value
        self._save_preferences()

    def get_preferences(self) -> Dict[str, Any]:
        return self.preferences.copy()

    def update_context(self, key: str, value: Any):
        self.context[key] = value
        self._save_context()

    def get_context(self) -> Dict[str, Any]:
        return self.context.copy()

    def record_skill_feedback(self, skill_name: str, feedback: str, rating: int):
        self.skill_feedback[skill_name].append({
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback,
            "rating": rating
        })

    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.conversations[-limit:]

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.task_history[-limit:]

    def get_skill_feedback_stats(self, skill_name: str) -> Dict[str, Any]:
        records = self.skill_feedback.get(skill_name, [])
        if not records:
            return {"total": 0, "avg_rating": 0, "recent": []}
        ratings = [r["rating"] for r in records if r.get("rating")]
        return {
            "total": len(records),
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "recent": records[-5:]
        }

    def get_user_profile(self) -> Dict[str, Any]:
        industry = self.preferences.get("industry", "")
        region = self.preferences.get("region", "")
        focus_keywords = self.preferences.get("focus_keywords", [])
        task_routes = [t.get("route") for t in self.task_history[-20:]]
        route_counts = {}
        for r in task_routes:
            route_counts[r] = route_counts.get(r, 0) + 1
        return {
            "user_id": self.user_id,
            "industry": industry,
            "region": region,
            "focus_keywords": focus_keywords,
            "total_conversations": len(self.conversations),
            "total_tasks": len(self.task_history),
            "recent_route_distribution": route_counts,
            "preferences": self.preferences,
        }


class MemoryManager:
    def __init__(self, memory_path: str = "data/memory"):
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self._users: Dict[str, UserMemory] = {}

    def get_user_memory(self, user_id: str) -> UserMemory:
        if user_id not in self._users:
            self._users[user_id] = UserMemory(user_id, str(self.memory_path))
        return self._users[user_id]

    def get_or_create_user_memory(self, user_id: str) -> UserMemory:
        return self.get_user_memory(user_id)


_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager