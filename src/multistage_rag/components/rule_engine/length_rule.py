"""
长度规则
"""
from typing import Dict, Any, Optional
from ...core.models import Document
from .base import BaseRule


class LengthRule(BaseRule):
    """长度规则：根据文档长度评分"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ideal_min_length = config.get("ideal_min_length", 50)
        self.ideal_max_length = config.get("ideal_max_length", 2000)
        self.too_short_penalty = config.get("too_short_penalty", 0.5)
        self.too_long_penalty = config.get("too_long_penalty", 0.3)

    def calculate_score(self, document: Document, query: Optional[str] = None) -> float:
        """计算长度分数"""
        content_length = len(document.content)

        # 理想长度范围内
        if self.ideal_min_length <= content_length <= self.ideal_max_length:
            # 越接近理想范围中间，分数越高
            ideal_mid = (self.ideal_min_length + self.ideal_max_length) / 2
            distance = abs(content_length - ideal_mid)
            max_distance = (self.ideal_max_length - self.ideal_min_length) / 2

            if max_distance > 0:
                normalized_distance = distance / max_distance
                return 1.0 - normalized_distance * 0.5  # 最高1.0，最低0.5
            return 1.0

        # 太短
        elif content_length < self.ideal_min_length:
            short_ratio = content_length / self.ideal_min_length
            return max(0.0, short_ratio - self.too_short_penalty)

        # 太长
        else:
            # 计算超过的比例
            if content_length < self.ideal_max_length * 2:
                excess_ratio = (content_length - self.ideal_max_length) / self.ideal_max_length
                return max(0.0, 1.0 - excess_ratio * self.too_long_penalty)
            else:
                return 0.0  # 严重超长