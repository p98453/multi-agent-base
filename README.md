# 🛡️ 多智能体安全分析系统

一个基于**多智能体架构**的网络安全威胁智能分析系统，集成 RAG 知识库问答功能。系统使用 **LangChain** 框架进行 LLM 调用和 RAG 编排，使用 **LangGraph** 框架实现多智能体状态图编排（StateGraph），通过路由智能体与多个领域专家智能体协同，结合大语言模型（DeepSeek-V4-Flash，SiliconFlow API）实现自动化安全告警分析；同时提供基于 LangChain 向量检索的 RAG 问答模块，支持本地文档上传和语义问答。

## 🌟 系统功能

- **🤖 多智能体告警分析**：基于 **LangGraph StateGraph** 编排路由智能体 + 三大领域专家智能体（Web攻击 / 漏洞利用 / 非法连接）
- **📚 RAG 知识库问答**：基于 **LangChain LCEL 链** 实现上传文档 → RecursiveCharacterTextSplitter 分块 → OpenAIEmbeddings 向量化 → Chroma 存储 → 语义检索 → LLM 生成答案
- **⚡ 全异步后端**：基于 asyncio，FastAPI 高性能异步 API 服务
- **📊 可视化前端**：Streamlit 多页面应用，包含分析、历史、仪表板、RAG 四大功能模块
- **🔄 优雅降级**：LLM 不可用时自动切换基于规则的告警分析
- **🔗 LangChain 生态集成**：ChatOpenAI / OpenAIEmbeddings / Chroma / ChatPromptTemplate / LCEL Chain

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
    ┌────────────▼───────────────┐ ┌──────────▼──────────────────────┐
    │ LangGraph StateGraph       │ │  RAG 服务 (LangChain LCEL)       │
    │  route_node(RouterAgent)   │ │  ├─ OpenAIEmbeddings (向量化)    │
    │  expert_node(Expert × 3)   │ │  ├─ Chroma (向量库)              │
    │  aggregate_node(综合)      │ │  └─ ChatOpenAI (生成答案)        │
    │   └─ ChatOpenAI (LLM)      │ │                                  │
    └────────────────────────────┘ └──────────────────────────────────┘
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
│   │   ├── optimized_expert.py   # 专家智能体（LangChain LCEL + 规则降级）
│   │   └── optimized_system.py   # LangGraph StateGraph 编排器
│   ├── models/
│   │   └── llm_factory.py        # LangChain ChatOpenAI 工厂（全局单例）
│   └── utils/
│       └── structured_logger.py  # JSONL 结构化日志
│
├── logs/                           # 运行日志
├── chroma_db/                      # ChromaDB 向量库（重启不丢失）
│
├── start_backend.py               # 后端启动脚本
├── start_frontend.py              # 前端启动脚本
├── requirements.txt               # Python 依赖
└── .env                            # 环境变量（不提交 Git）
```

## 🚀 快速开始（本地部署）

### 前提条件

- Python 3.12+
- Conda 环境（推荐）

### 1. 创建并激活环境

```bash
conda create -n my_agent python=3.12
conda activate my_agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

编辑根目录 `.env` 文件，填入 API 密钥：

```env
# LLM（对话模型）
LLM_API_KEY=your_siliconflow_api_key
MODEL_NAME=deepseek-ai/DeepSeek-V4-Flash
MODEL_URL=https://api.siliconflow.cn/v1

# Embedding（RAG 功能）
EMBEDDING_API_KEY=your_siliconflow_api_key
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_URL=https://api.siliconflow.cn/v1
```

> `EMBEDDING_API_KEY` 与 `LLM_API_KEY` 可使用同一个 SiliconFlow API Key。

### 4. 启动服务

**启动后端（终端 1）：**

```bash
conda activate my_agent
python start_backend.py
```

**启动前端（终端 2）：**

```bash
conda activate my_agent
python start_frontend.py
```

> 先启动后端，再启动前端。前端启动后会自动在浏览器打开。

### 5. 访问服务

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:8501 |
| 后端 API 文档（Swagger） | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/health |

**停止服务**：在对应终端按 `Ctrl+C`。

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

> **数据持久化**：ChromaDB 向量库数据存储在本地 `chroma_db/` 目录，重启服务后文档不丢失。

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

### LangGraph 编排（StateGraph）

系统使用 LangGraph StateGraph 定义三节点流水线：
```
START → route_node → expert_node → aggregate_node → END
```
- **route_node**：调用 RouterAgent 进行关键词+正则评分，选择最佳路由
- **expert_node**：调用对应领域的 ExpertAgent（LangChain LCEL 链）
- **aggregate_node**：综合路由结果和专家分析，生成最终报告

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

每个专家智能体：**LangChain ChatPromptTemplate** → **LCEL 链（prompt | ChatOpenAI | StrOutputParser）** → JSON 解析 → **LLM 不可用时自动降级为规则分析**

## 🧠 RAG 实现原理（LangChain 重构版）

```
文档入库流程（LangChain 组件）：
  文本 → RecursiveCharacterTextSplitter（500字/块，50字重叠）
       → OpenAIEmbeddings (Qwen3-Embedding-8B) 向量化
       → Chroma.add_texts() 持久化存储

问答流程（LCEL 链式调用）：
  问题 → Chroma.similarity_search_with_score() 余弦检索
       → Context 拼接
       → LCEL 链: ChatPromptTemplate | ChatOpenAI | StrOutputParser
       → 生成答案
```

## 🔐 安全说明

- API 密钥存储在 `.env` 文件中，已加入 `.gitignore`，不会提交到版本控制
- 后端 CORS 仅允许来自 Streamlit 前端的跨域请求
- 告警分析历史保存在**内存**中，服务重启后清空
- RAG 向量库数据**持久化**在 `chroma_db/` 目录

---

**版本**: 3.0.0 (LangChain/LangGraph 重构版) | **更新**: 2026-06-25