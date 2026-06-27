import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class BackendConfig:
    BASE_DIR = Path(__file__).resolve().parent.parent

    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"

    CORS_ORIGINS = [
        "http://localhost:8501",
        "http://localhost:3000",
        "http://127.0.0.1:8501",
    ]

    LLM_API_KEY = os.getenv("LLM_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME")
    MODEL_URL = os.getenv("MODEL_URL")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    CDP_API_URL = os.getenv("CDP_API_URL", "")
    CDP_API_KEY = os.getenv("CDP_API_KEY", "")
    CRM_SYSTEM = os.getenv("CRM_SYSTEM", "default")

    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "data/vector_db")
    CRAWLER_SCRIPTS_PATH = os.getenv("CRAWLER_SCRIPTS_PATH", "data/crawler_scripts")
    PPT_TEMPLATES_PATH = os.getenv("PPT_TEMPLATES_PATH", "data/ppt_templates")
    DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "data/documents")

    DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "bid-intelligence-agent")
    DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "bid-agent-network")
    USER_CONTAINER_PREFIX = os.getenv("USER_CONTAINER_PREFIX", "bid-user-")

    MAX_LOOPS = int(os.getenv("MAX_LOOPS", "3"))
    EVALUATION_THRESHOLD = float(os.getenv("EVALUATION_THRESHOLD", "7.0"))
    EVOLUTION_ENABLED = os.getenv("EVOLUTION_ENABLED", "True").lower() == "true"

    SKILL_EVOLUTION_PATH = os.getenv("SKILL_EVOLUTION_PATH", "data/skill_evolution")

    @classmethod
    def validate(cls):
        required_fields = ["LLM_API_KEY", "MODEL_NAME", "MODEL_URL"]
        missing = []
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)
        if missing:
            raise ValueError(f"missing env vars: {', '.join(missing)}")
        return True