from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List, Any, Dict, Callable

import math
import pandas as pd
import re


@dataclass
class JoseonWeather:
    date: date
    location: Optional[str]
    description: Optional[str]


def _try_parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    # pandas Timestamp or datetime
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date()
    # strings with common separators
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    # If it still fails, let pandas try
    try:
        ts = pd.to_datetime(s, errors="coerce")
        if pd.isna(ts):
            return None
        if isinstance(ts, pd.Timestamp):
            return ts.date()
    except Exception:
        return None
    return None


def _normalize_key(value: Any) -> str:
    s = str(value).strip().lower()
    # remove punctuation, quotes, brackets, spaces; keep korean/latin digits
    s = re.sub(r"[^0-9a-z\uac00-\ud7a3]", "", s)
    return s


def _first_existing_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    normalized_to_original: Dict[str, Any] = {}
    for c in df.columns:
        key = _normalize_key(c)
        if key:
            normalized_to_original[key] = c
    for cand in candidates:
        key = _normalize_key(cand)
        if key in normalized_to_original:
            return normalized_to_original[key]
    return None


def _find_by_tokens(df: pd.DataFrame, tokens: List[str]) -> Optional[str]:
    token_keys = [_normalize_key(t) for t in tokens if t and str(t).strip()]
    for c in df.columns:
        col_key = _normalize_key(c)
        if all(tok in col_key for tok in token_keys):
            return c
    return None


def _read_table_with_fallbacks(p: Path) -> pd.DataFrame:
    """Try reading with multiple engines/encodings depending on suffix."""
    suffix = p.suffix.lower()
    # Excel first
    if suffix == ".xls":
        # Try as legacy excel via xlrd, then as HTML table (some .xls are HTML exports), then openpyxl
        try:
            return pd.read_excel(p, engine="xlrd")
        except Exception:
            pass
        try:
            tables = pd.read_html(p, flavor="lxml")
            if tables:
                return tables[0]
        except Exception:
            pass
        try:
            return pd.read_excel(p, engine="openpyxl")
        except Exception:
            pass
    elif suffix in {".xlsx", ".xlsm", ".xltx"}:
        try:
            return pd.read_excel(p, engine="openpyxl")
        except Exception:
            pass

    # Delimited text
    if suffix in {".csv", ".tsv", ".tab", ".txt"}:
        seps = [",", "\t", "|"] if suffix == ".csv" else ["\t", ",", "|"]
        encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
        for sep in seps:
            for enc in encodings:
                try:
                    return pd.read_csv(p, sep=sep, encoding=enc, on_bad_lines="skip")
                except Exception:
                    continue

    # JSON
    if suffix == ".json":
        try:
            return pd.read_json(p)
        except Exception:
            pass

    # Last resort: try read_excel without explicit engine, then read_html
    try:
        return pd.read_excel(p)
    except Exception:
        pass
    try:
        tables = pd.read_html(p)
        if tables:
            return tables[0]
    except Exception:
        pass
    # As a final fallback, try csv default
    return pd.read_csv(p, encoding="utf-8", engine="python", on_bad_lines="skip")


