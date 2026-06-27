---
name: semantic_search
description: 对已入库的文档进行语义搜索，支持自然语言查询，返回最相关的文档片段及出处
agent_type: document
version: 1
parameters:
  query: str - 搜索查询（自然语言）
  collection_name: str - 搜索的目标向量集合
  top_k: int - 返回结果数量 默认5
  similarity_threshold: float - 相似度阈值 默认0.5
  filters: dict - 元数据过滤条件
  search_type: str - 搜索类型: semantic|hybrid|keyword
---