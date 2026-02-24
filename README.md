# 🛡️ 多智能体安全分析系统

一个基于多智能体架构的网络安全威胁智能分析系统，集成 RAG 知识库问答功能。系统通过路由智能体与多个领域专家智能体协同，结合大语言模型（Qwen，SiliconFlow API）实现自动化安全告警分析；同时提供基于向量检索的 RAG 问答模块，支持本地文档上传和语义问答。

## 🌟 系统功能

- **🤖 多智能体告警分析**：路由智能体智能分发 + 三大领域专家智能体深度分析（Web攻击 / 漏洞利用 / 非法连接）
- **📚 RAG 知识库问答**：上传文档 → Embedding 向量化（Qwen3-Embedding-8B）→ ChromaDB 本地存储 → 语义检索 → LLM 生成答案
- **⚡ 全异步后端**：基于 asyncio，FastAPI 高性能异步 API 服务
- **📊 可视化前端**：Streamlit 多页面应用，包含分析、历史、仪表板、RAG 四大功能模块
- **🔄 优雅降级**：LLM 不可用时自动切换基于规则的告警分析

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  Streamlit 前端  (端口 8501)                                         │
│  ├─ 🔍 告警分析     ├─ 📊 分析历史                                     │
│  ├─ 📈 系统仪表板   └─ 📚 RAG 知识库问答                               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP API
┌───────────────────────────▼─────────────────────────────────────────┐
│  FastAPI 后端  (端口 8000)                                            │
│  ├─ /api/analyze             → 告警分析                              │
│  ├─ /api/history, /api/stats → 历史 & 统计                           │
│  ├─ /api/health              → 健康检查                               │
│  └─ /api/rag/*               → RAG 上传 / 问答 / 管理                 │
└────────────────┬──────────────────────────┬────────────────────────-┘
                 │                          │
    ┌────────────▼───────────┐   ┌──────────▼──────────────────────┐
    │  多智能体系统 (src/)    │   │  RAG 服务                         │
    │  RouterAgent           │   │  ├─ Qwen3-Embedding-8B (向量化)  │
    │  ExpertAgent × 3       │   │  ├─ ChromaDB (本地向量库)         │
    │     └─ Qwen LLM        │   │  └─ Qwen LLM (生成答案)          │
    └────────────────────────┘   └─────────────────────────────────┘
```

## 📁 项目结构

```
multi-agent-base/
├── backend/                        # FastAPI 后端服务
│   ├── main.py                    # 应用入口，生命周期管理
│   ├── config.py                  # 配置管理（读取 .env）
│   ├── api/
│   │   ├── routes/
│   │   │   ├── analysis.py       # 告警分析 + 历史记录 API
│   │   │   ├── stats.py          # 统计信息 + 健康检查 API
│   │   │   └── rag.py            # RAG 上传 / 问答 / 管理 API
│   │   └── models/
│   │       └── schemas.py        # Pydantic 数据模型
│   └── services/
│       ├── agent_service.py      # 多智能体服务封装
│       ├── memory_storage.py     # 内存历史存储
│       └── rag_service.py        # RAG 核心服务（分块/Embedding/检索/生成）
│
├── frontend/                       # Streamlit 前端
│   ├── app.py                     # 主页面（系统介绍 + 导航）
│   ├── pages/
│   │   ├── 1_🔍_Alert_Analysis.py    # 告警分析页面
│   │   ├── 2_📊_Analysis_History.py  # 分析历史页面
│   │   ├── 3_📚_RAG_问答.py          # RAG 知识库问答页面
│   │   └── 4_📈_System_Dashboard.py  # 系统仪表板页面
│   └── utils/
│       └── api_client.py          # 前端 HTTP 客户端封装
│
├── src/                            # 多智能体核心引擎
│   ├── agents/
│   │   ├── optimized_router.py   # 路由智能体（关键词 + 正则规则）
│   │   ├── optimized_expert.py   # 专家智能体（LLM 分析 + 规则降级）
│   │   └── optimized_system.py   # 多智能体协调器
│   ├── models/
│   │   ├── api_client.py         # 异步 LLM API 客户端（httpx）
│   │   └── llm_inference.py      # LLM 推理封装（全局单例）
│   └── utils/
│       ├── config.py             # 配置读取工具
│       └── structured_logger.py  # JSONL 结构化日志
│
├── logs/                           # 运行日志（Docker volume 持久化）
├── chroma_db/                      # ChromaDB 向量库（Docker volume 持久化）
│
├── Dockerfile                      # Docker 镜像构建配置
├── docker-compose.yml              # 容器编排配置
├── supervisord.conf                # 进程管理（后端 + 前端同时运行）
├── start_backend.py               # 本地后端启动脚本
├── start_frontend.py              # 本地前端启动脚本
├── requirements.txt               # Python 依赖
└── .env                            # 环境变量（不提交 Git）
```

## 🚀 快速开始（Docker，推荐）

### 1. 配置环境变量

编辑根目录 `.env` 文件，填入 API 密钥：

```env
# LLM（对话模型）
LLM_API_KEY=your_siliconflow_api_key
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
MODEL_URL=https://api.siliconflow.cn/v1

# Embedding（RAG 功能）
EMBEDDING_API_KEY=your_siliconflow_api_key
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_URL=https://api.siliconflow.cn/v1
```

### 2. 构建并启动容器

```bash
docker-compose up -d --build
```

### 3. 访问服务

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:8501 |
| 后端 API 文档（Swagger） | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/health |

## 📖 使用指南

### 🔍 告警分析

1. 进入「🔍 告警分析」页面
2. 选择攻击类型、输入攻击载荷和 IP 地址（或从预设示例快速加载）
3. 点击「🚀 开始分析」
4. 查看：攻击技术识别、风险评分（0-10）、威胁等级、防御建议、路由决策、性能指标

### 📚 RAG 知识库问答

1. 进入「📚 RAG 知识库问答」页面
2. 在「文档上传」区粘贴文本或上传 `.txt`/`.md` 文件，点击「入库」
3. 在「知识库问答」区输入问题，点击「🔍 提问」
4. 查看 LLM 基于文档内容生成的答案及参考原文片段
5. 侧边栏可查看当前知识库状态，支持清空操作

> **数据持久化**：ChromaDB 向量库数据通过 Docker volume 持久化，重启容器后文档不丢失。

### 📊 分析历史 & 📈 系统仪表板

- 历史页面：查看所有告警分析记录，支持按威胁等级、攻击类型过滤
- 仪表板：威胁等级分布饼图、攻击类型分布柱状图、关键统计指标

## 🔧 API 端点

### 多智能体分析

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/analyze` | 提交告警进行智能分析 |
| `GET` | `/api/history` | 获取分析历史（支持过滤分页） |
| `GET` | `/api/stats` | 获取系统统计信息 |
| `GET` | `/api/health` | 健康检查 |

### RAG 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rag/upload` | 上传文档文本，分块入库 |
| `POST` | `/api/rag/query` | 知识库问答（检索 + LLM 生成） |
| `DELETE` | `/api/rag/clear` | 清空知识库 |
| `GET` | `/api/rag/stats` | 知识库统计（文档块数量等） |

## 🤖 智能体详解

### 路由智能体（RouterAgent）

- 基于 **关键词匹配 + 正则模式** 的规则引擎
- 自动计算各类别路由分数（关键词权重 0.6 + 正则权重 0.4），选择最高分
- 支持三大路由方向：`web_attack` / `vulnerability_attack` / `illegal_connection`

### 专家智能体（ExpertAgent × 3）

| 专家类型 | 擅长领域 | 典型场景 |
|----------|----------|----------|
| `web_attack` | Web 安全 | SQL注入、XSS、命令注入、目录遍历、Webshell |
| `vulnerability_attack` | 漏洞利用 | CVE漏洞、Exploit、Shellcode、缓冲区溢出 |
| `illegal_connection` | 非法网络连接 | C2通信、僵尸网络、DDoS、代理隧道 |

每个专家智能体：领域专属 Prompt → Qwen LLM API → JSON 解析 → **LLM 不可用时自动降级为规则分析**

## 🧠 RAG 实现原理

```
文档入库流程：
  文本 → 分块（500字/块，50字重叠） → Qwen3-Embedding-8B 向量化 → ChromaDB 持久化存储

问答流程：
  问题 → Embedding → ChromaDB 余弦相似度检索（top-k 块）→ Context 拼接 → Qwen LLM 生成答案
```

## 🔐 安全说明

- API 密钥存储在 `.env` 文件中，已加入 `.gitignore`，不会提交到版本控制
- 后端 CORS 仅允许来自 Streamlit 前端的跨域请求
- 告警分析历史保存在**内存**中，服务重启后清空
- RAG 向量库数据**持久化**在 `chroma_db/` 目录（Docker volume 挂载）

---

**版本**: 2.0.0 | **更新**: 2026-02-25
