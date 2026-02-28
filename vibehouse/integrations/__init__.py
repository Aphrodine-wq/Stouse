"""VibeHouse mock integration clients.

All clients implement ``BaseIntegration`` and return realistic fake data
without making any real external API calls.
"""

from vibehouse.integrations.ai_client import AIClient
from vibehouse.integrations.base import BaseIntegration
from vibehouse.integrations.maps import MapsClient
from vibehouse.integrations.sendgrid import EmailClient
from vibehouse.integrations.storage import StorageClient
from vibehouse.integrations.trello import TrelloClient
from vibehouse.integrations.twilio_client import SMSClient

__all__ = [
    "AIClient",
    "BaseIntegration",
    "EmailClient",
    "MapsClient",
    "SMSClient",
    "StorageClient",
    "TrelloClient",
]
