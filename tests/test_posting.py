"""Integration tests for the automated multi-platform posting system."""

from typing import Optional, Tuple
import pytest
from fastapi.testclient import TestClient
import httpx

from app.config import Settings
from app.main import app, get_posting_service
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult, PostingRequest
from app.services.posting_service import PostingService

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "endpoints" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["platforms_count"] >= 5
    assert isinstance(data["platforms"], list)


def test_posting_endpoint_default_unconfigured():
    """When no API keys are configured, platforms should report authentication failed gracefully."""
    payload = {
        "message": (
            "Check out our latest business platform and grow your "
            "online visibility. https://example.com"
        )
    }

    response = client.post("/posting", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "success" in data
    assert "results" in data
    assert len(data["results"]) >= 5

    # Verify each platform result conforms to schema
    for res in data["results"]:
        assert "platform" in res
        assert "status" in res
        assert "posted_url" in res
        assert "public_access" in res
        assert "date" in res
        assert "time" in res
        assert "error" in res
        assert res["status"] in ("success", "failed")


def test_posting_endpoint_simulation_mode():
    """In simulation mode, all platforms generate mock successful posts."""
    sim_settings = Settings(simulation_mode=True)
    sim_service = PostingService(settings=sim_settings)

    # Override dependency in FastAPI
    app.dependency_overrides[get_posting_service] = lambda: sim_service

    try:
        payload = {
            "message": (
                "Check out our latest business platform and grow your "
                "online visibility. https://example.com"
            )
        }
        response = client.post("/posting", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["results"]) >= 5

        for res in data["results"]:
            assert res["status"] == "success"
            assert res["posted_url"] is not None
            assert res["posted_url"].startswith("http")
            assert res["error"] is None
            assert res["date"] is not None
            assert res["time"] is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_fault_tolerance_isolated_failure():
    """Ensures that one failing or crashing platform does not prevent other platforms from posting."""

    class WorkingPlatform(BasePlatform):
        @property
        def name(self) -> str:
            return "WorkingPlatform"

        @property
        def default_public_access(self) -> bool:
            return True

        def is_configured(self) -> bool:
            return True

        def configuration_error_message(self) -> str:
            return ""

        async def _publish(
            self, client: httpx.AsyncClient, message: str, cta_url: str
        ) -> Tuple[str, Optional[bool]]:
            return "https://working.com/post/100", True

    class CrashingPlatform(BasePlatform):
        @property
        def name(self) -> str:
            return "CrashingPlatform"

        @property
        def default_public_access(self) -> bool:
            return False

        def is_configured(self) -> bool:
            return True

        def configuration_error_message(self) -> str:
            return ""

        async def _publish(
            self, client: httpx.AsyncClient, message: str, cta_url: str
        ) -> Tuple[str, Optional[bool]]:
            raise RuntimeError("Catastrophic network or database crash!")

    settings = Settings(simulation_mode=False)
    service = PostingService(
        settings=settings,
        platforms=[WorkingPlatform(settings), CrashingPlatform(settings)],
    )

    req = PostingRequest(
        message="Important announcement with CTA link https://example.com"
    )
    result = await service.publish_message(req)

    assert result.success is True
    assert len(result.results) == 2

    working_res = next(r for r in result.results if r.platform == "WorkingPlatform")
    assert working_res.status == "success"
    assert working_res.posted_url == "https://working.com/post/100"
    assert working_res.public_access is True
    assert working_res.error is None

    crashing_res = next(r for r in result.results if r.platform == "CrashingPlatform")
    assert crashing_res.status == "failed"
    assert crashing_res.posted_url is None
    assert "Catastrophic" in crashing_res.error
