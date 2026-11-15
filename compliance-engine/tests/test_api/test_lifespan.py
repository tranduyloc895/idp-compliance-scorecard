"""Lifespan khởi động được (không cần PostgreSQL/Redis thật).

Hồi quy: `import app.models` trong lifespan từng ghi đè tham số `app`, làm
`app.state.cache = ...` lỗi AttributeError và API không start (bắt được ở engine-smoke CI).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from app import main
from app.config import settings


class _FakeConn:
    async def run_sync(self, fn):
        return None


class _FakeEngine:
    @asynccontextmanager
    async def begin(self):
        yield _FakeConn()

    async def dispose(self):
        return None


async def test_lifespan_starts_and_sets_state(monkeypatch):
    monkeypatch.setattr(settings, "COLLECTOR_MODE", "fixtures")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    with (
        patch("app.database.init_db"),
        patch("app.database.get_engine", return_value=_FakeEngine()),
        patch("app.cache.ComplianceCache.connect", new=AsyncMock()),
        patch("app.cache.ComplianceCache.close", new=AsyncMock()),
    ):
        async with main.lifespan(main.app):
            assert main.app.state.cache is not None
            assert main.app.state.k8s_client is None  # fixture mode
            assert main.app.state.ai_recommender is None
