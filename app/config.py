from dataclasses import dataclass
from os import environ
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass(frozen=True, slots=True)
class Settings:
    obscura_cdp_url: str
    page_navigation_timeout_ms: float = 30_000


def load_settings() -> Settings:
    """Load and validate application settings from environment variables."""
    cdp_url = environ.get("OBSCURA_CDP_URL")
    if not cdp_url:
        raise ValueError("OBSCURA_CDP_URL must be configured")

    parsed_url = urlparse(cdp_url)
    if parsed_url.scheme not in {"http", "https", "ws", "wss"} or not parsed_url.netloc:
        raise ValueError("OBSCURA_CDP_URL must be a valid CDP URL")

    return Settings(obscura_cdp_url=cdp_url)
