from typing import List, Dict, Any
import hashlib
import json
import asyncio
from .base import BaseStage
from ..core.models import Document, StageType
from ..components.reranker.factory import RerankerFactory
from ..components.cache.factory import CacheFactory


class ReRankStage(BaseStage):
    """精排阶段"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, StageType.RE_RANK)
        self.top_k = config.get("top_k", 5)
        self.cache_ttl = config.get("cache_ttl", 3600)

        # 初始化重排序器
        reranker_config = config.get("reranker", {})
        self.reranker = RerankerFactory.create(reranker_config)

        # 初始化缓存
        cache_config = config.get("cache", {})
        self.cache = CacheFactory.create(cache_config)

    def _generate_cache_key(self, query: str, documents: List[Document]) -> str:
        """生成缓存键"""
        doc_signatures = []
        for doc in sorted(documents, key=lambda x: x.id):
            content_hash = hashlib.md5(doc.content.encode()).hexdigest()[:16]
            doc_signatures.append(f"{doc.id}:{content_hash}")

        normalized_query = " ".join(query.strip().lower().split())
        cache_str = f"rerank:{normalized_query}:{'|'.join(doc_signatures)}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    async def execute(self, query: str, documents: List[Document], **kwargs) -> List[Document]:
        if not documents:
            return []

        use_cache = kwargs.get("use_cache", True)
        cache_key = self._generate_cache_key(query, documents)

        # 尝试从缓存读取
        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Rerank cache hit: {cache_key[:12]}...")
                scores = json.loads(cached_result)

                for i, doc in enumerate(documents):
                    if i < len(scores):
                        doc.rerank_score = scores[i]
                        doc.final_score = doc.rerank_score

                sorted_docs = sorted(documents, key=lambda x: x.rerank_score, reverse=True)
                return sorted_docs[:self.top_k]

        # 调用重排序器
        self.logger.info(f"Calling reranker API")
        try:
            reranked_docs = await self.reranker.rerank(
                query=query,
                documents=documents,
                top_k=min(len(documents), self.top_k * 2)
            )

            # 缓存结果
            if use_cache:
                scores = [doc.rerank_score for doc in reranked_docs]
                cache_value = json.dumps(scores)
                asyncio.create_task(
                    self.cache.set(cache_key, cache_value, self.cache_ttl)
                )

            return reranked_docs[:self.top_k]

        except Exception as e:
            self.logger.error(f"Reranker failed: {str(e)}")
            # 降级：按当前分数排序
            sorted_docs = sorted(documents, key=lambda x: x.final_score, reverse=True)
            return sorted_docs[:self.top_k]