from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class TodayDaily:
    date: date
    tmin_c: Optional[float]
    tmax_c: Optional[float]

    @property
    def tmean_c(self) -> Optional[float]:
        if self.tmin_c is None or self.tmax_c is None:
            return None
        return (self.tmin_c + self.tmax_c) / 2.0


@dataclass
class CurrentWeather:
    time_iso: Optional[str]
    temperature_c: Optional[float]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
def get_today_daily(lat: float, lon: float, tz: str, target: date) -> TodayDaily:
    """Fetch today's forecast daily min/max temperatures from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": tz,
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    j = resp.json()
    d = j.get("daily") or {}
    times = d.get("time") or []
    tmax = d.get("temperature_2m_max") or []
    tmin = d.get("temperature_2m_min") or []
    target_str = target.isoformat()
    try:
        idx = times.index(target_str)
    except ValueError:
        return TodayDaily(date=target, tmin_c=None, tmax_c=None)
    tmin_v = tmin[idx] if idx < len(tmin) else None
    tmax_v = tmax[idx] if idx < len(tmax) else None
    return TodayDaily(date=target, tmin_c=tmin_v, tmax_c=tmax_v)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
def get_current_temperature(lat: float, lon: float, tz: str) -> CurrentWeather:
    """Fetch current 2m temperature from Open-Meteo current weather endpoint."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "timezone": tz,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    j = resp.json()
    cur = j.get("current") or {}
    return CurrentWeather(
        time_iso=cur.get("time"),
        temperature_c=cur.get("temperature_2m"),
    )

