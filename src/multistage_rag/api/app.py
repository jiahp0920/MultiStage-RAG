from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
import os

from ..core.models import RetrievalRequest, RetrievalResponse, HealthResponse
from ..core.retriever import MultiStageRetriever
from ..config.config_manager import ConfigManager
from ..utils.logger import get_logger
import yaml


class MultiStageRAGAPI:
    """API服务"""

    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_logger(__name__)

        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()

        # 创建FastAPI应用
        self.app = FastAPI(
            title="MultiStage-RAG API",
            description="多阶段检索增强生成API",
            version=self.config.get("app", {}).get("version", "1.0.0")
        )

        # 配置CORS
        self._setup_cors()

        # 初始化检索器
        self.retriever = None

        # 设置路由
        self._setup_routes()
        self._setup_lifespan()

        self.logger.info("API initialized")

    def _setup_cors(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        @self.app.get("/health", response_model=HealthResponse)
        async def health():
            from datetime import datetime
            return HealthResponse(
                status="healthy" if self.retriever else "initializing",
                version="1.0.0",
                components={
                    "retriever": "ready" if self.retriever else "initializing",
                    "api": "ready"
                },
                timestamp=datetime.now()
            )

        @self.app.post("/api/v1/retrieve", response_model=RetrievalResponse)
        async def retrieve(request: RetrievalRequest):
            if not self.retriever:
                raise HTTPException(503, "Service initializing")

            try:
                result = await self.retriever.retrieve(
                    query=request.query,
                    top_k=request.top_k,
                    filters=request.filters,
                    use_cache=request.use_cache,
                    enable_stages=request.enable_stages
                )

                return RetrievalResponse(
                    success=True,
                    data=result,
                    request_id=f"req_{int(time.time() * 1000)}"
                )
            except Exception as e:
                return RetrievalResponse(
                    success=False,
                    error=str(e),
                    request_id=f"req_{int(time.time() * 1000)}"
                )

    def _setup_lifespan(self):
        @self.app.on_event("startup")
        async def startup():
            self.logger.info("Starting MultiStageRAGAPI...")
            self.retriever = MultiStageRetriever(self.config)

        @self.app.on_event("shutdown")
        async def shutdown():
            if self.retriever:
                await self.retriever.close()

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        uvicorn.run(self.app, host=host, port=port)


def main():
    """主入口函数"""
    config_path = os.getenv("CONFIG_PATH", "./configs/default_config.yaml")
    api = MultiStageRAGAPI(config_path)
    api.run()


if __name__ == "__main__":
    main()