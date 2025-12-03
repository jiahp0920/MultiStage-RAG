from typing import List, Dict, Any, Optional
import asyncio
import time
import hashlib
import json
from .models import Document, RetrievalResult, StageType
from ..stages import RecallStage, PreRankStage, ReRankStage
from ..stages.base import Pipeline
from ..utils.logger import get_logger
from ..components.cache.factory import CacheFactory


class MultiStageRetriever:
    """多阶段检索器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(__name__)

        # 初始化阶段
        self.stages = self._init_stages(config)
        self.pipeline = Pipeline(self.stages)

        # 初始化缓存
        cache_config = config.get("cache", {})
        self.cache = CacheFactory.create(cache_config)

        # 初始化熔断器
        self.circuit_breaker = self._init_circuit_breaker(config)

        self.logger.info("MultiStageRetriever initialized")

    def _init_stages(self, config: Dict[str, Any]) -> List:
        stages = []
        retrieval_config = config.get("retrieval", {})
        enabled_stages = retrieval_config.get("enabled_stages", {})
        stage_params = retrieval_config.get("stage_params", {})

        # 召回阶段
        if enabled_stages.get("recall", True):
            recall_config = {
                **stage_params.get("recall", {}),
                "vector_store": config.get("vector_store", {}),
                "enabled": True
            }
            stages.append(RecallStage(recall_config))

        # 粗排阶段
        if enabled_stages.get("pre_rank", True):
            pre_rank_config = {
                **stage_params.get("pre_rank", {}),
                "rule_engine": config.get("rule_engine", {}),
                "enabled": True
            }
            stages.append(PreRankStage(pre_rank_config))

        # 精排阶段
        if enabled_stages.get("re_rank", True):
            re_rank_config = {
                **stage_params.get("re_rank", {}),
                "reranker": config.get("reranker", {}),
                "cache": config.get("cache", {}),
                "enabled": True
            }
            stages.append(ReRankStage(re_rank_config))

        return stages

    def _init_circuit_breaker(self, config: Dict[str, Any]):
        """初始化熔断器"""
        fallback_config = config.get("fallback", {})
        cb_config = fallback_config.get("circuit_breaker", {})

        class CircuitBreaker:
            def __init__(self, config):
                self.failure_threshold = config.get("failure_threshold", 5)
                self.recovery_timeout = config.get("recovery_timeout", 30)
                self.failure_count = 0
                self.last_failure_time = 0
                self.state = "CLOSED"

            def record_failure(self):
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"

            def record_success(self):
                self.failure_count = 0
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"

            def allow_request(self) -> bool:
                if self.state == "CLOSED":
                    return True
                elif self.state == "OPEN":
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        self.state = "HALF_OPEN"
                        return True
                    return False
                return True

        return CircuitBreaker(cb_config)

    def _generate_cache_key(self, query: str, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [
            "retrieve",
            query.strip().lower(),
            str(kwargs.get("top_k", "")),
            json.dumps(kwargs.get("filters", {}), sort_keys=True),
            json.dumps(kwargs.get("enable_stages", {}), sort_keys=True),
        ]
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def retrieve(self, query: str, top_k: Optional[int] = None,
                       filters: Optional[Dict] = None, use_cache: bool = True,
                       enable_stages: Optional[Dict[str, bool]] = None) -> RetrievalResult:
        start_time = time.time()

        # 检查熔断器
        if not self.circuit_breaker.allow_request():
            self.logger.warning("Circuit breaker OPEN")
            return await self._fallback_retrieve(query, top_k, filters, "circuit_breaker")

        # 检查缓存
        cache_key = None
        if use_cache:
            cache_key = self._generate_cache_key(query, top_k=top_k,
                                                 filters=filters, enable_stages=enable_stages)
            cached = await self.cache.get(cache_key)
            if cached:
                self.logger.info(f"Cache hit: {cache_key[:12]}...")
                result = RetrievalResult.from_dict(json.loads(cached))
                result.latency_ms = (time.time() - start_time) * 1000
                result.cache_hit = True
                return result

        # 应用阶段覆盖
        if enable_stages:
            for stage in self.stages:
                stage_name = stage.stage_type.value
                if stage_name in enable_stages:
                    stage.enabled = enable_stages[stage_name]

        # 运行管道
        try:
            kwargs = {"filters": filters, "use_cache": use_cache}
            pipeline_result = await self.pipeline.run(query, [], **kwargs)

            documents = pipeline_result["documents"]
            if top_k and top_k > 0:
                documents = documents[:top_k]

            # 缓存结果
            if use_cache and cache_key and documents:
                result = RetrievalResult(
                    query=query,
                    documents=documents,
                    stage=pipeline_result["stage"],
                    latency_ms=0,
                    cache_hit=False
                )
                asyncio.create_task(
                    self.cache.set(cache_key, json.dumps(result.to_dict()), ttl=300)
                )

            latency_ms = (time.time() - start_time) * 1000
            self.circuit_breaker.record_success()

            return RetrievalResult(
                query=query,
                documents=documents,
                stage=pipeline_result["stage"],
                latency_ms=latency_ms,
                cache_hit=False,
                metrics={"stage_metrics": [m.__dict__ for m in pipeline_result["metrics"]]}
            )

        except Exception as e:
            self.logger.error(f"Retrieval failed: {str(e)}")
            self.circuit_breaker.record_failure()
            return await self._fallback_retrieve(query, top_k, filters, str(e))

    async def _fallback_retrieve(self, query: str, top_k: Optional[int],
                                 filters: Optional[Dict], error_reason: str) -> RetrievalResult:
        """降级检索"""
        start_time = time.time()

        try:
            # 只使用召回阶段
            recall_stage = None
            for stage in self.stages:
                if isinstance(stage, RecallStage):
                    recall_stage = stage
                    break

            if not recall_stage:
                raise ValueError("Recall stage not found")

            # 执行召回
            documents = await recall_stage.execute(query, [], filters=filters)

            if top_k and top_k > 0:
                documents = documents[:top_k]

            latency_ms = (time.time() - start_time) * 1000

            return RetrievalResult(
                query=query,
                documents=documents,
                stage=StageType.FALLBACK,
                latency_ms=latency_ms,
                fallback_triggered=True,
                metrics={"error": error_reason, "fallback": True}
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return RetrievalResult(
                query=query,
                documents=[],
                stage=StageType.FALLBACK,
                latency_ms=latency_ms,
                fallback_triggered=True,
                metrics={"error": f"{error_reason}, fallback_error: {str(e)}"}
            )

    async def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档"""
        for stage in self.stages:
            if hasattr(stage, 'vector_store'):
                if hasattr(stage.vector_store, 'add_documents'):
                    return await asyncio.get_event_loop().run_in_executor(
                        None, stage.vector_store.add_documents, documents
                    )
        raise ValueError("No vector store available")

    async def close(self):
        """关闭资源"""
        if hasattr(self.cache, 'close'):
            await self.cache.close()