"""
关键词规则
"""
from typing import Dict, Any, Optional, List
import re
from ...core.models import Document
from .base import BaseRule


class KeywordRule(BaseRule):
    """关键词规则：基于关键词匹配评分"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mandatory_keywords = config.get("mandatory_keywords", [])
        self.boost_keywords = config.get("boost_keywords", [])
        self.penalty_keywords = config.get("penalty_keywords", [])
        self.keyword_weights = config.get("keyword_weights", {})

        # 编译正则表达式以提高性能
        self.mandatory_patterns = [re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
                                   for kw in self.mandatory_keywords]
        self.boost_patterns = [re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
                               for kw in self.boost_keywords]
        self.penalty_patterns = [re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
                                 for kw in self.penalty_keywords]

    def _count_keyword_matches(self, text: str, patterns: List[re.Pattern]) -> int:
        """统计关键词匹配次数"""
        count = 0
        lower_text = text.lower()

        for pattern in patterns:
            matches = pattern.findall(lower_text)
            count += len(matches)

        return count

    def calculate_score(self, document: Document, query: Optional[str] = None) -> float:
        """计算关键词分数"""
        score = 0.0
        content = document.content.lower()

        # 1. 检查必须关键词
        if self.mandatory_patterns:
            has_all_mandatory = all(
                self._count_keyword_matches(content, [pattern]) > 0
                for pattern in self.mandatory_patterns
            )
            if not has_all_mandatory:
                return -1.0  # 缺少必须关键词，严重扣分

        # 2. 加分关键词
        boost_count = self._count_keyword_matches(content, self.boost_patterns)
        if boost_count > 0:
            score += min(boost_count * 0.3, 2.0)  # 每个加分词加0.3分，最多2分

        # 3. 减分关键词
        penalty_count = self._count_keyword_matches(content, self.penalty_patterns)
        if penalty_count > 0:
            score -= min(penalty_count * 0.2, 1.0)  # 每个减分词减0.2分，最多减1分

        # 4. 特定权重关键词
        for keyword, weight in self.keyword_weights.items():
            pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
            if pattern.search(content):
                score += weight

        # 5. 如果查询存在，计算查询关键词匹配
        if query:
            query_keywords = re.findall(r'\b\w+\b', query.lower())
            for keyword in query_keywords:
                if len(keyword) > 2:  # 忽略短词
                    pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
                    if pattern.search(content):
                        score += 0.1  # 每个查询词匹配加0.1分

        return max(-1.0, min(score, 3.0))  # 限制在[-1, 3]范围