import sys
import os
import subprocess

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    print("=" * 60)
    print("bid intelligence multi-agent system - Frontend")
    print("=" * 60)
    print("frontend: http://localhost:8501")
    print("make sure backend is running: python start_backend.py")
    print("=" * 60)

    frontend_app = os.path.join(project_root, "frontend", "app.py")

    subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        frontend_app,
        "--server.port=8501",
        "--server.address=localhost"
    ])