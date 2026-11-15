"""Platform registry and discovery module."""

from typing import List, Type
from app.config import Settings
from app.platforms.base import BasePlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.twitter import TwitterPlatform
from app.platforms.slack import SlackPlatform

ALL_PLATFORMS: List[Type[BasePlatform]] = [
    TelegramPlatform,
    DiscordPlatform,
    MastodonPlatform,
    TwitterPlatform,
    SlackPlatform,
]


def get_all_platforms(settings: Settings) -> List[BasePlatform]:
    """Instantiates and returns all supported platform adapters with the given settings."""
    return [platform_cls(settings) for platform_cls in ALL_PLATFORMS]


__all__ = [
    "BasePlatform",
    "TelegramPlatform",
    "DiscordPlatform",
    "MastodonPlatform",
    "TwitterPlatform",
    "SlackPlatform",
    "ALL_PLATFORMS",
    "get_all_platforms",
]
