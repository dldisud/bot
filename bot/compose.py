from __future__ import annotations

from datetime import date


def _fmt_temp(value: float | None) -> str:
    return f"{value:.1f}℃" if value is not None else "–"


def compose_tweet(
    place_display: str,
    target_date: date,
    today_mean_c: float | None,
    normal_mean_c: float | None,
    approx_1525_mean_c: float | None,
    warming_c: float,
    lia_cooling_c: float,
    joseon_summary: str | None = None,
    current_temp_c: float | None = None,
    tag: str | None = None,
) -> str:
    today_s = _fmt_temp(today_mean_c)
    normal_s = _fmt_temp(normal_mean_c)
    past_s = _fmt_temp(approx_1525_mean_c)

    diff = None
    if today_mean_c is not None and approx_1525_mean_c is not None:
        diff = today_mean_c - approx_1525_mean_c
    diff_s = f"{diff:+.1f}℃" if diff is not None else "–"
    tendency = "더 따뜻합니다" if (diff is not None and diff > 0) else ("더 선선합니다" if (diff is not None and diff < 0) else "비교 불가")

    # 280자 이내를 목표로 짧게 작성
    header = f"{target_date.strftime('%Y-%m-%d')} {place_display}"
    if tag and tag.strip():
        header = f"[{tag.strip()}] " + header
    lines = [
        header,
        f"오늘(예상 평균): {today_s} / 평년(1991–2020): {normal_s}",
        f"1525년 같은 날(근사): {past_s} → 차이 {diff_s} ({tendency})",
        f"보정: 온난화 {warming_c:.1f}℃ + 소빙기 {lia_cooling_c:.1f}℃",
    ]
    if joseon_summary:
        lines.append(joseon_summary)
    if current_temp_c is not None:
        lines.append(f"지금 기온: {current_temp_c:.1f}℃")
    lines.append("데이터: Open‑Meteo (Forecast/ERA5)")
    text = "\n".join(lines)
    return text


