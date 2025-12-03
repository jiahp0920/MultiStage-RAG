from typing import List, Dict, Any
import asyncio
from .base import BaseStage
from ..core.models import Document, StageType
from ..components.rule_engine.factory import RuleEngineFactory
from ..utils.bm25 import BM25Ranker


class PreRankStage(BaseStage):
    """粗排阶段"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, StageType.PRE_RANK)
        self.top_k = config.get("top_k", 20)
        self.bm25_weight = config.get("bm25_weight", 0.7)
        self.rule_weight = config.get("rule_weight", 0.3)

        # 初始化规则引擎
        rule_config = config.get("rule_engine", {})
        self.rule_engine = RuleEngineFactory.create(rule_config)

        # 初始化BM25
        self.bm25_ranker = BM25Ranker(
            k1=config.get("bm25_k1", 1.5),
            b=config.get("bm25_b", 0.75)
        )

    async def execute(self, query: str, documents: List[Document], **kwargs) -> List[Document]:
        if not documents:
            return []

        # 异步计算BM25分数
        loop = asyncio.get_event_loop()
        documents_with_bm25 = await loop.run_in_executor(
            None,
            lambda: self.bm25_ranker.rank(query, documents)
        )

        # 应用规则引擎
        for doc in documents_with_bm25:
            rule_score = self.rule_engine.calculate_score(doc, query)
            doc.rule_score = rule_score
            doc.final_score = (
                    self.bm25_weight * doc.bm25_score +
                    self.rule_weight * rule_score
            )

        # 排序并截断
        sorted_docs = sorted(documents_with_bm25, key=lambda x: x.final_score, reverse=True)
        return sorted_docs[:self.top_k]