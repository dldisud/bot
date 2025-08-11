### 500년 전과 오늘의 날씨 비교 트위터 봇

이 봇은 같은 날짜(예: 8월 12일)의 오늘 날씨와 500년 전(1525년) 근사 기온을 비교해 트윗합니다.

- **현재 날씨**: Open‑Meteo 무료 API의 `current` 데이터를 사용합니다.
- **500년 전 근사**: 해당 위치의 1991–2020 일별 평년(ERA5 재분석 `archive-api`)에서 같은 월·일의 평균기온(일최고·일최저의 평균)을 구하고, 여기에
  - 산업화 이전(1850–1900) 대비 현재의 온난화(+기본 1.2℃)
  - 1525년 경 소빙기(LIA) 시기의 추가 냉각(+기본 0.4℃)
  를 반영해 과거(1525년) 기온을 근사합니다. 즉, `1525 ≈ 평년 − (1.2 + 0.4)℃`.

주의: 500년 전의 “일별 실제 날씨”는 존재하지 않으므로 과학적 근사치입니다. 강수 등은 불확실성이 커서 기본은 기온만 비교합니다.

### 빠른 시작

1) 가상환경과 의존성 설치 (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
```

2) 환경변수 파일 생성

```powershell
Copy-Item .env.example .env
# .env 파일 열어 트위터 키/토큰과 위치 등을 채우세요
```

3) 드라이런 실행 (트윗 미게시)

```powershell
.\.venv\Scripts\python.exe -m bot.main --place "Seoul" --dry-run
```

4) 실제 게시

```powershell
# .env에서 POST_TO_TWITTER=true 로 바꾸거나, CLI로 --post 사용
.\.venv\Scripts\python.exe -m bot.main --place "Seoul" --post
```

### 스케줄 실행(Windows)

- 작업 스케줄러에서 매일 원하는 시간에 `python -m bot.main --post`를 실행하도록 등록하세요.
- 가상환경 경로: `.\.venv\Scripts\python.exe`

### 환경변수 요약

- **LOCATION_NAME**: 기본 도시/지명(예: `Seoul`). CLI `--place`가 우선합니다.
- **LANGUAGE**: `ko` 추천.
- **TIMEZONE**: 예 `Asia/Seoul`.
- **POST_TO_TWITTER**: `true`면 게시, 아니면 콘솔 출력.
- **WARMING_SINCE_1850_C**: 1850–1900 대비 현재 온난화(기본 1.2℃).
- **LIA_EXTRA_COOLING_C**: 1525년 경 소빙기 추가 냉각(기본 0.4℃).

### 면책

- 1525년 “해당 날짜의 실제 날씨”는 알 수 없으며, 본 봇은 기후평년과 문헌 기반 보정치를 이용한 **근사치**입니다.
- Open‑Meteo API 상태나 네트워크 이슈에 따라 실패할 수 있습니다.

