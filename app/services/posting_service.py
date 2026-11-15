"""Posting orchestration service for executing concurrent multi-platform distribution."""

import asyncio
import logging
from typing import List, Optional

from app.config import Settings, get_settings
from app.platforms import get_all_platforms
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult, PostingRequest, PostingResponse

logger = logging.getLogger(__name__)


class PostingService:
    """Orchestrates multi-platform posting operations with full concurrency and isolation."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        platforms: Optional[List[BasePlatform]] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.platforms = platforms if platforms is not None else get_all_platforms(self.settings)

    async def publish_message(self, request: PostingRequest) -> PostingResponse:
        """Publishes the validated message concurrently across all integrated platforms.

        Guarantees fault-isolation: a network or authentication failure on one platform
        does not prevent or delay execution on the remaining platforms.
        """
        message = request.message
        cta_url = request.cta_url

        logger.info(
            "Initiating multi-platform distribution across %d platforms. Message length: %d chars.",
            len(self.platforms),
            len(message),
        )

        # Create asynchronous tasks for all platforms
        tasks = [platform.post(message, cta_url) for platform in self.platforms]

        # Execute concurrently with return_exceptions=True
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[PlatformResult] = []
        for platform, res in zip(self.platforms, raw_results):
            if isinstance(res, Exception):
                logger.error(
                    "[%s] Unhandled exception in platform task: %s", platform.name, str(res)
                )
                results.append(
                    PlatformResult(
                        platform=platform.name,
                        status="failed",
                        posted_url=None,
                        public_access=False,
                        date=None,
                        time=None,
                        error=f"Task execution failed: {str(res)}",
                    )
                )
            elif isinstance(res, PlatformResult):
                results.append(res)
            else:
                logger.error("[%s] Unexpected task output type: %s", platform.name, type(res))
                results.append(
                    PlatformResult(
                        platform=platform.name,
                        status="failed",
                        posted_url=None,
                        public_access=False,
                        date=None,
                        time=None,
                        error="Unknown platform execution error",
                    )
                )

        # Overall success is True if at least one platform successfully published
        any_success = any(r.status == "success" for r in results)

        success_count = sum(1 for r in results if r.status == "success")
        failure_count = len(results) - success_count
        logger.info(
            "Multi-platform posting finished. Succeeded: %d, Failed: %d",
            success_count,
            failure_count,
        )

        return PostingResponse(success=any_success, results=results)
