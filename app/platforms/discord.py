"""Discord Webhook API integration for publishing messages to server channels."""

from datetime import datetime
from typing import Optional, Tuple
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class DiscordPlatform(BasePlatform):
    """Integrates with the official Discord Webhook API.

    Docs: https://discord.com/developers/docs/resources/webhook#execute-webhook
    """

    @property
    def name(self) -> str:
        return "Discord"

    @property
    def default_public_access(self) -> bool:
        return self.settings.discord_public_access

    def is_configured(self) -> bool:
        return bool(self.settings.discord_webhook_url)

    def configuration_error_message(self) -> str:
        return "Authentication failed: DISCORD_WEBHOOK_URL must be configured in environment"

    def _simulate_post(self, message: str, cta_url: str) -> PlatformResult:
        now = datetime.now()
        fake_id = int(now.timestamp()) * 1000 + 456
        guild_id = self.settings.discord_guild_id or "128471928374829102"
        channel_id = self.settings.discord_channel_id or "987654321098765432"
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=f"https://discord.com/channels/{guild_id}/{channel_id}/{fake_id}",
            public_access=self.default_public_access,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    async def _publish(
        self, client: httpx.AsyncClient, message: str, cta_url: str
    ) -> Tuple[str, Optional[bool]]:
        base_url = self.settings.discord_webhook_url.strip()
        separator = "&" if "?" in base_url else "?"
        url_with_wait = f"{base_url}{separator}wait=true"

        payload = {"content": message}

        response = await client.post(url_with_wait, json=payload)
        response.raise_for_status()

        data = response.json()
        message_id = data.get("id")
        raw_channel = str(data.get("channel_id") or self.settings.discord_channel_id or "0").strip().rstrip("/")
        channel_id = raw_channel.split("/")[-1] if "/" in raw_channel else raw_channel
        raw_guild = str(data.get("guild_id") or self.settings.discord_guild_id or "@me").strip().rstrip("/")
        guild_id = raw_guild.split("/")[-1] if "/" in raw_guild else raw_guild

        posted_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        return posted_url, self.default_public_access
