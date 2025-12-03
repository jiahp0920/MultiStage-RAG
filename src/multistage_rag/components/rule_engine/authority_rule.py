"""
权威性规则
"""
from typing import Dict, Any, Optional
from ...core.models import Document
from .base import BaseRule


class AuthorityRule(BaseRule):
    """权威性规则：根据来源权威性评分"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 默认来源权重
        self.source_weights = {
            "wikipedia": 1.0,
            "textbook": 0.9,
            "research_paper": 0.8,
            "news": 0.6,
            "blog": 0.3,
            "forum": 0.2,
            "unknown": 0.1
        }
        # 覆盖配置中的权重
        self.source_weights.update(config.get("source_weights", {}))

    def calculate_score(self, document: Document, query: Optional[str] = None) -> float:
        """计算权威性分数"""
        source = document.metadata.get("source", "unknown")

        # 获取来源权重
        weight = self.source_weights.get(source, self.source_weights["unknown"])

        # 检查是否有其他权威指标
        if "is_verified" in document.metadata and document.metadata["is_verified"]:
            weight *= 1.2  # 已验证内容加分

        if "citation_count" in document.metadata:
            citations = document.metadata["citation_count"]
            if citations > 100:
                weight *= 1.3
            elif citations > 10:
                weight *= 1.1

        # 确保分数在合理范围
        return min(max(weight, 0.0), 2.0)  # 限制在[0, 2]范围