from abc import ABC, abstractmethod

from vibehouse.common.logging import get_logger


class BaseIntegration(ABC):
    """Base class for all external service integrations.

    Provides common logging and a required health_check interface so the
    application can verify connectivity at startup or on-demand.
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"integrations.{name}")

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True when the integration is reachable and functional."""
        ...
