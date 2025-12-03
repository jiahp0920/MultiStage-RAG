"""
LLM工厂
"""
from typing import Dict, Any
import importlib
from .base import BaseLLM
from ...utils.logger import get_logger


class LLMFactory:
    """LLM工厂类"""

    @staticmethod
    def create(config: Dict[str, Any]) -> BaseLLM:
        """创建LLM实例"""
        logger = get_logger(__name__)

        # 获取LLM类型
        llm_type = config.get("type", "openai")
        logger.info(f"Creating LLM of type: {llm_type}")

        # 动态导入对应的模块
        try:
            module_name = f"multistage_rag.components.llm.{llm_type}_llm"
            module = importlib.import_module(module_name)

            # 查找BaseLLM的子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (isinstance(attr, type) and
                        issubclass(attr, BaseLLM) and
                        attr != BaseLLM):
                    # 提取该类型的配置
                    type_config = config.get(llm_type, {})

                    # 创建实例
                    instance = attr(type_config)
                    logger.info(f"Successfully created LLM: {llm_type}")
                    return instance

            raise ValueError(f"No LLM implementation found for type: {llm_type}")

        except ImportError as e:
            logger.error(f"Failed to import LLM module: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create LLM: {str(e)}")
            raise