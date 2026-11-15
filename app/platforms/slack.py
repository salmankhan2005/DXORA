"""Slack Webhook / Web API integration for broadcasting messages to workspace channels."""

from datetime import datetime
from typing import Optional, Tuple
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class SlackPlatform(BasePlatform):
    """Integrates with the official Slack Webhook and Web API.

    Docs: https://api.slack.com/messaging/webhooks
    """

    @property
    def name(self) -> str:
        return "Slack"

    @property
    def default_public_access(self) -> bool:
        return False

    def is_configured(self) -> bool:
        return bool(
            self.settings.slack_webhook_url
            or (self.settings.slack_bot_token and self.settings.slack_channel)
        )

    def configuration_error_message(self) -> str:
        return (
            "Authentication failed: SLACK_WEBHOOK_URL or "
            "(SLACK_BOT_TOKEN and SLACK_CHANNEL) must be configured in environment"
        )

    def _simulate_post(self, message: str, cta_url: str) -> PlatformResult:
        now = datetime.now()
        fake_ts = int(now.timestamp())
        channel_id = self.settings.slack_channel or "C07DXORA01"
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=f"https://slack.com/archives/{channel_id}/p{fake_ts}000100",
            public_access=False,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    async def _publish(
        self, client: httpx.AsyncClient, message: str, cta_url: str
    ) -> Tuple[str, Optional[bool]]:
        # Case 1: Webhook integration
        if self.settings.slack_webhook_url:
            webhook_url = self.settings.slack_webhook_url.strip()
            payload = {"text": message}

            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()

            # Slack webhooks return plain text 'ok'
            if response.text.strip().lower() != "ok":
                raise ValueError(f"Slack webhook error: {response.text}")

            channel_ref = self.settings.slack_channel or "webhook-channel"
            posted_url = f"https://slack.com/archives/{channel_ref}"
            return posted_url, False

        # Case 2: Bot token and channel
        token = self.settings.slack_bot_token
        channel = self.settings.slack_channel
        post_url = "https://slack.com/api/chat.postMessage"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "channel": channel,
            "text": message,
        }

        response = await client.post(post_url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        if not data.get("ok"):
            raise ValueError(f"Slack API error: {data.get('error', 'unknown error')}")

        ts = data.get("ts", "")
        # Query permalink if available
        permalink_url = f"https://slack.com/api/chat.getPermalink?channel={channel}&message_ts={ts}"
        try:
            p_resp = await client.get(permalink_url, headers=headers)
            p_data = p_resp.json()
            if p_data.get("ok") and p_data.get("permalink"):
                return p_data["permalink"], False
        except Exception:
            pass

        ts_clean = ts.replace(".", "")
        return f"https://slack.com/archives/{channel}/p{ts_clean}", False
