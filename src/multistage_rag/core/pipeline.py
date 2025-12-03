from typing import List, Dict, Any, Optional
import time
from abc import ABC, abstractmethod
from .models import Document, StageMetrics, StageType
from ..utils.logger import get_logger


class BaseStage(ABC):
    """阶段基类"""

    def __init__(self, config: Dict[str, Any], stage_type: StageType):
        self.config = config
        self.stage_type = stage_type
        self.logger = get_logger(f"stage.{stage_type.value}")
        self.enabled = config.get("enabled", True)
        self.name = stage_type.value

    @abstractmethod
    async def execute(self, query: str, documents: List[Document], **kwargs) -> List[Document]:
        pass

    async def run(self, query: str, documents: List[Document], **kwargs) -> StageMetrics:
        start_time = time.time()
        input_count = len(documents)

        if not self.enabled:
            self.logger.info(f"Stage {self.name} disabled")
            return StageMetrics(
                stage_name=self.name,
                latency_ms=0,
                input_count=input_count,
                output_count=input_count,
                success=True
            )

        try:
            self.logger.debug(f"Running {self.name}, input: {input_count}")
            output_documents = await self.execute(query, documents, **kwargs)

            latency_ms = (time.time() - start_time) * 1000
            output_count = len(output_documents)

            self.logger.info(f"{self.name} completed in {latency_ms:.2f}ms")
            return StageMetrics(
                stage_name=self.name,
                latency_ms=latency_ms,
                input_count=input_count,
                output_count=output_count,
                success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.logger.error(f"{self.name} failed: {str(e)}")
            return StageMetrics(
                stage_name=self.name,
                latency_ms=latency_ms,
                input_count=input_count,
                output_count=0,
                success=False,
                error_message=str(e)
            )


class Pipeline:
    """检索管道"""

    def __init__(self, stages: List[BaseStage]):
        self.stages = stages
        self.logger = get_logger("pipeline")

    async def run(self, query: str, initial_docs: List[Document], **kwargs) -> Dict[str, Any]:
        current_docs = initial_docs
        all_metrics = []
        final_stage = StageType.RECALL

        for stage in self.stages:
            if not stage.enabled:
                continue

            metrics = await stage.run(query, current_docs, **kwargs)
            all_metrics.append(metrics)

            if metrics.success:
                current_docs = await stage.execute(query, current_docs, **kwargs)
                final_stage = stage.stage_type
            else:
                self.logger.warning(f"Stage {stage.name} failed, continuing")
                final_stage = StageType.FALLBACK

        return {
            "documents": current_docs,
            "stage": final_stage,
            "metrics": all_metrics
        }