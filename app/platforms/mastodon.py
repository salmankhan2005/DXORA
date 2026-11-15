"""Mastodon REST API integration for publishing federated public statuses."""

from datetime import datetime
from typing import Optional, Tuple
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class MastodonPlatform(BasePlatform):
    """Integrates with the official Mastodon API v1 (POST /api/v1/statuses).

    Docs: https://docs.joinmastodon.org/methods/statuses/#create
    """

    @property
    def name(self) -> str:
        return "Mastodon"

    @property
    def default_public_access(self) -> bool:
        return True

    def is_configured(self) -> bool:
        return bool(self.settings.mastodon_access_token)

    def configuration_error_message(self) -> str:
        return "Authentication failed: MASTODON_ACCESS_TOKEN must be configured in environment"

    def _simulate_post(self, message: str, cta_url: str) -> PlatformResult:
        now = datetime.now()
        fake_id = int(now.timestamp()) * 100 + 789
        instance = (
            self.settings.mastodon_instance_url.replace("https://", "").replace("http://", "").strip("/")
            if self.settings.mastodon_instance_url
            else "mastodon.social"
        )
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=f"https://{instance}/@dxora_bot/{fake_id}",
            public_access=True,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    async def _publish(
        self, client: httpx.AsyncClient, message: str, cta_url: str
    ) -> Tuple[str, Optional[bool]]:
        instance = (
            self.settings.mastodon_instance_url.replace("https://", "").replace("http://", "").strip("/")
        )
        api_url = f"https://{instance}/api/v1/statuses"

        headers = {
            "Authorization": f"Bearer {self.settings.mastodon_access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "status": message,
            "visibility": "public",
        }

        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        posted_url = data.get("url") or f"https://{instance}/web/statuses/{data.get('id')}"
        return posted_url, True
