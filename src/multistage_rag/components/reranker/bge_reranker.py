"""
BGE重排序器实现（开源替代）
"""
from typing import List, Dict, Any
import torch
from sentence_transformers import CrossEncoder
import asyncio
from ...core.models import Document
from .base import BaseReranker
from ...utils.logger import get_logger


class BGEReranker(BaseReranker):
    """BGE重排序器（开源）"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        self.model_name = config.get("model_name", "BAAI/bge-reranker-large")
        self.device = config.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = config.get("batch_size", 32)

        # 加载模型
        self.logger.info(f"Loading BGE model: {self.model_name} on {self.device}")
        self.model = CrossEncoder(
            self.model_name,
            device=self.device,
            max_length=512
        )

    async def rerank(self, query: str, documents: List[Document], top_k: int) -> List[Document]:
        """执行重排序"""
        if not documents:
            return []

        try:
            # 准备输入对
            pairs = [[query, doc.content[:1000]] for doc in documents]

            # 异步执行推理
            loop = asyncio.get_event_loop()

            def compute_scores():
                scores = self.model.predict(
                    pairs,
                    batch_size=self.batch_size,
                    show_progress_bar=False
                )
                return scores

            scores = await loop.run_in_executor(None, compute_scores)

            # 更新文档分数
            for i, doc in enumerate(documents):
                if i < len(scores):
                    doc.rerank_score = float(scores[i])
                    doc.final_score = doc.rerank_score

            # 按重排序分数排序
            sorted_docs = sorted(documents, key=lambda x: x.rerank_score, reverse=True)

            self.logger.info(f"BGE rerank completed, scored {len(documents)} documents")
            return sorted_docs[:top_k]

        except Exception as e:
            self.logger.error(f"BGE rerank failed: {str(e)}")
            return documents[:top_k]

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "type": "bge",
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size
        }

    async def close(self):
        """关闭模型"""
        # BGE模型会自动清理
        pass