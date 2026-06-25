# LangChain & LangGraph 教学文档

> 本文档通过本项目的实际代码，系统讲解 LangChain 和 LangGraph 的核心概念与使用方法。

---

## 目录

- [一、LangChain 基础概念](#一langchain-基础概念)
- [二、LCEL 链式调用](#二lcel-链式调用)
- [三、LangGraph StateGraph](#三langgraph-stategraph)
- [四、RAG 组件](#四rag-组件)
- [五、LangChain 在本项目中的完整应用](#五langchain-在本项目中的完整应用)
- [六、常用 API 速查](#六常用-api-速查)

---

## 一、LangChain 基础概念

### 1.1 什么是 LangChain？

LangChain 是一个用于构建 LLM 应用的 Python 框架，它提供了一系列标准化的组件：

| 组件 | 作用 | 本项目使用 |
|------|------|-----------|
| **ChatOpenAI** | 调用 OpenAI 兼容 API 的 LLM | ✅ `llm_factory.py` |
| **ChatPromptTemplate** | 构建结构化提示词模板 | ✅ `optimized_expert.py` |
| **StrOutputParser** | 将 LLM 输出解析为字符串 | ✅ `optimized_expert.py`, `rag_service.py` |
| **OpenAIEmbeddings** | 文本向量化 | ✅ `rag_service.py` |
| **Chroma** | 向量数据库 | ✅ `rag_service.py` |
| **RecursiveCharacterTextSplitter** | 智能文本分块 | ✅ `rag_service.py` |

### 1.2 ChatOpenAI — LLM 调用

`ChatOpenAI` 是 LangChain 中最常用的 LLM 封装类，兼容所有 OpenAI API 接口（包括 SiliconFlow、DeepSeek 等第三方服务）。

```python
from langchain_openai import ChatOpenAI

# 创建实例（连接 SiliconFlow API）
llm = ChatOpenAI(
    model="Qwen/Qwen2.5-7B-Instruct",     # 模型名称
    api_key="sk-xxx",                       # API 密钥
    base_url="https://api.siliconflow.cn/v1",  # API 基础 URL
    temperature=0.3,                        # 温度（0=确定性，1=随机）
    max_tokens=512,                         # 最大输出 token 数
)

# 同步调用
response = llm.invoke("你好，请介绍一下 SQL 注入")
print(response.content)  # 输出字符串

# 异步调用（FastAPI 场景）
response = await llm.ainvoke("你好，请介绍一下 SQL 注入")
print(response.content)
```

**本项目代码示例（`src/models/llm_factory.py`）：**

```python
from langchain_openai import ChatOpenAI
from backend.config import BackendConfig

_llm_instance = None

def get_chat_llm() -> ChatOpenAI:
    """全局单例模式 — 确保整个应用只创建一个 LLM 实例"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOpenAI(
            model=BackendConfig.MODEL_NAME,
            api_key=BackendConfig.LLM_API_KEY,
            base_url=BackendConfig.MODEL_URL,
            temperature=0.3,
            max_tokens=512,
        )
    return _llm_instance
```

> **为什么用单例模式？** ChatOpenAI 内部管理了 HTTP 连接池和认证状态，创建多个实例会浪费资源。

### 1.3 ChatPromptTemplate — 提示词模板

`ChatPromptTemplate` 用于构建结构化的多轮对话提示词：

```python
from langchain_core.prompts import ChatPromptTemplate

# 方式1: from_messages（推荐，最灵活）
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名{role}专家。"),
    ("human", "请分析以下内容：\n{content}"),
])

# 格式化输入变量
messages = prompt.invoke({"role": "Web安全", "content": "SELECT * FROM users..."})

# 方式2: from_template（简单场景）
prompt = ChatPromptTemplate.from_template("请回答：{question}")
```

**⚠️ 重要语法：JSON 中的花括号转义**

在 ChatPromptTemplate 中，`{变量名}` 是模板变量语法。如果你需要在 prompt 中输出字面量花括号（比如要求 LLM 返回 JSON），必须使用 **双花括号** `{{}}` 进行转义：

```python
# ❌ 错误 — LangChain 会把 { 当作变量名
prompt = ChatPromptTemplate.from_messages([
    ("human", '请返回JSON: {"name": "xxx"}')
])

# ✅ 正确 — 双花括号转义为字面量花括号
prompt = ChatPromptTemplate.from_messages([
    ("human", '请返回JSON: {{"name": "xxx"}}')
])
```

**本项目代码示例（`src/agents/optimized_expert.py`）：**

```python
self.prompt_templates = {
    'web_attack': ChatPromptTemplate.from_messages([
        ("system", "你是一名资深Web安全分析专家。"),
        ("human", """## 告警信息
- 攻击类型: {attack_type}
- 攻击载荷: {payload}
...
请严格以JSON格式返回（注意双花括号转义）：
{{
    "attack_technique": "具体攻击技术名称",
    "risk_score": 8.5,
    "recommendations": ["建议1", "建议2"]
}}""")
    ]),
}
```

---

## 二、LCEL 链式调用

### 2.1 什么是 LCEL？

**LCEL（LangChain Expression Language）** 是 LangChain 的核心编排机制。它通过 `|` 管道操作符将多个组件串联成处理链：

```
输入 → 组件A → 组件B → 组件C → 输出
```

用 Python 代码表示就是：

```python
chain = 组件A | 组件B | 组件C
result = chain.invoke(输入)        # 同步
result = await chain.ainvoke(输入)  # 异步
```

### 2.2 最常用的 LCEL 链：Prompt → LLM → Parser

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# 1. 定义 Prompt 模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名安全分析专家。"),
    ("human", "分析攻击类型：{attack_type}，载荷：{payload}"),
])

# 2. 创建 LLM
llm = ChatOpenAI(model="Qwen/Qwen2.5-7B-Instruct", api_key="sk-xxx", base_url="...")

# 3. 创建解析器
parser = StrOutputParser()  # 将 ChatMessage 对象转为纯字符串

# 4. 组合成 LCEL 链
chain = prompt | llm | parser

# 5. 调用链
result = await chain.ainvoke({
    "attack_type": "SQL注入",
    "payload": "UNION SELECT * FROM admin",
})
print(result)  # 纯字符串输出
```

### 2.3 LCEL 的数据流

```
输入字典 {"attack_type": "...", "payload": "..."}
    │
    ▼ ChatPromptTemplate.invoke()
生成 ChatMessage 列表 [SystemMessage("..."), HumanMessage("...")]
    │
    ▼ ChatOpenAI.ainvoke()
生成 AIMessage(content="LLM的回复文本...")
    │
    ▼ StrOutputParser.invoke()
提取 "LLM的回复文本..."（纯字符串）
```

### 2.4 本项目中的 LCEL 用法

**专家智能体的分析链（`optimized_expert.py`）：**

```python
async def analyze(self, alert_data):
    prompt = self.prompt_templates[self.expert_type]
    llm = get_chat_llm()
    chain = prompt | llm | self.output_parser  # LCEL 链

    result_text = await chain.ainvoke({
        "attack_type": alert_data.get('attack_type', 'unknown'),
        "payload": alert_data.get('payload', '')[:500],
        "source_ip": alert_data.get('source_ip', 'unknown'),
        "target_ip": alert_data.get('target_ip', 'unknown'),
    })

    result = self._parse_response(result_text)  # JSON 提取
```

**RAG 问答链（`rag_service.py`）：**

```python
chain = self._qa_prompt | self._llm | StrOutputParser()
answer = await chain.ainvoke({
    "context": context,      # 检索到的文档片段
    "question": question,    # 用户问题
})
```

---

## 三、LangGraph StateGraph

### 3.1 什么是 LangGraph？

**LangGraph** 是 LangChain 官方出品的**有状态图编排框架**，用于构建多步骤、多智能体的工作流。

核心概念：

| 概念 | 说明 |
|------|------|
| **State（状态）** | 图在执行过程中的共享数据容器（TypedDict） |
| **Node（节点）** | 图中的处理单元，是一个函数 |
| **Edge（边）** | 定义节点之间的流转顺序 |
| **StateGraph** | 图的构建器，用于注册节点和边 |
| **graph.compile()** | 将图编译为可执行对象 |
| **graph.ainvoke()** | 异步执行图 |

### 3.2 基本用法

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

# 步骤1: 定义状态
class MyState(TypedDict):
    input: str
    result: str

# 步骤2: 定义节点函数
async def process_node(state: MyState) -> dict:
    """节点函数接收当前状态，返回需要更新的字段"""
    return {"result": f"处理了: {state['input']}"}

# 步骤3: 构建图
graph_builder = StateGraph(MyState)
graph_builder.add_node("process", process_node)
graph_builder.set_entry_point("process")
graph_builder.add_edge("process", END)

# 步骤4: 编译
graph = graph_builder.compile()

# 步骤5: 执行
final_state = await graph.ainvoke({"input": "测试数据", "result": ""})
print(final_state["result"])  # "处理了: 测试数据"
```

### 3.3 节点函数的规则

```python
async def my_node(state: MyState) -> dict:
    # 1. 从 state 读取需要的数据
    data = state["some_field"]

    # 2. 执行处理逻辑
    result = do_something(data)

    # 3. 返回需要更新的字段（不需要返回所有字段）
    return {"output_field": result}

    # ⚠️ 注意：
    # - 参数是完整的 state 字典
    # - 返回值是 dict，只包含需要更新的字段
    # - 其他字段保持原值不变
    # - 可以是 async 函数
```

### 3.4 本项目中的 StateGraph

**状态定义（`optimized_system.py`）：**

```python
from typing import TypedDict

class AnalysisState(TypedDict):
    alert_data: dict       # 输入的告警数据
    task_id: str           # 任务唯一 ID
    start_time: float      # 开始时间戳
    routing_result: dict   # 路由节点的输出
    selected_route: str    # 选择的专家类型
    expert_result: dict    # 专家分析节点的输出
    final_result: dict     # 最终结果
```

**图构建：**

```python
def _build_graph(self):
    graph_builder = StateGraph(AnalysisState)

    # 注册三个节点
    graph_builder.add_node("route_node", self._route_node)
    graph_builder.add_node("expert_node", self._expert_node)
    graph_builder.add_node("aggregate_node", self._aggregate_node)

    # 定义流转：顺序执行
    graph_builder.set_entry_point("route_node")           # 入口
    graph_builder.add_edge("route_node", "expert_node")   # 路由 → 专家
    graph_builder.add_edge("expert_node", "aggregate_node")  # 专家 → 综合
    graph_builder.add_edge("aggregate_node", END)         # 综合 → 结束

    return graph_builder.compile()
```

**图的执行流程：**

```
输入: {alert_data: {...}, task_id: "uuid", ...}
  │
  ▼ route_node
  │  调用 RouterAgent.route(alert_data)
  │  更新: routing_result, selected_route
  │
  ▼ expert_node
  │  调用 ExpertAgent.analyze(alert_data)
  │  更新: expert_result
  │
  ▼ aggregate_node
  │  综合 routing_result + expert_result
  │  更新: final_result
  │
  ▼ END
输出: {final_result: {success: true, routing: {...}, expert_analysis: {...}}}
```

**节点函数示例（路由节点）：**

```python
async def _route_node(self, state: AnalysisState) -> dict:
    """路由决策节点 — 只更新 routing_result 和 selected_route"""
    routing_result = await self.router.route(state["alert_data"])
    return {
        "routing_result": routing_result,
        "selected_route": routing_result['selected_route'],
    }
```

### 3.5 条件分支（高级用法）

LangGraph 还支持根据状态值选择不同的下一节点：

```python
from langgraph.graph import StateGraph, END

# 条件路由函数
def route_by_type(state):
    if state["selected_route"] == "web_attack":
        return "web_expert"
    elif state["selected_route"] == "vulnerability_attack":
        return "vuln_expert"
    else:
        return "conn_expert"

# 添加条件边
graph_builder.add_conditional_edges(
    "route_node",          # 源节点
    route_by_type,         # 条件函数
    {                      # 映射表：函数返回值 → 目标节点
        "web_expert": "web_expert_node",
        "vuln_expert": "vuln_expert_node",
        "conn_expert": "conn_expert_node",
    }
)
```

> 本项目当前使用线性图（所有专家共享一个 expert_node），如需每个专家独立节点可使用此条件分支。

---

## 四、RAG 组件

### 4.1 RAG 流程概览

```
               文档入库                          问答
      ┌─────────────────────┐     ┌───────────────────────────────┐
      │  文本                │     │  用户问题                      │
      │    ↓                │     │    ↓                          │
      │  文本分块            │     │  向量化                       │
      │    ↓                │     │    ↓                          │
      │  向量化              │     │  向量库检索 (top-k)            │
      │    ↓                │     │    ↓                          │
      │  存入向量库          │     │  构建 Context                 │
      └─────────────────────┘     │    ↓                          │
                                  │  LLM 生成答案                 │
                                  └───────────────────────────────┘
```

### 4.2 RecursiveCharacterTextSplitter — 文本分块

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 每块最大字符数
    chunk_overlap=50,     # 相邻块重叠字符数（避免截断语义）
    length_function=len,
    separators=["\n\n", "\n", "。", ".", " ", ""],  # 分割优先级
)

chunks = splitter.split_text("很长的文档文本...")
# → ["第一块内容...", "第二块内容...", ...]
```

> **为什么要分块？** LLM 有 context 长度限制，且检索粒度太粗（整篇文档）会降低精度。推荐 chunk_size 在 200~1000 之间。

### 4.3 OpenAIEmbeddings — 文本向量化

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="Qwen/Qwen3-Embedding-8B",
    api_key="sk-xxx",
    base_url="https://api.siliconflow.cn/v1",
)

# 单条文本向量化
vector = embeddings.embed_query("什么是 SQL 注入？")
# → [0.123, -0.456, 0.789, ...]  (高维浮点向量)

# 批量向量化
vectors = embeddings.embed_documents(["文本1", "文本2", "文本3"])
# → [[0.1, ...], [0.2, ...], [0.3, ...]]
```

### 4.4 Chroma — 向量数据库

```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(...)

# 创建 / 连接向量库
vectorstore = Chroma(
    collection_name="my_docs",
    embedding_function=embeddings,
    persist_directory="./chroma_db",  # 本地持久化路径
)

# 添加文档
vectorstore.add_texts(
    texts=["SQL注入是一种攻击...", "XSS是跨站脚本..."],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}],
)

# 检索（余弦相似度）
results = vectorstore.similarity_search_with_score(
    query="什么是注入攻击？",
    k=3,  # 返回前 3 个最相似的
)
for doc, score in results:
    print(f"相似度: {1-score:.4f}, 内容: {doc.page_content}")
```

### 4.5 完整 RAG 链（本项目实现）

```python
# 1. 检索文档
sources = self.retrieve(question, top_k=3)

# 2. 构建上下文
context = "\n\n".join([f"[片段{i}]\n{src['text']}" for i, src in enumerate(sources, 1)])

# 3. LCEL 链生成答案
chain = self._qa_prompt | self._llm | StrOutputParser()
answer = await chain.ainvoke({"context": context, "question": question})
```

---

## 五、LangChain 在本项目中的完整应用

### 5.1 架构总览

```
┌─────────────────────────────────────────────────┐
│  LangGraph StateGraph                           │
│                                                 │
│  route_node ──→ expert_node ──→ aggregate_node  │
│                     │                           │
│                     ▼                           │
│              LCEL 链式调用                        │
│    ChatPromptTemplate | ChatOpenAI | Parser      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  RAG 服务 (LangChain 组件)                       │
│                                                 │
│  RecursiveCharacterTextSplitter → 文本分块        │
│  OpenAIEmbeddings → 向量化                       │
│  Chroma → 存储 & 检索                            │
│  LCEL 链 → 生成答案                              │
└─────────────────────────────────────────────────┘
```

### 5.2 文件关系图

```
src/models/llm_factory.py       ← ChatOpenAI 全局单例
    ↕ 被引用
src/agents/optimized_expert.py  ← ChatPromptTemplate + LCEL 链
    ↕ 被组合
src/agents/optimized_system.py  ← LangGraph StateGraph 编排
    ↕ 被调用
backend/services/agent_service.py  ← FastAPI 业务层

backend/services/rag_service.py ← OpenAIEmbeddings + Chroma + LCEL 链
    ↕ 被调用
backend/api/routes/rag.py       ← FastAPI 路由层
```

### 5.3 关键代码对照（重构前 vs 重构后）

#### LLM 调用

```python
# ❌ 重构前: 手写 httpx 异步 HTTP 调用
async with httpx.AsyncClient() as client:
    response = await client.post(api_url, headers=headers, json=payload)
    result = response.json()["choices"][0]["message"]["content"]

# ✅ 重构后: LangChain ChatOpenAI
llm = get_chat_llm()
result = await llm.ainvoke("你的 prompt")
print(result.content)
```

#### Prompt 构建

```python
# ❌ 重构前: 手写 str.format()
prompt = f"你是{expert_type}专家\n分析：{payload}"

# ✅ 重构后: ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是{expert_type}专家"),
    ("human", "分析：{payload}"),
])
chain = prompt | llm | StrOutputParser()
result = await chain.ainvoke({"expert_type": "Web安全", "payload": "..."})
```

#### 多智能体编排

```python
# ❌ 重构前: 手写过程式调用
async def analyze(self, alert_data):
    routing = await self.router.route(alert_data)
    expert = self.experts[routing['selected_route']]
    expert_result = await expert.analyze(alert_data)
    return combine(routing, expert_result)

# ✅ 重构后: LangGraph StateGraph
graph_builder = StateGraph(AnalysisState)
graph_builder.add_node("route_node", self._route_node)
graph_builder.add_node("expert_node", self._expert_node)
graph_builder.add_node("aggregate_node", self._aggregate_node)
graph_builder.set_entry_point("route_node")
graph_builder.add_edge("route_node", "expert_node")
graph_builder.add_edge("expert_node", "aggregate_node")
graph_builder.add_edge("aggregate_node", END)
graph = graph_builder.compile()

# 执行：自动按图流转
final_state = await graph.ainvoke(initial_state)
```

#### RAG 文本分块

```python
# ❌ 重构前: 手写分块逻辑
def _split_text(self, text):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i+chunk_size])

# ✅ 重构后: LangChain TextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_text(text)
```

---

## 六、常用 API 速查

### LangChain Core

```python
# Prompt
from langchain_core.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages([("system", "..."), ("human", "...")])

# Parser
from langchain_core.output_parsers import StrOutputParser
parser = StrOutputParser()

# LCEL 链
chain = prompt | llm | parser
result = await chain.ainvoke({"key": "value"})
```

### LangChain OpenAI

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

llm = ChatOpenAI(model="...", api_key="...", base_url="...", temperature=0.3)
embeddings = OpenAIEmbeddings(model="...", api_key="...", base_url="...")
```

### LangChain Chroma

```python
from langchain_chroma import Chroma

vectorstore = Chroma(collection_name="...", embedding_function=embeddings, persist_directory="...")
vectorstore.add_texts(texts=["..."], metadatas=[{...}])
results = vectorstore.similarity_search_with_score(query="...", k=3)
```

### LangChain Text Splitters

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_text("long text...")
```

### LangGraph

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class MyState(TypedDict):
    field1: str
    field2: dict

graph_builder = StateGraph(MyState)
graph_builder.add_node("node_name", node_function)
graph_builder.set_entry_point("node_name")
graph_builder.add_edge("node_name", END)
graph = graph_builder.compile()

result = await graph.ainvoke({"field1": "...", "field2": {}})
```

---

> 📝 **文档版本**: 1.0.0 | **更新**: 2026-02-25
