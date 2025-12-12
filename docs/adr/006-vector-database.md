# ADR-006: 向量数据库选型

| 属性 | 值 |
|------|-----|
| **状态** | 🟢 Accepted |
| **决策者** | [Your Name] |
| **日期** | 2024-12 |
| **相关 ADR** | ADR-001 (Agent 框架) |

## 上下文 (Context)

TravelMind 需要向量数据库支持以下 RAG 场景：

| 场景 | 数据类型 | 预估规模 |
|------|---------|---------|
| 旅游攻略知识库 | 文本 chunks | 1-10 万条 |
| POI 语义搜索 | 景点描述向量 | 10-100 万条 |
| 用户历史偏好 | 会话向量 | 1-10 万条 |

技术需求：
1. **语义检索**：支持向量相似度搜索 (cosine, L2)
2. **元数据过滤**：支持 city="杭州" AND category="景点" 等条件
3. **本地开发友好**：无需复杂部署即可开发测试
4. **生产可扩展**：数据增长时可平滑迁移
5. **成本控制**：个人项目预算有限

## 考虑的备选方案 (Alternatives Considered)

### 方案 A: Chroma

**概述**：轻量级开源向量数据库，专为 AI 应用设计。

**优势**：
- 安装简单：`pip install chromadb`
- 本地持久化：SQLite + DuckDB 后端
- 与 LangChain/LlamaIndex 集成开箱即用
- 内置 Embedding 支持
- 完全免费开源
- 适合 100 万向量以下规模

**劣势**：
- 大规模数据性能下降
- 分布式能力弱
- 生产环境需要 Chroma Server

**定价**：开源免费

### 方案 B: Milvus

**概述**：云原生分布式向量数据库，支持万亿级向量。

**优势**：
- 性能强劲，支持 GPU 加速
- 分布式架构，水平扩展
- 丰富的索引类型 (IVF, HNSW, DiskANN)
- Zilliz Cloud 提供托管服务
- 阿里云、腾讯云有国内节点

**劣势**：
- 部署复杂（依赖 etcd, MinIO 等）
- 本地开发需要 Docker
- 小规模数据杀鸡用牛刀

**定价**：
- 开源自托管：免费
- Zilliz Cloud：$0.08/CU·小时起

### 方案 C: Pinecone

**概述**：全托管向量数据库服务。

**优势**：
- 完全托管，零运维
- 性能稳定
- API 简洁

**劣势**：
- **服务器在美国**，数据出境风险
- 免费层限制严格
- 付费版价格高

### 方案 D: PostgreSQL + pgvector

**概述**：PostgreSQL 扩展，支持向量操作。

**优势**：
- 复用现有 PostgreSQL
- SQL 原生，学习成本低
- 事务支持
- Supabase 等托管服务支持

**劣势**：
- 向量检索性能不如专用数据库
- 索引类型有限
- 大规模数据需要调优

### 方案 E: Qdrant

**概述**：Rust 实现的高性能向量数据库。

**优势**：
- 性能优异
- 丰富的过滤能力
- Docker 部署简单
- 免费层慷慨

**劣势**：
- 社区相对较小
- 与 LangChain 集成不如 Chroma 成熟

## 决策 (Decision)

**采用分层策略：开发用 Chroma，生产用 Milvus Lite / Qdrant。**

```python
# src/rag/vector_store.py
from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    async def add_documents(self, docs: list[Document]) -> list[str]:
        pass
    
    @abstractmethod
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5,
        filter: dict | None = None
    ) -> list[Document]:
        pass

# 环境配置决定具体实现
def get_vector_store() -> VectorStore:
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "development":
        return ChromaVectorStore(persist_dir="./data/chroma")
    elif env == "production":
        return MilvusVectorStore(
            host=os.getenv("MILVUS_HOST"),
            port=os.getenv("MILVUS_PORT")
        )
```

### 各阶段配置

| 阶段 | 方案 | 理由 |
|------|------|------|
| **本地开发** | Chroma (本地持久化) | 零配置，pip 安装即用 |
| **CI 测试** | Chroma (内存模式) | 测试隔离，无状态 |
| **Demo 部署** | Milvus Lite / Chroma Server | 单机足够，Docker 部署 |
| **生产扩展** | Milvus / Qdrant 集群 | 需要时再迁移 |

## 后果 (Consequences)

### 正面影响

- ✅ 开发体验极佳，无需 Docker 即可开始
- ✅ 成本为零（开发阶段）
- ✅ 抽象层设计，未来可无缝切换
- ✅ LangChain/LlamaIndex 原生支持

### 负面影响

- ⚠️ Chroma 在大规模数据下性能受限
- ⚠️ 开发与生产环境差异可能导致问题

### 缓解措施

- 通过 `VectorStore` 抽象层隔离具体实现
- 集成测试同时覆盖 Chroma 和 Milvus
- 数据迁移脚本预先准备

## 实现示例

```python
# src/rag/chroma_store.py
import chromadb
from chromadb.config import Settings

class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: str = "./data/chroma"):
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir,
            anonymized_telemetry=False
        ))
        self.collection = self.client.get_or_create_collection(
            name="travelmind",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add_documents(self, docs: list[Document]) -> list[str]:
        ids = [doc.id for doc in docs]
        embeddings = await self._embed([doc.content for doc in docs])
        metadatas = [doc.metadata for doc in docs]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=[doc.content for doc in docs]
        )
        return ids
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5,
        filter: dict | None = None
    ) -> list[Document]:
        query_embedding = await self._embed([query])
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k,
            where=filter  # e.g., {"city": "杭州"}
        )
        
        return [
            Document(id=id, content=doc, metadata=meta)
            for id, doc, meta in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0]
            )
        ]
```

## 参考资料

- [Chroma 官方文档](https://docs.trychroma.com/)
- [Milvus 官方文档](https://milvus.io/docs)
- [向量数据库对比 2024](https://www.pinecone.io/learn/vector-database-comparison/)
- [LangChain Vector Stores](https://python.langchain.com/docs/modules/data_connection/vectorstores/)
