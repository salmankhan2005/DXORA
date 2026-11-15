"""Abstract base class and contract for all third-party platform integrations."""

from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Optional, Tuple
import httpx

from app.config import Settings
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class BasePlatform(ABC):
    """Abstract Base Class for third-party publishing platforms.

    Encapsulates lifecycle, credential verification, execution timing,
    simulation mode, and standardized error handling.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    @abstractmethod
    def name(self) -> str:
        """The display name of the platform."""
        pass

    @property
    @abstractmethod
    def default_public_access(self) -> bool:
        """Default public visibility flag for published content on this platform."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Determines whether the necessary API credentials are present in settings."""
        pass

    @abstractmethod
    def configuration_error_message(self) -> str:
        """Descriptive error message returned when credentials are missing."""
        pass

    @abstractmethod
    async def _publish(
        self, client: httpx.AsyncClient, message: str, cta_url: str
    ) -> Tuple[str, Optional[bool]]:
        """Executes the platform-specific HTTP request to publish the message.

        Returns:
            Tuple[str, Optional[bool]]: (posted_url, public_access override if applicable)
        """
        pass

    def _simulate_post(self, message: str, cta_url: str) -> PlatformResult:
        """Generates a realistic simulated post result for testing/offline evaluation."""
        now = datetime.now()
        fake_id = int(now.timestamp()) % 1000000 + 100000
        simulated_url = f"https://example.com/{self.name.lower().replace(' ', '')}/post/{fake_id}"
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=simulated_url,
            public_access=self.default_public_access,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    async def post(self, message: str, cta_url: str) -> PlatformResult:
        """Publishes the message to the platform with robust error handling and isolation.

        Ensures failure on one platform never halts or affects other platform executions.
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # 1. Check configuration
        if not self.is_configured():
            if self.settings.simulation_mode:
                logger.info(
                    "[%s] Operating in SIMULATION_MODE; generating simulated success response.",
                    self.name,
                )
                return self._simulate_post(message, cta_url)

            logger.warning("[%s] Missing configuration / credentials.", self.name)
            return PlatformResult(
                platform=self.name,
                status="failed",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=self.configuration_error_message(),
            )

        # 2. Execute live HTTP publishing
        try:
            timeout = httpx.Timeout(self.settings.request_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                posted_url, custom_public = await self._publish(client, message, cta_url)
                public_access = (
                    custom_public if custom_public is not None else self.default_public_access
                )

                logger.info(
                    "[%s] Successfully published content: %s", self.name, posted_url
                )
                return PlatformResult(
                    platform=self.name,
                    status="success",
                    posted_url=posted_url,
                    public_access=public_access,
                    date=date_str,
                    time=time_str,
                    error=None,
                )

        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error("[%s] API responded with error: %s", self.name, error_detail)
            return PlatformResult(
                platform=self.name,
                status="failed",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=error_detail,
            )

        except httpx.TimeoutException:
            logger.error("[%s] Request timed out.", self.name)
            return PlatformResult(
                platform=self.name,
                status="failed",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Connection timed out after {self.settings.request_timeout_seconds}s",
            )

        except httpx.RequestError as e:
            logger.error("[%s] Network connection error: %s", self.name, str(e))
            return PlatformResult(
                platform=self.name,
                status="failed",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Network error: {str(e)}",
            )

        except Exception as e:
            logger.exception("[%s] Unexpected exception during posting: %s", self.name, str(e))
            return PlatformResult(
                platform=self.name,
                status="failed",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Internal error: {str(e)}",
            )
