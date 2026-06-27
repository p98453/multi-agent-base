# 招投标情报分析多智能体系统

基于 **Gateway + Sub-Agent + Loop** 架构的招投标情报分析系统，通过 CDP 对接 CRM，用户以自然对话方式发起需求，网关负责意图识别、动态路由与质量管控。

## 总体架构

```
用户 → Streamlit前端 → FastAPI后端 → LangGraph编排引擎
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼                     ▼
              Gateway网关           CrawlerAgent        DocumentAgent        PresentationAgent        DistributionAgent
              (意图识别+路由        (爬虫管理)           (文档处理)           (智能演示)           (多端分发)
               质量评估+进化)            │                     │                     │                     │
                    │              ┌────┴────┐          ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
                    │             6个Skills           7个Skills           6个Skills           7个Skills
                    │
              Skill进化引擎 ─── 用户反馈 → 5Why根因分析 → 自动修改Skill → 验证 → 部署
```

## 核心流程 (Loop架构)

```
START → gateway_node(意图识别+Skill选择)
         → agent_node(Agent执行Skill链)
              → evaluate_node(4维质量评估: 覆盖度/准确性/可用性/效率)
                   ├── satisfied → aggregate_node(结果综合) → END
                   └── unsatisfied & loop<3 → agent_node(带反馈重试)
```

- 最多 3 次 Loop 重试
- 每次重试携带评估反馈指导 Agent 改进
- 每次 Loop 完整记录 Skill 链和评估历史

## 四大智能体

### 1. 爬虫管理Agent (CrawlerAgent)

| Skill | 功能 |
|-------|------|
| `parse_crawler_intent` | 自然语言→结构化爬取参数（平台、关键词、时间、地域、行业） |
| `match_crawler_script` | 自动匹配预置爬虫脚本（6个平台脚本+复合脚本） |
| `execute_crawl` | 爬取全生命周期管理（启动、监控、重试、降级） |
| `parse_crawl_results` | 原始数据清洗→结构化情报（含去重、格式标准化） |
| `monitor_crawl_status` | 实时监控+异常自动恢复 |
| `generate_crawl_report` | 生成6段式情报分析报告（概览→趋势→标讯→竞品→洞察→建议） |

### 2. 文档处理Agent (DocumentAgent)

| Skill | 功能 |
|-------|------|
| `identify_document_format` | 自动识别 PDF/Word/Excel/HTML/扫描件/图片格式 |
| `parse_document_structure` | 深度结构化解析（元数据、标题树、表格、图片、交叉引用） |
| `generate_summary` | 4级智能摘要（一句话/标准/分级/决策导向） |
| `extract_structured_data` | 6类实体提取（项目、时间、参与方、资质、技术、评标规则） |
| `vectorize_and_store` | 4种分块策略+向量化+ChromaDB入库 |
| `semantic_search` | 3种检索模式（语义/混合/关键词）+结果排序 |
| `compare_documents` | 5维横向对比（基础、时间、资质、技术、评标） |

### 3. 智能演示Agent (PresentationAgent)

| Skill | 功能 |
|-------|------|
| `organize_presentation_content` | 4种演示类型策划（情报/竞品/提案/简报）+页面规划 |
| `generate_charts` | 6种图表（柱状/折线/饼图/雷达/散点/热力图）+洞察标注 |
| `match_template` | 5种模板库智能匹配+品牌定制 |
| `generate_comparison_slides` | 4种对比类型幻灯片（竞品/方案/预算/资质）+多维度可视化 |
| `export_presentation` | 多格式导出（PPTX/PDF/HTML/PNG）+质量检查 |
| `format_data_table` | 表格美化+条件格式+排序+高亮规则 |

### 4. 多端分发Agent (DistributionAgent)

