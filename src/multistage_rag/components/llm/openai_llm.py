"""
OpenAI LLM实现
"""
import openai
from typing import List, Dict, Any, Optional
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseLLM
from ...utils.logger import get_logger


class OpenAILLM(BaseLLM):
    """OpenAI LLM"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.temperature = config.get("temperature", 0.1)
        self.max_tokens = config.get("max_tokens", 1000)
        self.timeout = config.get("timeout", 30)

        # 初始化OpenAI客户端
        if self.api_key:
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        else:
            raise ValueError("OpenAI API key is required")

        self.logger.info(f"OpenAI LLM initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """调用Chat Completion API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                timeout=self.timeout
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {str(e)}")
            raise

    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        messages = [
            {"role": "user", "content": prompt}
        ]

        return await self.chat(messages, **kwargs)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话"""
        return await self._call_chat_completion(messages, **kwargs)

    async def embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )

            return response.data[0].embedding

        except Exception as e:
            self.logger.error(f"OpenAI embedding failed: {str(e)}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "type": "openai",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

    async def close(self):
        """关闭连接"""
        # OpenAI客户端会自动管理连接
        self.logger.info("OpenAI LLM closed")