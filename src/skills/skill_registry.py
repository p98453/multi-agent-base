import json
import copy
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


SKILLS_ROOT = Path(__file__).resolve().parent


def _parse_skill_md(file_path: Path) -> Dict[str, Any]:
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    frontmatter = yaml.safe_load(parts[1]) or {}
    prompt_template = parts[2].strip()
    skill_name = file_path.parent.name
    frontmatter.setdefault("name", skill_name)
    frontmatter["prompt_template"] = prompt_template
    frontmatter.setdefault("version", 1)
    frontmatter.setdefault("evolution_count", 0)
    frontmatter.setdefault("last_evolved", None)
    frontmatter.setdefault("intent_triggers", [])
    frontmatter.setdefault("parameters", {})
    frontmatter.setdefault("scripts_path", str(file_path.parent / "scripts"))
    frontmatter.setdefault("references_path", str(file_path.parent / "references"))
    frontmatter.setdefault("assets_path", str(file_path.parent / "assets"))
    return frontmatter


def _scan_skills() -> Dict[str, Dict[str, Dict[str, Any]]]:
    skills = {}
    for agent_dir in SKILLS_ROOT.iterdir():
        if not agent_dir.is_dir():
            continue
        if agent_dir.name in ("__pycache__",):
            continue
        agent_type = agent_dir.name
        agent_skills = {}
        for skill_dir in agent_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            skill_data = _parse_skill_md(skill_md)
            if skill_data:
                agent_skills[skill_dir.name] = skill_data
                for sub in ("scripts", "references", "assets"):
                    (skill_dir / sub).mkdir(exist_ok=True)
        if agent_skills:
            skills[agent_type] = agent_skills
    return skills


ALL_SKILLS = _scan_skills()


class SkillRegistry:
    def __init__(self, evolution_path: str = "data/skill_evolution"):
        self._skills: Dict[str, Dict[str, Dict[str, Any]]] = copy.deepcopy(ALL_SKILLS)
        self.evolution_path = Path(evolution_path)
        self.evolution_path.mkdir(parents=True, exist_ok=True)
        self._evolution_log: List[Dict[str, Any]] = []
        self._load_evolutions()

    def _load_evolutions(self):
        evo_file = self.evolution_path / "evolutions.jsonl"
        if evo_file.exists():
            with open(evo_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            self._evolution_log.append(record)
                            self._apply_evolution(record)
                        except json.JSONDecodeError:
                            pass

    def _apply_evolution(self, record: Dict[str, Any]):
        agent_type = record.get("agent_type")
        skill_name = record.get("skill_name")
        if agent_type in self._skills and skill_name in self._skills[agent_type]:
            skill = self._skills[agent_type][skill_name]
            if record.get("new_prompt_template"):
                skill["prompt_template"] = record["new_prompt_template"]
            if record.get("new_parameters"):
                skill["parameters"] = record["new_parameters"]
            skill["version"] = skill.get("version", 1) + 1
            skill["evolution_count"] = skill.get("evolution_count", 0) + 1
            skill["last_evolved"] = record.get("timestamp", datetime.now().isoformat())

    def get_skill(self, agent_type: str, skill_name: str) -> Optional[Dict[str, Any]]:
        return self._skills.get(agent_type, {}).get(skill_name)

    def get_agent_skills(self, agent_type: str) -> Dict[str, Dict[str, Any]]:
        return self._skills.get(agent_type, {})

    def list_all_skills(self) -> List[Dict[str, Any]]:
        result = []
        for agent_type, skills in self._skills.items():
            for name, skill in skills.items():
                result.append({
                    "name": name,
                    "agent_type": agent_type,
                    "description": skill.get("description", ""),
                    "version": skill.get("version", 1),
                    "evolution_count": skill.get("evolution_count", 0),
                    "last_evolved": skill.get("last_evolved"),
                    "parameters": skill.get("parameters", {}),
                    "prompt_template": skill.get("prompt_template", "")[:200],
                })
        return result

    def evolve_skill(self, agent_type: str, skill_name: str, new_prompt_template: Optional[str] = None, new_parameters: Optional[Dict[str, Any]] = None, reason: str = "") -> bool:
        if agent_type not in self._skills or skill_name not in self._skills[agent_type]:
            return False
        skill = self._skills[agent_type][skill_name]
        record = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": agent_type,
            "skill_name": skill_name,
            "old_version": skill.get("version", 1),
            "old_prompt_template": skill.get("prompt_template", "")[:200],
            "new_prompt_template": new_prompt_template[:200] if new_prompt_template else None,
            "new_parameters": new_parameters,
            "reason": reason,
        }
        self._apply_evolution(record)
        self._evolution_log.append(record)
        with open(self.evolution_path / "evolutions.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True

    def get_evolution_history(self, agent_type: Optional[str] = None, skill_name: Optional[str] = None) -> List[Dict[str, Any]]:
        result = self._evolution_log
        if agent_type:
            result = [r for r in result if r.get("agent_type") == agent_type]
        if skill_name:
            result = [r for r in result if r.get("skill_name") == skill_name]
        return result

    def find_skill_by_intent(self, intent: str) -> tuple:
        intent_lower = intent.lower()
        for agent_type, skills in self._skills.items():
            for name, skill in skills.items():
                triggers = skill.get("intent_triggers", [])
                for trigger in triggers:
                    if trigger in intent_lower:
                        return agent_type, name, skill
        gw_skills = self._skills.get("gateway", {})
        return "gateway", "fallback_default", gw_skills.get("fallback_default", {})

    def build_skill_prompt(self, agent_type: str, skill_name: str, context: Dict[str, Any] = None) -> str:
        skill = self.get_skill(agent_type, skill_name)
        if not skill:
            return ""
        template = skill.get("prompt_template", "")
        if context and template:
            for key, value in context.items():
                template = template.replace(f"{{{key}}}", str(value))
        return template


_global_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry


def reset_skill_registry():
    global _global_registry
    _global_registry = SkillRegistry()
    return _global_registry