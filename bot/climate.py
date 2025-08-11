from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple, List
import csv
import math

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class NormalForDay:
    month: int
    day: int
    tmin_c: Optional[float]
    tmax_c: Optional[float]

    @property
    def tmean_c(self) -> Optional[float]:
        if self.tmin_c is None or self.tmax_c is None:
            return None
        return (self.tmin_c + self.tmax_c) / 2.0


def _round_coord(value: float) -> float:
    return round(value, 3)


def _cache_file(lat: float, lon: float, month: int) -> Path:
    cache_dir = Path("cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"normal_{_round_coord(lat)}_{_round_coord(lon)}_{month:02d}.csv"


def _write_cache(path: Path, rows: List[Tuple[int, float, float]]):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["day", "tmin_c", "tmax_c"])  # header
        for day, tmin, tmax in rows:
            w.writerow([day, f"{tmin:.4f}" if tmin is not None else "", f"{tmax:.4f}" if tmax is not None else ""])


def _read_cache(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    result = {}
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            day = int(row["day"]) if row.get("day") else None
            tmin = float(row["tmin_c"]) if row.get("tmin_c") else None
            tmax = float(row["tmax_c"]) if row.get("tmax_c") else None
            if day is not None:
                result[day] = (tmin, tmax)
    return result


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.7, min=0.7, max=5))
def _fetch_month_for_year(lat: float, lon: float, year: int, month: int) -> dict:
    """Fetch ERA5 daily tmin/tmax for the given month in a single year."""
    start_date = date(year, month, 1)
    last_day = _last_day_of_month(year, month)
    end_date = date(year, month, last_day)

    url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "UTC",
    }
    resp = requests.get(url, params=params, timeout=40)
    resp.raise_for_status()
    return resp.json()


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    next_month = date(year, month + 1, 1)
    last_day = (next_month - (date(2000, 1, 2) - date(2000, 1, 1))).day
    return last_day


def _safe_mean(values: List[float]) -> Optional[float]:
    seq = [v for v in values if v is not None and not math.isnan(v)]
    if not seq:
        return None
    return sum(seq) / len(seq)


def get_daily_normal(lat: float, lon: float, target_month: int, target_day: int) -> NormalForDay:
    """Return climatological normal (1991–2020) for the given month/day using ERA5 daily tmin/tmax.

    Strategy: fetch all days in target month from 1991..2020, then average entries with day==target_day across years.
    Results are cached per (rounded lat, lon, month).
    """
    cache_path = _cache_file(lat, lon, target_month)
    cache = _read_cache(cache_path)
    if cache is None or target_day not in cache:
        rows = {}
        for y in range(1991, 2021):
            data = _fetch_month_for_year(lat, lon, y, target_month)
            daily = data.get("daily") or {}
            times = daily.get("time") or []
            tmins = daily.get("temperature_2m_min") or []
            tmaxs = daily.get("temperature_2m_max") or []
            for t, tmin, tmax in zip(times, tmins, tmaxs):
                dt = datetime.strptime(t, "%Y-%m-%d").date()
                day = dt.day
                pair = rows.get(day, ([], []))
                pair[0].append(tmin)
                pair[1].append(tmax)
                rows[day] = pair
        cache_rows = []
        for day, (mins, maxs) in sorted(rows.items()):
            cache_rows.append((day, _safe_mean(mins), _safe_mean(maxs)))
        _write_cache(cache_path, cache_rows)
        cache = _read_cache(cache_path)

    tmin_c, tmax_c = cache.get(target_day, (None, None))
    return NormalForDay(month=target_month, day=target_day, tmin_c=tmin_c, tmax_c=tmax_c)


def estimate_1525_from_normal(normal: NormalForDay, warming_since_1850_c: float, lia_extra_cooling_c: float) -> Optional[float]:
    """Estimate 1525 daily mean from 1991–2020 normal by subtracting warming and LIA extra cooling."""
    if normal.tmean_c is None:
        return None
    delta = (warming_since_1850_c or 0.0) + (lia_extra_cooling_c or 0.0)
    return normal.tmean_c - delta


