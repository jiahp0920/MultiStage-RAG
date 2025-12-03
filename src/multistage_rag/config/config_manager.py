"""
配置管理器 - 负责加载、验证和管理配置
"""
import os
import yaml
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
from .schema import AppConfig
from ..utils.logger import get_logger


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.config_path = config_path
        self.config = None
        self.config_dict = {}

        # 加载环境变量
        load_dotenv()

        # 自动查找配置文件
        if not config_path:
            config_path = self._find_config_file()

        if config_path:
            self.load_config(config_path)
        else:
            self.logger.warning("No config file found, using default configuration")
            self.config = AppConfig()

    def _find_config_file(self) -> Optional[str]:
        """查找配置文件"""
        possible_paths = [
            "./configs/default_config.yaml",
            "./configs/config.yaml",
            "./config.yaml",
            "./config.yml",
            os.path.expanduser("~/.multistage_rag/config.yaml"),
            "/etc/multistage_rag/config.yaml"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"Found config file: {path}")
                return path

        return None

    def _replace_env_vars(self, value: Any) -> Any:
        """替换环境变量"""
        if isinstance(value, str):
            # 替换 ${VAR_NAME} 格式的环境变量
            import re
            pattern = r'\$\{([^}]+)\}'

            def replace_match(match):
                var_name = match.group(1)
                env_value = os.getenv(var_name)
                if env_value is None:
                    self.logger.warning(f"Environment variable {var_name} not found")
                    return match.group(0)  # 保持原样
                return env_value

            return re.sub(pattern, replace_match, value)

        elif isinstance(value, dict):
            return {k: self._replace_env_vars(v) for k, v in value.items()}

        elif isinstance(value, list):
            return [self._replace_env_vars(item) for item in value]

        else:
            return value

    def load_config(self, config_path: str) -> 'ConfigManager':
        """加载配置文件"""
        try:
            self.config_path = config_path
            path = Path(config_path)

            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

            # 根据文件类型加载
            if path.suffix in ['.yaml', '.yml']:
                with open(path, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f)
            elif path.suffix == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")

            if not config_dict:
                raise ValueError("Config file is empty")

            # 替换环境变量
            config_dict = self._replace_env_vars(config_dict)
            self.config_dict = config_dict

            # 使用Pydantic验证配置
            self.config = AppConfig(**config_dict)

            self.logger.info(f"Configuration loaded from {config_path}")
            return self

        except Exception as e:
            self.logger.error(f"Failed to load config from {config_path}: {str(e)}")
            # 回退到默认配置
            self.logger.info("Falling back to default configuration")
            self.config = AppConfig()
            return self

    def get_config(self) -> AppConfig:
        """获取配置对象"""
        if self.config is None:
            self.config = AppConfig()
        return self.config

    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        if self.config:
            return self.config.model_dump()
        return self.config_dict

    def update_config(self, updates: Dict[str, Any]) -> 'ConfigManager':
        """更新配置"""
        try:
            # 合并更新
            current_dict = self.get_config_dict()
            updated_dict = self._deep_merge(current_dict, updates)

            # 重新验证
            self.config = AppConfig(**updated_dict)
            self.config_dict = updated_dict

            self.logger.info("Configuration updated")
            return self

        except Exception as e:
            self.logger.error(f"Failed to update config: {str(e)}")
            raise

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(self, save_path: Optional[str] = None) -> str:
        """保存配置到文件"""
        if save_path is None:
            if self.config_path:
                save_path = self.config_path
            else:
                save_path = "./configs/saved_config.yaml"

        try:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            config_dict = self.get_config_dict()

            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"Configuration saved to {save_path}")
            return save_path

        except Exception as e:
            self.logger.error(f"Failed to save config to {save_path}: {str(e)}")
            raise

    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """获取组件配置"""
        config_dict = self.get_config_dict()

        # 映射组件名称到配置路径
        component_map = {
            "vector_store": "vector_store",
            "reranker": "reranker",
            "cache": "cache",
            "llm": "llm",
            "rule_engine": "rule_engine"
        }

        if component_name not in component_map:
            raise ValueError(f"Unknown component: {component_name}")

        config_path = component_map[component_name]
        parts = config_path.split('.')

        current = config_dict
        for part in parts:
            current = current.get(part, {})

        return current

    def validate(self) -> bool:
        """验证配置"""
        try:
            # 使用Pydantic验证
            _ = AppConfig(**self.config_dict)
            self.logger.info("Configuration validation passed")
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            return False

    def get_env_vars(self) -> Dict[str, str]:
        """获取需要的环境变量"""
        env_vars = {}

        # 从配置中提取环境变量引用
        def extract_env_vars(value, path=""):
            if isinstance(value, str):
                import re
                matches = re.findall(r'\$\{([^}]+)\}', value)
                for match in matches:
                    env_vars[match] = os.getenv(match, "")

            elif isinstance(value, dict):
                for k, v in value.items():
                    new_path = f"{path}.{k}" if path else k
                    extract_env_vars(v, new_path)

            elif isinstance(value, list):
                for i, item in enumerate(value):
                    new_path = f"{path}[{i}]"
                    extract_env_vars(item, new_path)

        extract_env_vars(self.config_dict)
        return env_vars


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager