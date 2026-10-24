"""
FraudLens - Redis Queue Placeholder
Chưa kết nối Redis thực ở giai đoạn Stub (sẽ kích hoạt khi tách Worker độc lập).
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("fraudlens.redis")

class RedisQueuePlaceholder:
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.is_connected = False
        logger.info("Initialized RedisQueuePlaceholder (Stub mode - calls routed synchronously).")

    def push_job(self, queue_name: str, payload: Dict[str, Any]) -> str:
        """Giả lập đẩy job vào Redis Queue (ML Jobs hoặc LLM Jobs)"""
        logger.debug(f"[Stub Redis Queue] Pushed job to '{queue_name}': {payload.get('transaction_id') or payload.get('case_id')}")
        return "mock-job-id-stub"

    def pop_job(self, queue_name: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Giả lập lấy job từ Redis Queue"""
        return None

# Singleton instance for Workflow Module
redis_queue = RedisQueuePlaceholder()
