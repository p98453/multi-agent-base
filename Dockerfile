# ============================================
# 多智能体安全分析系统 Docker 镜像
# 包含 FastAPI 后端 (8000) + Streamlit 前端 (8501)
# ============================================

# ---------- 基础镜像 ----------
FROM python:3.11-slim

# ---------- 系统依赖 ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ---------- 工作目录 ----------
WORKDIR /app

# ---------- 安装 Python 依赖 ----------
# 先复制 requirements.txt 利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- 复制项目代码 ----------
COPY . .

# ---------- 复制 supervisord 配置 ----------
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ---------- 创建日志目录 ----------
RUN mkdir -p /app/logs

# ---------- 暴露端口 ----------
# 8000: FastAPI 后端 API
# 8501: Streamlit 前端界面
EXPOSE 8000 8501

# ---------- 启动命令 ----------
# 使用 supervisord 同时管理后端和前端进程
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
