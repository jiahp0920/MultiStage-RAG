"""
规则引擎主类
"""
from typing import List, Dict, Any, Optional
from .base import BaseRule
from ...core.models import Document
from ...utils.logger import get_logger


class RuleEngine:
    """规则引擎，组合多个规则"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 加载启用的规则
        self.rules = self._load_rules(config)
        self.logger.info(f"RuleEngine initialized with {len(self.rules)} rules")

    def _load_rules(self, config: Dict[str, Any]) -> List[BaseRule]:
        """加载规则"""
        rules = []
        enabled_rules = config.get("enabled_rules", [])
        rule_params = config.get("rule_params", {})

        # 规则映射
        rule_classes = {
            "recency": "RecencyRule",
            "authority": "AuthorityRule",
            "keyword": "KeywordRule",
        }

        for rule_name in enabled_rules:
            if rule_name in rule_classes:
                try:
                    # 动态导入规则类
                    module_name = f"multistage_rag.components.rule_engine.{rule_name}_rule"
                    module = __import__(module_name, fromlist=[rule_classes[rule_name]])
                    rule_class = getattr(module, rule_classes[rule_name])

                    # 获取规则配置
                    rule_config = rule_params.get(rule_name, {})

                    # 创建规则实例
                    rule_instance = rule_class(rule_config)
                    rules.append(rule_instance)

                    self.logger.info(f"Loaded rule: {rule_name}")

                except Exception as e:
                    self.logger.error(f"Failed to load rule {rule_name}: {str(e)}")

        return rules

    def calculate_score(self, document: Document, query: Optional[str] = None) -> float:
        """计算文档的总规则分数"""
        if not self.rules:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for rule in self.rules:
            try:
                rule_score = rule.calculate_score(document, query)
                weighted_score = rule_score * rule.weight

                total_score += weighted_score
                total_weight += rule.weight

            except Exception as e:
                self.logger.error(f"Rule {rule.name} calculation failed: {str(e)}")
                continue

        # 归一化分数
        if total_weight > 0:
            return total_score / total_weight
        return 0.0

    def get_rule_info(self) -> List[Dict[str, Any]]:
        """获取规则信息"""
        return [
            {
                "name": rule.name,
                "weight": rule.weight,
                "description": rule.get_description()
            }
            for rule in self.rules
        ]