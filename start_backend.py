import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    from backend.config import BackendConfig

    print("=" * 60)
    print("bid intelligence multi-agent system - Backend")
    print("=" * 60)
    print(f"address: http://{BackendConfig.API_HOST}:{BackendConfig.API_PORT}")
    print(f"API docs: http://{BackendConfig.API_HOST}:{BackendConfig.API_PORT}/docs")
    print(f"health: http://{BackendConfig.API_HOST}:{BackendConfig.API_PORT}/api/health")
    print("=" * 60)

    uvicorn.run(
        "backend.main:app",
        host=BackendConfig.API_HOST,
        port=BackendConfig.API_PORT,
        reload=BackendConfig.API_RELOAD,
        log_level=BackendConfig.LOG_LEVEL.lower()
    )