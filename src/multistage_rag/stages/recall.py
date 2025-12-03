from typing import List, Dict, Any, Optional
import asyncio
from .base import BaseStage
from ..core.models import Document, StageType
from ..components.vector_store.factory import VectorStoreFactory


class RecallStage(BaseStage):
    """召回阶段"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, StageType.RECALL)
        self.top_k = config.get("top_k", 100)
        self.score_threshold = config.get("score_threshold", 0.0)

        # 初始化向量存储
        vector_store_config = config.get("vector_store", {})
        self.vector_store = VectorStoreFactory.create(vector_store_config)

    async def execute(self, query: str, documents: List[Document], **kwargs) -> List[Document]:
        # 如果已经有文档（测试用），直接返回
        if documents:
            return documents

        filters = kwargs.get("filters")

        # 异步执行向量搜索
        loop = asyncio.get_event_loop()
        recalled_docs = await loop.run_in_executor(
            None,
            lambda: self.vector_store.search(query, self.top_k, filters)
        )

        # 分数过滤
        if self.score_threshold > 0:
            recalled_docs = [
                doc for doc in recalled_docs
                if doc.vector_score >= self.score_threshold
            ]

        return recalled_docs