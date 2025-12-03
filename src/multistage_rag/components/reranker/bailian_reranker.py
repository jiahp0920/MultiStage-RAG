"""
阿里百炼重排序器实现（默认）
"""
import dashscope
from typing import List, Dict, Any
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from ...core.models import Document
from .base import BaseReranker
from ...utils.logger import get_logger


class BailianReranker(BaseReranker):
    """阿里百炼重排序器"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        self.api_key = config.get("api_key", "")
        self.endpoint = config.get("endpoint", "https://dashscope.aliyuncs.com/api/v1/services/rerank")
        self.model = config.get("model", "bailian-rerank-v1")
        self.timeout = config.get("timeout", 5)

        # 设置API密钥
        if self.api_key:
            dashscope.api_key = self.api_key
        else:
            self.logger.warning("Bailian API key not provided")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_rerank_api(self, query: str, documents: List[Dict]) -> List[Dict]:
        """调用百炼重排序API"""
        try:
            # 准备文档列表
            doc_texts = [doc["content"] for doc in documents]

            # 同步调用API（通过线程池转换为异步）
            loop = asyncio.get_event_loop()

            def sync_call():
                response = dashscope.Rerank.call(
                    model=self.model,
                    query=query,
                    documents=doc_texts,
                    top_n=len(documents),
                    return_documents=True
                )

                if response.status_code == 200:
                    return response.output.results
                else:
                    raise Exception(f"API error: {response.code} - {response.message}")

            results = await loop.run_in_executor(None, sync_call)
            return results

        except Exception as e:
            self.logger.error(f"Bailian API call failed: {str(e)}")
            raise

    async def rerank(self, query: str, documents: List[Document], top_k: int) -> List[Document]:
        """执行重排序"""
        if not documents:
            return []

        try:
            # 准备API调用数据
            doc_dicts = [
                {
                    "id": doc.id,
                    "content": doc.content[:5000]  # 限制长度
                }
                for doc in documents
            ]

            # 调用API
            results = await self._call_rerank_api(query, doc_dicts)

            # 更新文档分数
            for result in results:
                doc_idx = result.index
                if doc_idx < len(documents):
                    doc = documents[doc_idx]
                    doc.rerank_score = result.relevance_score
                    doc.final_score = doc.rerank_score
                    doc.metadata["rerank_rank"] = result.rank
                    doc.metadata["rerank_relevance"] = result.relevance_score

            # 按重排序分数排序
            sorted_docs = sorted(documents, key=lambda x: x.rerank_score, reverse=True)

            self.logger.info(f"Bailian rerank completed, scored {len(documents)} documents")
            return sorted_docs[:top_k]

        except Exception as e:
            self.logger.error(f"Bailian rerank failed: {str(e)}")
            # 降级：返回原始顺序
            return documents[:top_k]

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "type": "bailian",
            "model": self.model,
            "endpoint": self.endpoint,
            "timeout": self.timeout
        }

    async def close(self):
        """关闭连接"""
        # 百炼API不需要显式关闭
        pass