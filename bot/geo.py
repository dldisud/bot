from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class GeoResult:
    name: str
    latitude: float
    longitude: float
    country: Optional[str]
    admin1: Optional[str]
    timezone: Optional[str]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
def geocode_place(name: str, language: str = "ko") -> GeoResult:
    """Resolve place name to coordinates using Open-Meteo Geocoding API."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": name,
        "count": 1,
        "language": language,
        "format": "json",
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    if not results:
        raise ValueError(f"지오코딩 실패: '{name}'에 대한 결과가 없습니다.")
    r0 = results[0]
    display_name_parts = [
        p
        for p in [r0.get("name"), r0.get("admin1"), r0.get("country")]
        if p
    ]
    display_name = ", ".join(display_name_parts)
    return GeoResult(
        name=display_name,
        latitude=float(r0["latitude"]),
        longitude=float(r0["longitude"]),
        country=r0.get("country"),
        admin1=r0.get("admin1"),
        timezone=r0.get("timezone"),
    )


