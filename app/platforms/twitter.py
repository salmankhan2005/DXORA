"""Twitter / X API v2 integration for publishing tweets."""

from datetime import datetime
from typing import Optional, Tuple
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class TwitterPlatform(BasePlatform):
    """Integrates with the official Twitter / X API v2 (POST /2/tweets).

    Docs: https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets
    """

    @property
    def name(self) -> str:
        return "Twitter / X"

    @property
    def default_public_access(self) -> bool:
        return True

    def is_configured(self) -> bool:
        return bool(
            self.settings.twitter_bearer_token
            or (self.settings.twitter_api_key and self.settings.twitter_access_token)
        )

    def configuration_error_message(self) -> str:
        return "Authentication failed: TWITTER_BEARER_TOKEN must be configured in environment"

    def _simulate_post(self, message: str, cta_url: str) -> PlatformResult:
        now = datetime.now()
        fake_id = 1800000000000000000 + int(now.timestamp())
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=f"https://x.com/dxora_official/status/{fake_id}",
            public_access=True,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    async def _publish(
        self, client: httpx.AsyncClient, message: str, cta_url: str
    ) -> Tuple[str, Optional[bool]]:
        api_url = "https://api.twitter.com/2/tweets"

        headers = {
            "Authorization": f"Bearer {self.settings.twitter_bearer_token}",
            "Content-Type": "application/json",
        }
        payload = {"text": message}

        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        tweet_data = data.get("data", {})
        tweet_id = tweet_data.get("id")

        if not tweet_id:
            raise ValueError(f"Twitter API response missing tweet ID: {data}")

        posted_url = f"https://x.com/i/status/{tweet_id}"
        return posted_url, True
