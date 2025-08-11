from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Settings:
    location_name: str
    language: str
    timezone: str
    post_to_twitter: bool
    warming_since_1850_c: float
    lia_extra_cooling_c: float
    twitter_api_key: Optional[str]
    twitter_api_secret: Optional[str]
    twitter_access_token: Optional[str]
    twitter_access_token_secret: Optional[str]
    twitter_bearer_token: Optional[str]
    # Joseon options
    joseon_path: Optional[str]
    joseon_mode: str
    joseon_loc: Optional[str]
    joseon_tol: int


def _get_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    value_lower = value.strip().lower()
    return value_lower in {"1", "true", "yes", "y", "on"}


def _get_float(value: Optional[str], default: float) -> float:
    try:
        return float(value) if value is not None else default
    except Exception:
        return default


def load_settings() -> Settings:
    load_dotenv(override=False)

    return Settings(
        location_name=os.getenv("LOCATION_NAME", "Seoul"),
        language=os.getenv("LANGUAGE", "ko"),
        timezone=os.getenv("TIMEZONE", "Asia/Seoul"),
        post_to_twitter=_get_bool(os.getenv("POST_TO_TWITTER"), default=False),
        warming_since_1850_c=_get_float(os.getenv("WARMING_SINCE_1850_C"), 1.2),
        lia_extra_cooling_c=_get_float(os.getenv("LIA_EXTRA_COOLING_C"), 0.4),
        twitter_api_key=os.getenv("TWITTER_API_KEY"),
        twitter_api_secret=os.getenv("TWITTER_API_SECRET"),
        twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        twitter_access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        joseon_path=os.getenv("JOSEON_PATH"),
        joseon_mode=os.getenv("JOSEON_MODE", "exact"),
        joseon_loc=os.getenv("JOSEON_LOC"),
        joseon_tol=int(os.getenv("JOSEON_TOL", "0") or 0),
    )


