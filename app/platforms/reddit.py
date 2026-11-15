"""Reddit OAuth2 API integration for submitting text/link posts to subreddits."""

from datetime import datetime
from typing import Optional, Tuple
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class RedditPlatform(BasePlatform):
    """Integrates with the official Reddit API (OAuth2 submit endpoint).

    Docs: https://www.reddit.com/dev/api/#POST_api_submit
    """

    @property
    def name(self) -> str:
        return "Reddit"

    @property
    def default_public_access(self) -> bool:
        return True

    def is_configured(self) -> bool:
        return bool(
            self.settings.reddit_client_id
            and self.settings.reddit_client_secret
            and self.settings.reddit_username
            and self.settings.reddit_password
        )

    def configuration_error_message(self) -> str:
        return (
            "Authentication failed: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
            "REDDIT_USERNAME, and REDDIT_PASSWORD must be configured in environment"
        )

    def _simulate_post(self, message: str, cta_url: str) -> PlatformResult:
        now = datetime.now()
        fake_id = hex(int(now.timestamp()))[2:]
        subreddit = self.settings.reddit_subreddit or "test"
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=f"https://www.reddit.com/r/{subreddit}/comments/{fake_id}/dxora_announcement/",
            public_access=True,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    async def _publish(
        self, client: httpx.AsyncClient, message: str, cta_url: str
    ) -> Tuple[str, Optional[bool]]:
        # 1. Obtain Reddit OAuth Access Token
        token_url = "https://www.reddit.com/api/v1/access_token"
        auth = (self.settings.reddit_client_id, self.settings.reddit_client_secret)
        auth_data = {
            "grant_type": "password",
            "username": self.settings.reddit_username,
            "password": self.settings.reddit_password,
        }
        headers = {"User-Agent": self.settings.reddit_user_agent}

        token_resp = await client.post(token_url, data=auth_data, auth=auth, headers=headers)
        token_resp.raise_for_status()
        token_json = token_resp.json()
        access_token = token_json.get("access_token")

        if not access_token:
            raise ValueError(f"Failed to obtain Reddit access token: {token_json}")

        # 2. Submit post to subreddit
        submit_url = "https://oauth.reddit.com/api/submit"
        oauth_headers = {
            "Authorization": f"bearer {access_token}",
            "User-Agent": self.settings.reddit_user_agent,
        }

        # Derive short title from message
        title = message[:60].strip() + ("..." if len(message) > 60 else "")

        submit_data = {
            "sr": self.settings.reddit_subreddit,
            "kind": "self",
            "title": title,
            "text": message,
            "api_type": "json",
        }

        submit_resp = await client.post(submit_url, data=submit_data, headers=oauth_headers)
        submit_resp.raise_for_status()

        result = submit_resp.json()
        json_body = result.get("json", {})
        errors = json_body.get("errors", [])
        if errors:
            raise ValueError(f"Reddit API rejected post: {errors}")

        post_data = json_body.get("data", {})
        posted_url = post_data.get("url")

        if not posted_url:
            post_id = post_data.get("id") or post_data.get("name", "").replace("t3_", "")
            posted_url = f"https://www.reddit.com/r/{self.settings.reddit_subreddit}/comments/{post_id}/"

        return posted_url, True