def load_joseon_weather(path: str | Path) -> List[JoseonWeather]:
    """Load Joseon weather table from CSV/TSV/XLSX/JSON with heuristic column detection.

    Expects a date column and at least one of (location, description).
    Known column name candidates:
      - date: [date, 날짜, 양력, 양력날짜, 양력일자, gregorian_date, solar_date]
      - location: [location, 지역, 지명, place]
      - description: [weather, 기상, 기상현상, 날씨, 현상, 내용, 발췌]
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"파일 없음: {p}")

    df = _read_table_with_fallbacks(p)

    date_col = _first_existing_column(
        df,
        [
            "date",
            "날짜",
            "양력",
            "양력날짜",
            "양력일자",
            "gregorian_date",
            "solar_date",
        ],
    )
    if not date_col:
        # Try explicit year/month/day columns (e.g., ('서기력','년'))
        y_col = _first_existing_column(
            df,
            [
                "year",
                "gregorian_year",
                "ad_year",
                "서기년",
                "양력년",
            ],
        ) or _find_by_tokens(df, ["서기력", "년"]) or _find_by_tokens(df, ["양력", "년"])

        m_col = _first_existing_column(
            df,
            [
                "month",
                "gregorian_month",
                "ad_month",
                "서기월",
                "양력월",
            ],
        ) or _find_by_tokens(df, ["서기력", "월"]) or _find_by_tokens(df, ["양력", "월"])

        d_col = _first_existing_column(
            df,
            [
                "day",
                "gregorian_day",
                "ad_day",
                "서기일",
                "양력일",
            ],
        ) or _find_by_tokens(df, ["서기력", "일"]) or _find_by_tokens(df, ["양력", "일"])

        if y_col is not None and m_col is not None and d_col is not None:
            # Build a temp date column
            dates: List[Optional[date]] = []
            for _, row in df.iterrows():
                try:
                    y = int(str(row.get(y_col)).split()[0])
                    m = int(str(row.get(m_col)).split()[0])
                    d = int(str(row.get(d_col)).split()[0])
                    dt = date(y, m, d)
                except Exception:
                    dt = None
                dates.append(dt)
            df["__built_date__"] = dates
            date_col = "__built_date__"

    if not date_col:
        raise ValueError("날짜 컬럼을 찾지 못했습니다. date/양력/서기 또는 (년/월/일) 조합 필요")

    loc_col = _first_existing_column(df, ["location", "지역", "지명", "place", "장소"]) or _find_by_tokens(df, ["장소"]) or _find_by_tokens(df, ["지명"]) or _find_by_tokens(df, ["지역"])
    desc_col = _first_existing_column(
        df, ["weather", "기상", "기상현상", "날씨", "현상", "내용", "발췌", "기사내용", "본문", "원문", "번역", "기사", "텍스트"]
    )

    records: List[JoseonWeather] = []
    for _, row in df.iterrows():
        d = _try_parse_date(row.get(date_col))
        if not d:
            continue
        loc = str(row.get(loc_col)).strip() if loc_col and not pd.isna(row.get(loc_col)) else None
        desc = None
        if desc_col and not pd.isna(row.get(desc_col)):
            desc = str(row.get(desc_col)).strip()
        if not desc:
            # Heuristic: pick first column with long korean text
            for c in df.columns:
                val = row.get(c)
                if isinstance(val, str) and len(val) >= 10 and re.search(r"[\uac00-\ud7a3]", val):
                    desc = val.strip()
                    break
        records.append(JoseonWeather(date=d, location=loc, description=desc))
    # sort by date for stable nearest search
    records.sort(key=lambda r: r.date)
    return records


def find_best_match(
    records: List[JoseonWeather],
    target_date: date,
    location_hint: Optional[str] = None,
    tolerance_days: int = 0,
) -> Optional[JoseonWeather]:
    """Find exact or nearest record within tolerance. Prefer rows matching location_hint."""
    if not records:
        return None

    # exact date first
    same_day = [r for r in records if r.date == target_date]
    if same_day:
        if location_hint:
            hint = str(location_hint).strip().lower()
            prioritized = []
            for r in same_day:
                loc = str(r.location).strip().lower() if r.location is not None else ""
                if hint and loc and hint in loc:
                    prioritized.append(r)
            return prioritized[0] if prioritized else same_day[0]
        return same_day[0]

    if tolerance_days <= 0:
        return None

    # nearest within tolerance
    def score(r: JoseonWeather) -> tuple:
        dd = abs((r.date - target_date).days)
        loc_score = 0
        if location_hint:
            hint = str(location_hint).strip().lower()
            loc = str(r.location).strip().lower() if r.location is not None else ""
            if hint and loc and hint in loc:
                loc_score = -1  # better
        return (dd, loc_score)

    candidates = [r for r in records if abs((r.date - target_date).days) <= tolerance_days]
    if not candidates:
        return None
    candidates.sort(key=score)
    return candidates[0]


def format_summary_line(match: JoseonWeather, source_label: str = "조선왕조실록") -> str:
    def _truncate(text: str, max_len: int = 100) -> str:
        t = (text or "").strip()
        return (t[: max_len - 1] + "…") if len(t) > max_len else t

    loc = f", {match.location}" if match.location else ""
    desc = _truncate(match.description if match.description else "기록 있음")
    return f"{source_label}: {match.date.isoformat()}{loc}: {desc}"


def _score_preference(r: JoseonWeather, location_hint: Optional[str]) -> tuple:
    # Prefer rows matching location_hint and having longer description
    loc_score = 0
    if location_hint:
        hint = str(location_hint).strip().lower()
        loc = str(r.location).strip().lower() if r.location else ""
        if hint and loc and hint in loc:
            loc_score = -1  # better
    desc_len = len(r.description) if isinstance(r.description, str) else 0
    return (loc_score, -desc_len)


def find_monthday_match(
    records: List[JoseonWeather], target_date: date, location_hint: Optional[str] = None
) -> Optional[JoseonWeather]:
    same_md = [r for r in records if r.date.month == target_date.month and r.date.day == target_date.day]
    if not same_md:
        return None
    same_md.sort(key=lambda r: _score_preference(r, location_hint))
    return same_md[0]


def find_year_shift_match(
    records: List[JoseonWeather], target_date: date, year_shift: int = 500, location_hint: Optional[str] = None
) -> Optional[JoseonWeather]:
    try:
        shifted = date(target_date.year - year_shift, target_date.month, target_date.day)
    except Exception:
        return None
    exact = [r for r in records if r.date == shifted]
    if not exact:
        return None
    exact.sort(key=lambda r: _score_preference(r, location_hint))
    return exact[0]


def find_nearest_by_doy(
    records: List[JoseonWeather], target_date: date, max_diff_days: Optional[int] = None, location_hint: Optional[str] = None
) -> Optional[JoseonWeather]:
    def doy(d: date) -> int:
        return (d - date(d.year, 1, 1)).days

    target_doy = doy(target_date)
    def score(r: JoseonWeather) -> tuple:
        diff = abs(doy(r.date) - target_doy)
        loc_score, desc_score = _score_preference(r, location_hint)
        return (diff, loc_score, desc_score)

    candidates = records
    if max_diff_days is not None:
        candidates = [r for r in records if abs(doy(r.date) - target_doy) <= max_diff_days]
        if not candidates:
            return None
    return min(candidates, key=score)



