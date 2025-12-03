"""
重排序器工厂
"""
from typing import Dict, Any
import importlib
from .base import BaseReranker
from ...utils.logger import get_logger


class RerankerFactory:
    """重排序器工厂类"""

    @staticmethod
    def create(config: Dict[str, Any]) -> BaseReranker:
        """创建重排序器实例"""
        logger = get_logger(__name__)

        # 获取重排序器类型
        reranker_type = config.get("type", "bailian")
        logger.info(f"Creating reranker of type: {reranker_type}")

        # 动态导入对应的模块
        try:
            module_name = f"multistage_rag.components.reranker.{reranker_type}_reranker"
            module = importlib.import_module(module_name)

            # 查找BaseReranker的子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (isinstance(attr, type) and
                        issubclass(attr, BaseReranker) and
                        attr != BaseReranker):
                    # 提取该类型的配置
                    type_config = config.get(reranker_type, {})

                    # 创建实例
                    instance = attr(type_config)
                    logger.info(f"Successfully created reranker: {reranker_type}")
                    return instance

            raise ValueError(f"No Reranker implementation found for type: {reranker_type}")

        except ImportError as e:
            logger.error(f"Failed to import reranker module: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create reranker: {str(e)}")
            raise