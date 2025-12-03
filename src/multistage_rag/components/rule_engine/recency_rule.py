"""
时效性规则
"""
import time
from typing import Dict, Any, Optional
from ...core.models import Document
from .base import BaseRule


class RecencyRule(BaseRule):
    """时效性规则：越新的文档分数越高"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.recent_days = config.get("recent_days", 7)
        self.older_penalty = config.get("older_penalty", 0.1)

    def calculate_score(self, document: Document, query: Optional[str] = None) -> float:
        """计算时效性分数"""
        score = 0.0

        # 检查发布时间
        if "publish_date" in document.metadata:
            try:
                publish_time = document.metadata["publish_date"]

                # 如果是时间戳
                if isinstance(publish_time, (int, float)):
                    days_old = (time.time() - publish_time) / 86400
                # 如果是字符串，尝试解析
                else:
                    # 简化处理，实际应使用日期解析
                    days_old = 365  # 默认认为较旧

                # 计算分数
                if days_old < self.recent_days:
                    score = 1.0 - (days_old / self.recent_days) * 0.5
                elif days_old < 30:  # 一个月内
                    score = 0.5
                elif days_old < 365:  # 一年内
                    score = 0.2
                else:  # 超过一年
                    score = -self.older_penalty

            except Exception:
                score = 0.0

        return max(-1.0, min(1.0, score))  # 限制在[-1, 1]范围