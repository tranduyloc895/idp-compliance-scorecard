"""
BaseCollector — Abstract base class cho tất cả compliance data collectors.

Mỗi collector (Kyverno, Trivy, kube-bench) implement interface này
để ComplianceAggregator có thể orchestrate đồng nhất.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from kubernetes_asyncio.client import ApiClient

from app.models.finding import RawFinding

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Abstract collector interface.

    Subclasses phải implement collect() để trả về list[RawFinding]
    từ nguồn data tương ứng (K8s CRD, ConfigMap, etc.).
    """

    def __init__(self, k8s_client: ApiClient) -> None:
        self.k8s_client = k8s_client
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def collect(self, namespace: Optional[str] = None) -> list[RawFinding]:
        """
        Thu thập raw compliance data.

        Args:
            namespace: Filter theo namespace cụ thể. None = tất cả namespaces.

        Returns:
            list[RawFinding]: Raw findings chưa qua normalizer.
        """
        ...

    async def health_check(self) -> bool:
        """
        Kiểm tra xem collector có thể kết nối với data source không.
        Override trong subclass nếu cần custom logic.
        """
        try:
            await self.collect(namespace="default")
            return True
        except Exception as e:
            self.logger.warning("Health check failed: %s", e)
            return False
