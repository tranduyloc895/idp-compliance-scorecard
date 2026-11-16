"""Kiểm tra khởi tạo Kubernetes client trong lifespan."""

from __future__ import annotations

from unittest.mock import patch

from app import main
from app.config import settings


async def test_incluster_config_is_called_synchronously(monkeypatch):
    """load_incluster_config() là hàm sync; init không được trả None khi nó thành công."""
    monkeypatch.setattr(settings, "K8S_IN_CLUSTER", True)
    monkeypatch.setattr(settings, "COLLECTOR_MODE", "kubernetes")

    with patch("kubernetes_asyncio.config.load_incluster_config", return_value=None) as loader:
        client = await main._init_k8s_client()

    loader.assert_called_once()
    assert client is not None
    await client.close()


async def test_fixture_mode_skips_kubernetes(monkeypatch):
    monkeypatch.setattr(settings, "COLLECTOR_MODE", "fixtures")
    assert await main._init_k8s_client() is None
