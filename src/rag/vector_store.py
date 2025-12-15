"""
向量数据库模块

使用 Chroma 进行 RAG 支持
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass
class Document:
    """文档数据类"""

    id: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None


class VectorStore(ABC):
    """向量存储抽象基类"""

    @abstractmethod
    async def add_documents(self, docs: list[Document]) -> list[str]:
        """添加文档"""
        pass

    @abstractmethod
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """相似度搜索"""
        pass

    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        """删除文档"""
        pass


class ChromaVectorStore(VectorStore):
    """Chroma 向量存储实现"""

    def __init__(
        self,
        collection_name: str = "travelmind",
        persist_directory: str | None = None,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory or settings.chroma_persist_dir

        # 确保目录存在
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        self._client = None
        self._collection = None
        self._embedding_func = None

    def _get_client(self):
        """延迟初始化 Chroma 客户端"""
        if self._client is None:
            import chromadb

            # 使用 PersistentClient 进行持久化存储（ChromaDB 0.4+ 的正确方式）
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info("ChromaDB PersistentClient initialized", path=self.persist_directory)
        return self._client

    def _get_collection(self):
        """获取或创建集合"""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB collection ready", name=self.collection_name, count=self._collection.count())
        return self._collection

    async def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """获取文本嵌入"""
        from src.llm import get_llm

        llm = get_llm()
        return await llm.embed(texts)

    async def add_documents(self, docs: list[Document]) -> list[str]:
        """添加文档到向量存储"""
        if not docs:
            return []

        logger.info("Adding documents to vector store", count=len(docs))

        collection = self._get_collection()

        # 获取嵌入
        texts = [doc.content for doc in docs]
        embeddings = await self._get_embeddings(texts)

        # 准备数据
        ids = [doc.id for doc in docs]
        metadatas = [doc.metadata for doc in docs]

        # 添加到 Chroma
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info("Documents added", count=len(ids))
        return ids

    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """执行相似度搜索"""
        logger.debug("Similarity search", query=query[:50], k=k)

        collection = self._get_collection()

        # 获取查询嵌入
        query_embedding = (await self._get_embeddings([query]))[0]

        # 构建查询参数
        query_params: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": k,
        }

        if filter:
            query_params["where"] = filter

        # 执行查询
        results = collection.query(**query_params)

        # 转换结果
        documents = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                documents.append(
                    Document(
                        id=doc_id,
                        content=results["documents"][0][i] if results["documents"] else "",
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    )
                )

        logger.info("Search completed", query=query[:30], results=len(documents))
        return documents

    async def delete(self, ids: list[str]) -> None:
        """删除文档"""
        if not ids:
            return

        collection = self._get_collection()
        collection.delete(ids=ids)
        logger.info("Documents deleted", count=len(ids))

    def persist(self) -> None:
        """持久化到磁盘（PersistentClient 自动持久化，此方法为兼容保留）"""
        # PersistentClient 会自动持久化，无需手动调用
        logger.debug("Persist called (PersistentClient auto-persists)")


# 全局实例
_vector_store: ChromaVectorStore | None = None


def get_vector_store() -> ChromaVectorStore:
    """获取向量存储单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore()
    return _vector_store


# ============================================================
# 便捷函数
# ============================================================


async def index_travel_guides(guides: list[dict[str, Any]]) -> list[str]:
    """
    索引旅游攻略

    Args:
        guides: 攻略列表，每项包含 title, content, city, tags 等字段

    Returns:
        索引的文档 ID 列表
    """
    import hashlib

    documents = []
    for guide in guides:
        doc_id = hashlib.md5(guide.get("title", "").encode()).hexdigest()[:16]
        documents.append(
            Document(
                id=doc_id,
                content=guide.get("content", ""),
                metadata={
                    "title": guide.get("title", ""),
                    "city": guide.get("city", ""),
                    "tags": guide.get("tags", []),
                    "source": guide.get("source", ""),
                },
            )
        )

    store = get_vector_store()
    return await store.add_documents(documents)


async def search_travel_guides(
    query: str,
    city: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """
    搜索旅游攻略

    Args:
        query: 搜索查询
        city: 可选的城市过滤
        k: 返回数量

    Returns:
        匹配的攻略列表
    """
    store = get_vector_store()

    filter_dict = None
    if city:
        filter_dict = {"city": city}

    docs = await store.similarity_search(query, k=k, filter=filter_dict)

    return [
        {
            "id": doc.id,
            "content": doc.content,
            **doc.metadata,
        }
        for doc in docs
    ]
