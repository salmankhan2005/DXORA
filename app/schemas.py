"""Pydantic data models and validation logic for multi-platform posting."""

import re
from typing import List, Literal, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Regular expression to extract URLs with schemes or www prefix
URL_PATTERN = re.compile(
    r'(?:[a-zA-Z][a-zA-Z0-9+.-]*://|www\.)[^\s<>\"\'`]+',
    re.IGNORECASE,
)

# Hostname validation (RFC 1123 compliant domain names, localhost, or IPv4)
DOMAIN_PATTERN = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    r'|^localhost$'
    r'|^(?:\d{1,3}\.){3}\d{1,3}$'
)


class PostingRequest(BaseModel):
    """Incoming request payload for multi-platform posting.

    Validates:
    1. Total message length must not exceed 200 characters.
    2. Message must contain exactly one Call-To-Action (CTA) link.
    3. The CTA link must be a valid HTTP or HTTPS URL with a valid domain.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "message": (
                    "Check out our latest business platform and grow your "
                    "online visibility. https://example.com"
                )
            }
        },
    )

    message: str = Field(
        ...,
        description="The content to publish. Must be under 200 characters and contain exactly one CTA URL.",
        examples=[
            "Check out our latest business platform and grow your online visibility. https://example.com"
        ],
    )

    @field_validator("message")
    @classmethod
    def validate_message_and_cta(cls, value: str) -> str:
        """Enforces character limit, CTA presence, uniqueness, and URL validity."""
        if not value or not value.strip():
            raise ValueError("Message cannot be empty.")

        cleaned_text = value.strip()

        # 1. Message character limit check (<= 200 characters)
        if len(cleaned_text) > 200:
            raise ValueError(
                f"Message length ({len(cleaned_text)} characters) exceeds the maximum limit of 200 characters."
            )

        # 2. Extract potential CTA links and strip trailing sentence punctuation
        raw_matches = URL_PATTERN.findall(cleaned_text)
        cleaned_urls = []
        for raw in raw_matches:
            sanitized = re.sub(r'[\.,!?;\)\]>]+$', '', raw)
            if sanitized:
                cleaned_urls.append(sanitized)

        # Exactly one CTA link must be included
        if len(cleaned_urls) == 0:
            raise ValueError("Message must contain exactly one CTA link, but none was found.")
        if len(cleaned_urls) > 1:
            raise ValueError(
                f"Message must contain exactly one CTA link, but found {len(cleaned_urls)} links: "
                f"{', '.join(cleaned_urls)}."
            )

        # 3. URL format and protocol validation
        url = cleaned_urls[0]
        if url.startswith("www."):
            url = f"https://{url}"

        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"The CTA link '{url}' must use HTTP or HTTPS protocol (found '{parsed.scheme}')."
            )

        netloc = parsed.netloc
        if "@" in netloc:
            netloc = netloc.split("@", 1)[1]
        if ":" in netloc:
            netloc = netloc.split(":", 1)[0]

        if not netloc or not DOMAIN_PATTERN.match(netloc):
            raise ValueError(
                f"The CTA link '{url}' has an invalid domain or hostname '{netloc}'."
            )

        return cleaned_text

    @property
    def cta_url(self) -> str:
        """Extracts the validated single CTA link from the message."""
        raw_matches = URL_PATTERN.findall(self.message)
        for raw in raw_matches:
            sanitized = re.sub(r'[\.,!?;\)\]>]+$', '', raw)
            if sanitized:
                if sanitized.startswith("www."):
                    return f"https://{sanitized}"
                return sanitized
        return ""


class PlatformResult(BaseModel):
    """Posting result for an individual platform."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "Telegram",
                "status": "success",
                "posted_url": "https://t.me/my_channel/123",
                "public_access": True,
                "date": "2026-11-15",
                "time": "10:30:00",
                "error": None,
            }
        }
    )

    platform: str = Field(..., description="Platform name")
    status: Literal["success", "failed"] = Field(..., description="Posting status: success or failed")
    posted_url: Optional[str] = Field(None, description="Published content URL, or null if failed")
    public_access: bool = Field(..., description="Whether content is publicly accessible")
    date: Optional[str] = Field(None, description="Posting date in YYYY-MM-DD format")
    time: Optional[str] = Field(None, description="Posting time in HH:MM:SS format")
    error: Optional[str] = Field(None, description="Error details, if applicable")


class PostingResponse(BaseModel):
    """Aggregate response returned by the multi-platform posting endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "results": [
                    {
                        "platform": "Telegram",
                        "status": "success",
                        "posted_url": "https://t.me/dxora_channel/42",
                        "public_access": True,
                        "date": "2026-11-15",
                        "time": "10:30:00",
                        "error": None,
                    },
                    {
                        "platform": "Discord",
                        "status": "failed",
                        "posted_url": None,
                        "public_access": False,
                        "date": None,
                        "time": None,
                        "error": "Authentication failed: DISCORD_WEBHOOK_URL not configured",
                    },
                ],
            }
        }
    )

    success: bool = Field(
        ...,
        description="Indicates whether the multi-platform posting operation completed and at least one platform succeeded",
    )
    results: List[PlatformResult] = Field(
        ...,
        description="Individual posting execution results for each integrated platform",
    )


class ValidationErrorDetail(BaseModel):
    """Details of a single validation failure."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Standardized error response payload for client errors."""

    success: bool = False
    error: str
    details: List[ValidationErrorDetail] = []
