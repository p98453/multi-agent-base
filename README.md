# 🛡️ 多智能体安全分析系统

一个基于多智能体架构的网络安全威胁智能分析系统，通过路由智能体与多个领域专家智能体协同工作，结合大语言模型（Qwen）实现自动化安全告警分析。

## 🌟 系统特性

- **🤖 多智能体架构**: 路由智能体智能分发 + 三大领域专家智能体深度分析
- **⚡ 全异步处理**: 基于 asyncio/httpx，提升分析性能和并发能力
- **🧠 LLM 驱动**: 集成 Qwen 大语言模型（SiliconFlow 远程API），提供专业级威胁分析
- **📊 完整前后端**: Streamlit 可视化前端 + FastAPI 高性能后端
- **📝 结构化日志**: 完整的分析链路日志记录，便于复盘和审计
- **🔄 优雅降级**: LLM 不可用时自动切换为基于规则的分析

## 🏗️ 系统架构

```
┌───────────────────────┐
│   Streamlit 前端       │  ← 用户交互、可视化展示
│   (localhost:8501)     │
└──────────┬────────────┘
           │ HTTP API
┌──────────▼────────────┐
│   FastAPI 后端         │  ← RESTful API、请求校验
│   (localhost:8000)     │
└──────────┬────────────┘
           │
┌──────────▼────────────┐
│   AgentService 服务层  │  ← 业务编排、历史存储
└──────────┬────────────┘
           │
┌──────────▼────────────────────────────────────┐
│            MultiAgentSystem 智能体核心          │
│  ┌──────────────┐    ┌─────────────────────┐  │
│  │ RouterAgent  │───→│   ExpertAgent × 3    │  │
│  │ (路由决策)    │    │ ├ web_attack         │  │
│  │              │    │ ├ vulnerability_attack│  │
│  └──────────────┘    │ └ illegal_connection  │  │
│                       └─────────┬───────────┘  │
│                                 │ LLM API      │
│                       ┌─────────▼───────────┐  │
│                       │  Qwen LLM (远程API)  │  │
│                       │  SiliconFlow         │  │
│                       └─────────────────────┘  │
└────────────────────────────────────────────────┘
```

## 📁 项目结构

```
multi-agent-security-analysis-main/
├── backend/                        # FastAPI 后端服务
│   ├── main.py                    # 应用入口，生命周期管理
│   ├── config.py                  # 配置管理（读取.env）
│   ├── api/
│   │   ├── routes/
│   │   │   ├── analysis.py       # 分析API（提交告警、查询历史）
│   │   │   └── stats.py          # 统计API + 健康检查
│   │   └── models/
│   │       └── schemas.py        # Pydantic 数据模型
│   └── services/
│       ├── agent_service.py      # 智能体服务封装
│       └── memory_storage.py     # 内存历史存储
│
├── frontend/                       # Streamlit 前端
│   ├── app.py                     # 主页面
│   ├── pages/
│   │   ├── 1_🔍_Alert_Analysis.py    # 告警分析页面
│   │   ├── 2_📊_Analysis_History.py  # 分析历史页面
│   │   └── 4_📈_System_Dashboard.py  # 系统仪表板
│   └── utils/
│       └── api_client.py          # HTTP 客户端封装
│
├── src/                            # 智能体核心系统
│   ├── agents/
│   │   ├── optimized_router.py   # 路由智能体（关键词+正则规则）
│   │   ├── optimized_expert.py   # 专家智能体（LLM分析+规则降级）
│   │   └── optimized_system.py   # 多智能体协调器
│   ├── models/
│   │   ├── api_client.py         # 异步 LLM API 客户端
│   │   └── llm_inference.py      # LLM 推理封装
│   └── utils/
│       ├── config.py             # 配置读取工具
│       └── structured_logger.py  # 结构化日志
│
├── .env                            # 环境变量（不提交）
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
├── start_backend.py               # 后端启动脚本
└── start_frontend.py              # 前端启动脚本
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- pip 包管理器（推荐使用 conda 管理虚拟环境）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入实际的 API 密钥：

```env
LLM_API_KEY=your_api_key_here
MODEL_NAME=Qwen/Qwen3-30B-A3B-Thinking-2507
MODEL_URL=https://api.siliconflow.cn/v1
```

### 4. 启动后端服务

```bash
python start_backend.py
```

后端服务将在 `http://localhost:8000` 启动

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/health

### 5. 启动前端界面

在新终端窗口执行：

```bash
python start_frontend.py
```

前端界面将在 `http://localhost:8501` 打开

## 📖 使用指南

### 🔍 告警分析

1. 进入「告警分析」页面
2. 选择攻击类型、输入攻击载荷、填写 IP 地址
3. 点击「开始分析」
4. 查看分析结果：
   - **攻击技术识别** — 精确识别攻击手法
   - **风险评分** — 1-10 分量化评估
   - **威胁等级** — 高危 / 中危 / 低危
   - **防御建议** — 具体可操作的应对措施
   - **路由决策** — 展示智能体分发逻辑
   - **性能指标** — 各阶段处理耗时

### 📊 分析历史

- 查看所有历史分析记录
- 按威胁等级、攻击类型过滤
- 数据表格展示，支持排序浏览

### 📈 系统仪表板

- 总分析次数、高危占比等关键指标
- 威胁等级分布饼图
- 攻击类型分布柱状图

## 🔧 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/analyze` | 提交告警进行分析 |
| `GET` | `/api/history` | 获取分析历史记录 |
| `GET` | `/api/stats` | 获取系统统计信息 |
| `GET` | `/api/health` | 健康检查 |

## 🤖 智能体详解

### 路由智能体（RouterAgent）

- 基于 **关键词匹配 + 正则模式** 的规则引擎
- 自动计算各类别路由分数，选择最佳匹配
- 支持三大路由方向：`web_attack` / `vulnerability_attack` / `illegal_connection`
- 低匹配度时自动降低置信度，默认路由到 `web_attack`

### 专家智能体（ExpertAgent × 3）

| 专家类型 | 擅长领域 | 典型场景 |
|----------|----------|----------|
| web_attack | Web 安全攻击 | SQL注入、XSS、命令注入、目录遍历、Webshell |
| vulnerability_attack | 漏洞利用攻击 | CVE漏洞、Exploit利用、Shellcode |
| illegal_connection | 非法网络连接 | C2通信、僵尸网络、DDoS、代理隧道 |

每个专家智能体的工作流程：
1. 使用领域特定的 Prompt 模板构造输入
2. 调用 Qwen LLM 远程 API 进行深度分析
3. 解析 LLM 返回的 JSON 结构化结果
4. **LLM 不可用时自动降级**为基于规则的分析

## 🔐 安全说明

- API 密钥存储在 `.env` 文件中，已加入 `.gitignore`
- 后端服务默认仅允许来自 Streamlit 的 CORS 请求
- 分析历史保存在内存中，服务重启后清空

## 📄 许可证

本项目仅用于学习和研究目的。

---

**版本**: 1.0.0  
**最后更新**: 2026-02-15