| Skill | 功能 |
|-------|------|
| `parse_channel_config` | 解析分发配置（收件人/渠道/定时规则/提醒规则/附件） |
| `compose_email` | 智能邮件撰写（HTML/Markdown、智能主题、角色适配语气） |
| `send_via_email` | SMTP/Exchange发送（附件/抄送/密送/已读回执/自动重试） |
| `push_to_channels` | 多端推送（企业微信/钉钉/飞书/短信/内部API）+内容适配 |
| `manage_schedule` | 定时任务管理（创建/修改/暂停/恢复/删除/查看状态） |
| `generate_distribution_report` | 分发效果分析（送达率/打开率/行动转化/趋势） |
| `query_address_book` | 企业通讯录查询（姓名/部门/角色模糊匹配） |

## Skill进化引擎

当用户指出偏差时，系统自动完成闭环进化：

```
用户反馈 → analyze_feedback(5Why根因分析)
         → update_skill_strategy(生成进化策略: Prompt修改/参数调整/能力扩展)
         → evolve_skill(写入SKILL.md+version递增)
         → validate_skill_update(功能/兼容/性能/鲁棒性验证)
         → 部署生效
```

- 进化记录持久化到 `evolutions.jsonl`
- 支持版本回滚
- 最小改动原则，渐进式进化

## CDP对接与用户记忆

- **CDP Client**: 对接CRM系统，获取用户行业、地域、偏好等上下文
- **User Memory**: 每个用户独立存储对话历史、任务记录、Skill反馈
- **Docker Manager**: 支持为每个用户独立启动Docker容器，隔离Agent+Skill+Memory环境

## 技术栈

| 层级 | 技术 |
|------|------|
| 编排引擎 | LangGraph StateGraph (条件边+循环边) |
| LLM调用 | LangChain ChatOpenAI (兼容SiliconFlow等) |
| 后端框架 | FastAPI + Pydantic v2 |
| 前端界面 | Streamlit |
| 向量存储 | ChromaDB |
| 文件处理 | python-pptx |
| 数据可视化 | Plotly + Pandas |

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (.env)
LLM_API_KEY=your_api_key
MODEL_NAME=your_model_name
MODEL_URL=your_base_url

# 启动后端 (端口8000)
python start_backend.py

# 启动前端 (端口8501)
python start_frontend.py
```

## API端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 主对话入口 |
| POST | `/api/feedback` | 提交反馈触发Skill进化 |
| GET | `/api/skills` | 查看所有Skill列表 |
| GET | `/api/skills/evolution` | 查看进化历史 |
| POST | `/api/docker/container` | 管理用户容器 |
| GET | `/api/health` | 健康检查 |

## Skills目录结构

```
src/skills/
├── gateway/
│   ├── identify_intent/      (SKILL.md + scripts/ + references/ + assets/)
│   ├── evaluate_quality/
│   ├── analyze_feedback/
│   ├── update_skill_strategy/
│   ├── validate_skill_update/
│   └── fallback_default/
├── crawler/
│   ├── parse_crawler_intent/
│   ├── match_crawler_script/
│   ├── execute_crawl/
│   ├── parse_crawl_results/
│   ├── monitor_crawl_status/
│   └── generate_crawl_report/
├── document/
│   ├── identify_document_format/
│   ├── parse_document_structure/
│   ├── generate_summary/
│   ├── extract_structured_data/
│   ├── vectorize_and_store/
│   ├── semantic_search/
│   └── compare_documents/
├── presentation/
│   ├── organize_presentation_content/
│   ├── generate_charts/
│   ├── match_template/
│   ├── generate_comparison_slides/
│   ├── export_presentation/
│   └── format_data_table/
└── distribution/
    ├── parse_channel_config/
    ├── compose_email/
    ├── send_via_email/
    ├── push_to_channels/
    ├── manage_schedule/
    ├── generate_distribution_report/
    └── query_address_book/
```

每个Skill目录包含：`SKILL.md`（YAML元数据+完整Prompt模板）、`scripts/`（可执行脚本）、`references/`（参考文档）、`assets/`（模板/静态文件）