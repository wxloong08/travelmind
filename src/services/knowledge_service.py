"""
RAG 知识库服务

用于缓存博查搜索结果，减少 API 调用
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger()


class TravelKnowledgeBase:
    """
    旅游知识库
    
    策略：
    1. 搜索时先查本地向量库
    2. 如果本地有足够相似的结果，直接返回
    3. 如果本地没有，调用博查 API 并存入向量库
    """
    
    # 相似度阈值（0-1，越高要求越严格）
    SIMILARITY_THRESHOLD = 0.75
    
    # 每个查询最少需要的结果数
    MIN_RESULTS = 3
    
    def __init__(self):
        self._initialized = False
        self._store = None
    
    async def _ensure_initialized(self):
        """延迟初始化向量库"""
        if self._initialized:
            return
        
        try:
            from src.rag import get_vector_store
            self._store = get_vector_store()
            self._initialized = True
            logger.info("Travel knowledge base initialized")
        except Exception as e:
            logger.warning("Failed to initialize vector store", error=str(e))
            self._initialized = True  # 标记为已初始化，避免重复尝试
    
    def _generate_doc_id(self, url: str) -> str:
        """根据 URL 生成文档 ID"""
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    async def search_local(
        self,
        query: str,
        destination: str | None = None,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        在本地知识库搜索
        
        Returns:
            匹配的文档列表，如果向量库不可用则返回空列表
        """
        await self._ensure_initialized()
        
        if not self._store:
            return []
        
        try:
            # 构建过滤条件
            filter_dict = None
            if destination:
                filter_dict = {"destination": destination}
            
            # 执行搜索
            docs = await self._store.similarity_search(
                query=query,
                k=k,
                filter=filter_dict,
            )
            
            results = []
            for doc in docs:
                results.append({
                    "title": doc.metadata.get("title", ""),
                    "snippet": doc.content[:500],
                    "url": doc.metadata.get("url", ""),
                    "source": doc.metadata.get("source", ""),
                    "date": doc.metadata.get("date"),
                    "from_cache": True,
                })
            
            logger.info(
                "Local search completed",
                query=query[:30],
                destination=destination,
                results=len(results),
            )
            
            return results
            
        except Exception as e:
            logger.warning("Local search failed", error=str(e))
            return []
    
    async def store_results(
        self,
        results: list[dict[str, Any]],
        destination: str,
        query_type: str = "general",
    ) -> int:
        """
        存储搜索结果到向量库
        
        Args:
            results: 博查 API 返回的结果列表
            destination: 目的地
            query_type: 查询类型（general/place/food/accommodation）
        
        Returns:
            存储的文档数量
        """
        await self._ensure_initialized()
        
        if not self._store:
            return 0
        
        try:
            from src.rag import Document
            
            docs = []
            for r in results:
                url = r.get("url", "")
                if not url:
                    continue
                
                doc_id = self._generate_doc_id(url)
                
                # 组合标题和摘要作为内容
                content = f"{r.get('title', '')}\n\n{r.get('snippet', '')}"
                
                docs.append(Document(
                    id=doc_id,
                    content=content,
                    metadata={
                        "title": r.get("title", ""),
                        "url": url,
                        "source": r.get("source", ""),
                        "date": r.get("date"),
                        "destination": destination,
                        "query_type": query_type,
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                    },
                ))
            
            if docs:
                ids = await self._store.add_documents(docs)
                logger.info(
                    "Stored search results",
                    destination=destination,
                    query_type=query_type,
                    count=len(ids),
                )
                return len(ids)
            
            return 0
            
        except Exception as e:
            logger.warning("Failed to store results", error=str(e))
            return 0
    
    async def store_full_content(
        self,
        url: str,
        content: str,
        destination: str,
        title: str = "",
    ) -> bool:
        """
        存储抓取的完整攻略内容
        
        Args:
            url: 页面 URL
            content: 完整内容
            destination: 目的地
            title: 标题
        
        Returns:
            是否存储成功
        """
        await self._ensure_initialized()
        
        if not self._store or not content:
            return False
        
        try:
            from src.rag import Document
            
            doc_id = self._generate_doc_id(url) + "_full"
            
            doc = Document(
                id=doc_id,
                content=content[:10000],  # 限制长度
                metadata={
                    "title": title,
                    "url": url,
                    "destination": destination,
                    "is_full_content": True,
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            
            await self._store.add_documents([doc])
            logger.info("Stored full content", url=url[:50], destination=destination)
            return True
            
        except Exception as e:
            logger.warning("Failed to store full content", error=str(e))
            return False
    
    async def search_with_fallback(
        self,
        query: str,
        destination: str | None = None,
        count: int = 5,
        use_api_if_needed: bool = True,
    ) -> tuple[list[dict], bool]:
        """
        搜索并在需要时回退到博查 API
        
        Args:
            query: 搜索查询
            destination: 目的地
            count: 期望的结果数量
            use_api_if_needed: 如果本地结果不足，是否调用 API
        
        Returns:
            (results, from_api) - 结果列表和是否来自 API
        """
        # 先搜索本地
        local_results = await self.search_local(
            query=query,
            destination=destination,
            k=count * 2,  # 多搜一些用于过滤
        )
        
        # 如果本地结果足够，直接返回
        if len(local_results) >= self.MIN_RESULTS:
            logger.info(
                "Using cached results",
                query=query[:30],
                count=len(local_results),
            )
            return local_results[:count], False
        
        # 本地结果不足，调用博查 API
        if use_api_if_needed:
            try:
                from src.tools import web_search
                
                result = await web_search.ainvoke({
                    "query": query,
                    "count": count,
                })
                
                api_results = result.get("results", [])
                
                # 存储结果到本地
                if api_results and destination:
                    await self.store_results(
                        results=api_results,
                        destination=destination,
                        query_type="general",
                    )
                
                logger.info(
                    "Used API search",
                    query=query[:30],
                    count=len(api_results),
                )
                
                return api_results, True
                
            except Exception as e:
                logger.warning("API search failed", error=str(e))
                # API 失败时返回本地结果（即使不足）
                return local_results[:count], False
        
        return local_results[:count], False


# 全局实例
_knowledge_base: TravelKnowledgeBase | None = None


def get_knowledge_base() -> TravelKnowledgeBase:
    """获取知识库单例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = TravelKnowledgeBase()
    return _knowledge_base
