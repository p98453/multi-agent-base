---
name: vectorize_and_store
description: 将文档内容转换为向量嵌入并存入向量数据库，支持后续语义搜索和相似文档匹配
agent_type: document
version: 1
parameters:
  document_content: str - 文档内容
  document_metadata: dict - 文档元数据
  chunk_strategy: str - 分块策略: fixed_size|semantic|recursive|hybrid
  chunk_size: int - 分块大小（字符数）
  chunk_overlap: int - 分块重叠大小
  embedding_model: str - 向量化模型名称
  collection_name: str - 向量库集合名称
---