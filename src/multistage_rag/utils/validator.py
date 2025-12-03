"""
验证工具函数
"""
import re
import json
import yaml
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlparse
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Validator:
    """验证器类"""

    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_json(data: str) -> bool:
        """验证JSON格式"""
        try:
            json.loads(data)
            return True
        except json.JSONDecodeError:
            return False

    @staticmethod
    def validate_yaml(data: str) -> bool:
        """验证YAML格式"""
        try:
            yaml.safe_load(data)
            return True
        except yaml.YAMLError:
            return False

    @staticmethod
    def validate_api_key(api_key: str, provider: str = "openai") -> bool:
        """验证API密钥格式"""
        if not api_key or not isinstance(api_key, str):
            return False

        api_key = api_key.strip()

        # 根据提供商验证格式
        if provider == "openai":
            # OpenAI API密钥格式: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            return api_key.startswith("sk-") and len(api_key) >= 30

        elif provider == "cohere":
            # Cohere API密钥格式: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            return len(api_key) >= 30 and not api_key.startswith("sk-")

        elif provider == "bailian":
            # 阿里百炼API密钥格式: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            return len(api_key) >= 20

        else:
            # 通用验证：至少20个字符
            return len(api_key) >= 20

    @staticmethod
    def validate_document(document: Dict[str, Any]) -> Tuple[bool, str]:
        """验证文档格式"""
        required_fields = ["id", "content"]

        for field in required_fields:
            if field not in document:
                return False, f"Missing required field: {field}"

        if not isinstance(document["id"], str):
            return False, "Field 'id' must be a string"

        if not isinstance(document["content"], str):
            return False, "Field 'content' must be a string"

        if len(document["content"].strip()) == 0:
            return False, "Field 'content' cannot be empty"

        # 可选字段验证
        if "metadata" in document and not isinstance(document["metadata"], dict):
            return False, "Field 'metadata' must be a dictionary"

        return True, "Valid"

    @staticmethod
    def validate_query(query: str, min_length: int = 1, max_length: int = 1000) -> Tuple[bool, str]:
        """验证查询字符串"""
        if not isinstance(query, str):
            return False, "Query must be a string"

        query = query.strip()

        if len(query) < min_length:
            return False, f"Query too short (minimum {min_length} characters)"

        if len(query) > max_length:
            return False, f"Query too long (maximum {max_length} characters)"

        # 检查是否包含有效字符（至少一个字母或数字）
        if not re.search(r'[a-zA-Z0-9]', query):
            return False, "Query must contain at least one alphanumeric character"

        return True, "Valid"

    @staticmethod
    def validate_top_k(top_k: int, min_value: int = 1, max_value: int = 100) -> Tuple[bool, str]:
        """验证top_k参数"""
        if not isinstance(top_k, int):
            return False, "top_k must be an integer"

        if top_k < min_value:
            return False, f"top_k must be at least {min_value}"

        if top_k > max_value:
            return False, f"top_k must be at most {max_value}"

        return True, "Valid"

    @staticmethod
    def validate_filters(filters: Dict[str, Any]) -> Tuple[bool, str]:
        """验证过滤器"""
        if not isinstance(filters, dict):
            return False, "Filters must be a dictionary"

        # 验证每个过滤器
        for key, value in filters.items():
            if not isinstance(key, str):
                return False, f"Filter key must be string, got {type(key)}"

            # 验证值类型
            valid_types = (str, int, float, bool, list)
            if not isinstance(value, valid_types):
                return False, f"Filter value must be str, int, float, bool, or list, got {type(value)}"

            # 如果是列表，验证列表元素
            if isinstance(value, list):
                if len(value) == 0:
                    return False, f"Filter list cannot be empty for key: {key}"

                # 列表元素必须同类型
                first_type = type(value[0])
                valid_item_types = (str, int, float, bool)

                if first_type not in valid_item_types:
                    return False, f"List items must be str, int, float, or bool for key: {key}"

                for item in value[1:]:
                    if type(item) != first_type:
                        return False, f"All list items must be same type for key: {key}"

        return True, "Valid"

    @staticmethod
    def validate_config_section(config: Dict[str, Any],
                                required_fields: List[str],
                                section_name: str = "config") -> Tuple[bool, str]:
        """验证配置部分"""
        if not isinstance(config, dict):
            return False, f"{section_name} must be a dictionary"

        for field in required_fields:
            if field not in config:
                return False, f"Missing required field '{field}' in {section_name}"

        return True, "Valid"

    @staticmethod
    def validate_cache_key(key: str) -> Tuple[bool, str]:
        """验证缓存键"""
        if not isinstance(key, str):
            return False, "Cache key must be a string"

        if len(key) == 0:
            return False, "Cache key cannot be empty"

        if len(key) > 256:
            return False, "Cache key too long (maximum 256 characters)"

        # 允许的字符：字母、数字、下划线、冒号、点、连字符
        if not re.match(r'^[a-zA-Z0-9_:\-\.]+$', key):
            return False, "Cache key contains invalid characters"

        return True, "Valid"

    @staticmethod
    def validate_port(port: int) -> Tuple[bool, str]:
        """验证端口号"""
        if not isinstance(port, int):
            return False, "Port must be an integer"

        if port < 1 or port > 65535:
            return False, "Port must be between 1 and 65535"

        if port < 1024:
            logger.warning(f"Port {port} is in system port range (1-1023)")

        return True, "Valid"


def validate_request_data(data: Dict[str, Any],
                          required_fields: List[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """验证请求数据"""
    if not isinstance(data, dict):
        return False, "Request data must be a dictionary", {}

    # 检查必需字段
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}", {}

    # 清理数据：移除None值，去除字符串空格
    cleaned_data = {}
    for key, value in data.items():
        if value is None:
            continue

        if isinstance(value, str):
            cleaned_data[key] = value.strip()
        else:
            cleaned_data[key] = value

    return True, "Valid", cleaned_data


def validate_batch_size(batch_size: int,
                        min_size: int = 1,
                        max_size: int = 100) -> Tuple[bool, str]:
    """验证批量大小"""
    if not isinstance(batch_size, int):
        return False, "Batch size must be an integer"

    if batch_size < min_size:
        return False, f"Batch size must be at least {min_size}"

    if batch_size > max_size:
        return False, f"Batch size must be at most {max_size}"

    return True, "Valid"


def validate_threshold(threshold: float,
                       min_value: float = 0.0,
                       max_value: float = 1.0) -> Tuple[bool, str]:
    """验证阈值"""
    if not isinstance(threshold, (int, float)):
        return False, "Threshold must be a number"

    if threshold < min_value:
        return False, f"Threshold must be at least {min_value}"

    if threshold > max_value:
        return False, f"Threshold must be at most {max_value}"

    return True, "Valid"


# 常用验证函数的快捷方式
validate_url = Validator.validate_url
validate_email = Validator.validate_email
validate_json = Validator.validate_json
validate_query = Validator.validate_query
validate_top_k = Validator.validate_top_k
validate_filters = Validator.validate_filters