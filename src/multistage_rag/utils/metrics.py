import time
from typing import Dict, Any
from collections import defaultdict


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = time.time()

    def record_retrieval(self, latency_ms: float, stage: str, doc_count: int):
        """记录检索指标"""
        self.metrics["retrieval_latency"].append(latency_ms)
        self.metrics["retrieval_stage"].append(stage)
        self.metrics["document_count"].append(doc_count)

    def record_cache_hit(self):
        """记录缓存命中"""
        self.metrics["cache_hits"].append(1)

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.metrics["cache_misses"].append(1)

    def record_error(self):
        """记录错误"""
        self.metrics["errors"].append(1)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {}

        for key, values in self.metrics.items():
            if values:
                if key.endswith("_latency"):
                    stats[f"{key}_avg"] = sum(values) / len(values) if values else 0
                    stats[f"{key}_p95"] = sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0]
                elif key == "cache_hits" or key == "cache_misses":
                    hits = len(self.metrics.get("cache_hits", []))
                    misses = len(self.metrics.get("cache_misses", []))
                    total = hits + misses
                    stats["cache_hit_rate"] = hits / total if total > 0 else 0
                elif key == "errors":
                    stats["error_count"] = len(values)

        stats["uptime"] = time.time() - self.start_time
        return stats