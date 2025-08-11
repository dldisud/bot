from __future__ import annotations

import argparse
from datetime import datetime
import sys

import pytz

from .config import load_settings
from .geo import geocode_place
from .weather import get_today_daily, get_current_temperature
from .climate import get_daily_normal, estimate_1525_from_normal
from .compose import compose_tweet
from .twitter import post_tweet_if_enabled
from .joseon import (
    load_joseon_weather,
    find_best_match,
    format_summary_line,
    find_monthday_match,
    find_year_shift_match,
    find_nearest_by_doy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="오늘과 500년 전(근사) 날씨 비교 트위터 봇")
    parser.add_argument("--place", type=str, help="지명/도시명", default=None)
    parser.add_argument("--date", type=str, help="YYYY-MM-DD (기본: 오늘)", default=None)
    parser.add_argument("--post", action="store_true", help="실제 트윗 게시")
    parser.add_argument("--with-current", action="store_true", help="현재 기온을 본문에 포함")
    parser.add_argument("--tag", type=str, default=None, help="머리말 태그 추가 (예: 아침/점심/저녁)")
    parser.add_argument("--dry-run", action="store_true", help="게시하지 않고 본문만 출력")
    parser.add_argument(
        "--joseon-path",
        type=str,
        default=None,
        help="조선왕조실록 날씨 데이터 파일 경로(csv/tsv/xlsx/json)",
    )
    parser.add_argument(
        "--joseon-loc",
        type=str,
        default=None,
        help="기록 중 우선할 지역 키워드(예: 한양, 서울)",
    )
    parser.add_argument(
        "--joseon-tol",
        type=int,
        default=0,
        help="해당 날짜 기록 없을 시 허용 오차 일수(정수). 0은 같은 날짜만",
    )
    parser.add_argument(
        "--joseon-mode",
        type=str,
        default="exact",
        choices=["exact", "monthday", "yearshift", "doy"],
        help="실록 매칭 모드: exact(같은 날짜), monthday(월일), yearshift(500년 전 같은 날짜), doy(연중일 근접)",
    )
    return parser.parse_args()


def main() -> int:
    settings = load_settings()
    args = parse_args()

    place = args.place or settings.location_name
    tz_name = settings.timezone
    tz = pytz.timezone(tz_name)

    if args.date:
        target_dt = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_dt = datetime.now(tz)
    target_date = target_dt.date()

    geo = geocode_place(place, language=settings.language)
    display_place = geo.name or place

    today_daily = get_today_daily(geo.latitude, geo.longitude, tz_name, target_date)
    normal = get_daily_normal(geo.latitude, geo.longitude, target_date.month, target_date.day)
    approx_1525 = estimate_1525_from_normal(
        normal,
        warming_since_1850_c=settings.warming_since_1850_c,
        lia_extra_cooling_c=settings.lia_extra_cooling_c,
    )

    joseon_summary = None
    joseon_path = args.joseon_path or settings.joseon_path
    joseon_mode = args.joseon_mode or settings.joseon_mode
    joseon_loc = args.joseon_loc or settings.joseon_loc
    joseon_tol = args.joseon_tol or settings.joseon_tol
    if joseon_path:
        try:
            records = load_joseon_weather(joseon_path)
            mode = joseon_mode
            match = None
            if mode == "exact":
                match = find_best_match(records, target_date, joseon_loc, joseon_tol)
            elif mode == "monthday":
                match = find_monthday_match(records, target_date, joseon_loc)
            elif mode == "yearshift":
                match = find_year_shift_match(records, target_date, 500, joseon_loc)
            elif mode == "doy":
                match = find_nearest_by_doy(records, target_date, max_diff_days=joseon_tol or None, location_hint=joseon_loc)
            if match:
                joseon_summary = format_summary_line(match)
        except Exception as e:
            joseon_summary = f"조선왕조실록: 불러오기 실패({e})"

    current_temp = None
    if args.with_current:
        try:
            cur = get_current_temperature(geo.latitude, geo.longitude, tz_name)
            current_temp = cur.temperature_c
        except Exception:
            current_temp = None

    text = compose_tweet(
        place_display=display_place,
        target_date=target_date,
        today_mean_c=today_daily.tmean_c,
        normal_mean_c=normal.tmean_c,
        approx_1525_mean_c=approx_1525,
        warming_c=settings.warming_since_1850_c,
        lia_cooling_c=settings.lia_extra_cooling_c,
        joseon_summary=joseon_summary,
        current_temp_c=current_temp,
        tag=args.tag,
    )

    post_enabled = args.post or (settings.post_to_twitter and not args.dry_run)
    post_tweet_if_enabled(
        text=text,
        post_enabled=post_enabled,
        consumer_key=settings.twitter_api_key,
        consumer_secret=settings.twitter_api_secret,
        access_token=settings.twitter_access_token,
        access_token_secret=settings.twitter_access_token_secret,
        bearer_token=settings.twitter_bearer_token,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


