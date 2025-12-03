"""
通义千问LLM实现
"""
import dashscope
from typing import List, Dict, Any, Optional
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseLLM
from ...utils.logger import get_logger


class QwenLLM(BaseLLM):
    """通义千问LLM"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "qwen-max")
        self.temperature = config.get("temperature", 0.1)
        self.max_tokens = config.get("max_tokens", 1000)

        # 设置API密钥
        if self.api_key:
            dashscope.api_key = self.api_key
        else:
            raise ValueError("Qwen API key is required")

        self.logger.info(f"Qwen LLM initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_qwen_api(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """调用通义千问API"""
        try:
            # 同步调用API（通过线程池转换为异步）
            loop = asyncio.get_event_loop()

            def sync_call():
                response = dashscope.Generation.call(
                    model=self.model,
                    messages=messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                    result_format='message'
                )

                if response.status_code == 200:
                    return response.output.choices[0].message.content
                else:
                    raise Exception(f"API error: {response.code} - {response.message}")

            return await loop.run_in_executor(None, sync_call)

        except Exception as e:
            self.logger.error(f"Qwen API call failed: {str(e)}")
            raise

    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        messages = [
            {"role": "user", "content": prompt}
        ]

        return await self.chat(messages, **kwargs)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话"""
        return await self._call_qwen_api(messages, **kwargs)

    async def embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        try:
            # 通义千问的嵌入API调用
            loop = asyncio.get_event_loop()

            def sync_call():
                response = dashscope.TextEmbedding.call(
                    model="text-embedding-v2",
                    input=text
                )

                if response.status_code == 200:
                    return response.output.embeddings[0].embedding
                else:
                    raise Exception(f"API error: {response.code} - {response.message}")

            return await loop.run_in_executor(None, sync_call)

        except Exception as e:
            self.logger.error(f"Qwen embedding failed: {str(e)}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "type": "qwen",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

    async def close(self):
        """关闭连接"""
        # 通义千问API不需要显式关闭
        self.logger.info("Qwen LLM closed")