from typing import Protocol

from app.schemas.domain.ai import ParseResponse


class AIParser(Protocol):
    """Protocol for AI parsing services."""

    async def parse_offer(self, raw_data: str) -> ParseResponse:
        """
        Parse raw offer data into structured format.

        Args:
            raw_data: Raw text content to parse

        Returns:
            ParseResponse with structured data or error
        """
        ...
