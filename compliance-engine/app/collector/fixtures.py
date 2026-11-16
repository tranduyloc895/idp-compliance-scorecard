"""
Fixture collectors — đọc dữ liệu scanner từ file JSON thay vì Kubernetes API.

Bật bằng COLLECTOR_MODE=fixtures. Dùng cho smoke test trong CI (docker compose,
không có cluster). Mỗi thư mục fixture chứa:

  policyreports.json          List PolicyReport (Kyverno), dạng {"items": [...]}
  clusterpolicyreports.json   (tùy chọn) List ClusterPolicyReport
  vulnerabilityreports.json   List VulnerabilityReport (Trivy Operator)
  kubebench.json              Output `kube-bench run --json`

Logic parse giữ nguyên của collector thật; chỉ thay phần lấy dữ liệu.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.collector.kubebench import KubeBenchCollector
from app.collector.kyverno import KyvernoCollector
from app.collector.trivy import TrivyCollector

logger = logging.getLogger(__name__)


def _load_json(path: Path) -> Any:
    if not path.is_file():
        logger.warning("Fixture file missing: %s", path)
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _items(path: Path, namespace: Optional[str] = None) -> list[dict]:
    data = _load_json(path)
    if data is None:
        return []
    items = data.get("items", []) if isinstance(data, dict) else list(data)
    if namespace:
        items = [i for i in items if i.get("metadata", {}).get("namespace") == namespace]
    return items


class FixtureKyvernoCollector(KyvernoCollector):
    def __init__(self, fixtures_dir: Path) -> None:
        self.k8s_client = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fixtures_dir = fixtures_dir

    async def _get_namespace_reports(self, namespace: str) -> list[dict]:
        return _items(self.fixtures_dir / "policyreports.json", namespace)

    async def _get_all_namespace_reports(self) -> list[dict]:
        return _items(self.fixtures_dir / "policyreports.json")

    async def _get_cluster_reports(self) -> list[dict]:
        path = self.fixtures_dir / "clusterpolicyreports.json"
        return _items(path) if path.is_file() else []


class FixtureTrivyCollector(TrivyCollector):
    def __init__(self, fixtures_dir: Path) -> None:
        self.k8s_client = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fixtures_dir = fixtures_dir

    async def _get_namespace_reports(self, namespace: str) -> list[dict]:
        return _items(self.fixtures_dir / "vulnerabilityreports.json", namespace)

    async def _get_all_reports(self) -> list[dict]:
        return _items(self.fixtures_dir / "vulnerabilityreports.json")


class FixtureKubeBenchCollector(KubeBenchCollector):
    def __init__(self, fixtures_dir: Path) -> None:
        self.k8s_client = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fixtures_dir = fixtures_dir

    async def _get_results_from_configmap(self) -> Optional[str]:
        path = self.fixtures_dir / "kubebench.json"
        if not path.is_file():
            logger.warning("Fixture file missing: %s", path)
            return None
        return path.read_text(encoding="utf-8")
