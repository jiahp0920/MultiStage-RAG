"""
规则引擎工厂
"""
from typing import Dict, Any, List
import importlib
from .base import BaseRule
from .rule_engine import RuleEngine
from ...utils.logger import get_logger


class RuleEngineFactory:
    """规则引擎工厂类"""

    @staticmethod
    def create(config: Dict[str, Any]) -> RuleEngine:
        """创建规则引擎实例"""
        logger = get_logger(__name__)
        logger.info("Creating RuleEngine")

        try:
            return RuleEngine(config)
        except Exception as e:
            logger.error(f"Failed to create RuleEngine: {str(e)}")
            raise

    @staticmethod
    def create_rule(rule_name: str, config: Dict[str, Any]) -> BaseRule:
        """创建单个规则实例"""
        logger = get_logger(__name__)

        # 规则名称到类名的映射
        rule_class_map = {
            "recency": "RecencyRule",
            "authority": "AuthorityRule",
            "keyword": "KeywordRule",
            "length": "LengthRule",
        }

        if rule_name not in rule_class_map:
            raise ValueError(f"Unknown rule type: {rule_name}")

        class_name = rule_class_map[rule_name]

        try:
            # 动态导入规则模块
            module_name = f"multistage_rag.components.rule_engine.{rule_name}_rule"
            module = importlib.import_module(module_name)

            # 获取规则类
            rule_class = getattr(module, class_name)

            # 创建实例
            rule_instance = rule_class(config)
            logger.info(f"Created rule: {rule_name}")
            return rule_instance

        except ImportError as e:
            logger.error(f"Failed to import rule module: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create rule {rule_name}: {str(e)}")
            raise