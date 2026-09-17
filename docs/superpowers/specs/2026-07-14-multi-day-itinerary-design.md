# 항공편 기반 다일정(몇박 며칠) 추천 — 설계

2026-07-14 승인. 사용자 결정: 편명 자동 조회(B551178) · 지역 클러스터링 · A안(오케스트레이터 신설).

## 목적

도착 항공편(제주행)과 출발 항공편(제주발)을 입력받아 체류 기간(N박 M일)을 계산하고,
일자별로 지역을 묶은 하루 일정들을 한 번에 추천한다. 같은 날 도착·출발이면 기존
당일 일정과 동일하게 동작한다.

## 확정된 외부 API 사실 (2026-07-14 실측)

한국공항공사 실시간 항공운항 현황 `https://apis.data.go.kr/B551178/flight-status`
— **기존 data.go.kr 키로 이미 승인·작동 확인**.

- 도착편: `GET /arrival?serviceKey&type=json&searchday=YYYYMMDD&airport_code=CJU&flight_id=RS901&line=D&numOfRows&pageNo`
- 출발편: `GET /depart?...` (동일 파라미터, 응답의 도착공항 코드 철자는 `arrvAirportCode`)
- 응답 필드: `flightid, airline, depAirport(Code), arrAirport, scheduledatetime(YYYYMMDDHHMM),
  estimateddatetime, rmkKor(도착/출발/사전결항), line(국내/국제), codeshare, io`
- `flight_id`는 정확 일치 검색 (부분 문자열 불가)
- **조회 범위: 오늘 기준 약 +3일까지** (+7일은 0건) — 범위 밖 날짜는 시간 직접 입력으로 폴백
- 기상청 단기예보(getVilageFcst) 응답에는 +2~3일치가 포함됨 — 현재 코드는 첫날만 집계하므로
  일자별 집계로 확장 (`weather_client.fetch_forecast`)

## 백엔드

### 1. flight_client.py (신규 서비스)

`search_flights(direction: "arrival"|"departure", date: "YYYY-MM-DD", flight_id: str|None) -> list[dict]`

- 제주 기준 고정: arrival 은 `airport_code=CJU`(제주 도착), departure 는 `depart` 오퍼레이션 + `airport_code=CJU`
- 반환 항목: `{flight_id, airline, counterpart_airport(상대 공항명), scheduled_time("HH:MM"),
  estimated_time, status(rmkKor), is_cancelled(사전결항/결항 포함 여부), date}`
- 10분 TTL 캐시(weather_client 패턴), 실패·0건이면 빈 목록 (mock 없음 — 프론트가 수동 입력 폴백)

### 2. GET /api/flights (신규 라우터)

쿼리: `direction, date, flight_id?` → `{flights: [...], searchable: bool}`
(`searchable=false` = 해당 날짜 조회 결과 자체가 0건 → 프론트가 "시간 직접 입력" 안내)

### 3. POST /api/itinerary/multi (신규, 기존 /api/itinerary 무변경 유지)

요청:
```json
{ "user_profile": {...},
  "arrival_date": "2026-07-20", "arrival_time": "10:30",
  "departure_date": "2026-07-22", "departure_time": "18:30",
  "selected_place_ids": ["bf_674"] }
```
응답:
```json
{ "nights": 2, "days_count": 3, "trip_label": "2박 3일",
  "days": [ { "date": "2026-07-20", "day_label": "1일차", "region_label": "제주시권",
              "weather_summary": {...} | null, "forecast_available": true,
              "slots": [ItinerarySlot...] } ],
  "early_departure": {...}, "cautions": [...] }
```
- 검증: departure < arrival 이면 422. 같은 날이면 days 1개(기존 당일 로직 결과).
- 슬롯 스키마는 기존 `ItinerarySlot` 재사용 (place_id·is_user_selected 포함).

### 4. multi_itinerary_service.py (신규 오케스트레이터)

1. **일수 계산**: arrival_date~departure_date → N박 M일 (당일=0박 1일)
2. **일자별 날씨**: `weather_client.fetch_forecast_daily()` 신규 — 기존 응답을 fcstDate 별로
   집계해 `{date: weather_dict}` 반환(+3일 내). 범위 밖 날짜는 None →
   해당 day 에 `forecast_available: false` + caution "예보 범위 밖 날짜는 날씨를 반영하지 못했습니다"
3. **권역 분류**: 좌표 규칙 — 서부(lon<126.35), 동부(lon>126.75), 남부(lat<33.35), 나머지 제주시권.
   좌표 없는 장소는 제주시권 취급.
4. **일자별 권역 배정**: 1일차·마지막날 = 제주시권(공항 인근), 중간일 = 남부→동부→서부 순회
   (중간일이 3일 초과면 반복). 해당 권역 장소가 부족하면 인접 권역에서 보충.
5. **하루 생성**: 기존 `itinerary_service._pick_visits` 재사용 (권역 필터 + 사용한 장소 누적 제외).
   - 1일차: 도착시각+1시간(수속·이동)부터. 14시 이후 시작이면 1곳, 아니면 2곳
   - 중간일: 2곳(기존 로직)
   - 마지막날: 출발 2시간 전(악천후 2.5시간) 공항 도착 역산. 오전 1곳 + pre_departure 슬롯
   - 점심 슬롯은 일정이 12:30 을 걸치는 날만 삽입
6. **담은 장소 분배**: 각 선택 장소를 그 장소의 권역이 배정된 날에 우선 배치,
   맞는 날이 없으면 중간일에 순서대로. 등급 무관 드롭 금지(기존 원칙).
7. **cautions**: 기존 문구 + 결항/예보 범위/장소 부족 안내.

## 프론트엔드

### PlannerConditionBar 교체 (여행 날짜·출도 시간 → 항공편 2줄)

- `도착 항공편`: [날짜][편명 입력][🔍 조회] → 성공 시 "김포→제주 RS901 · 에어서울 · 07:15 도착"
  확정 칩 표시. 결항이면 빨간 경고. 조회 0건(범위 밖·미취항)이면 [도착 시간 직접 입력] 노출.
- `출발 항공편`: 동일 (제주발). 기존 `departure_time` 프로필 필드는 출발 항공편 시각으로 채움
  (공항 스텝·기존 로직 하위호환).
- 날짜가 같으면 "당일 여행" 배지, 다르면 "N박 M일" 배지 자동 표시.
- 추천(query) 요청의 `travel_date`는 arrival_date 사용.

### PlannerPage ④ 일정 스텝

- `postItineraryMulti()` 호출 (같은 날이어도 multi 사용 — 응답 days 1개).
- days 를 일자별 아코디언(1일차/2일차…, region_label·날씨 요약 표기)으로 렌더,
  각 day 는 기존 `ItineraryTimeline` 재사용 (day.slots → Itinerary 형태로 매핑).
- `forecast_available=false` 인 날은 "예보 범위 밖 — 날씨 미반영" 배지 (정직 표기).
- ⑤ 공항 스텝은 출발 항공편 시각으로 `postAirportPlan` 호출 (기존 그대로).

## 오류 처리

- 항공편 API 실패/0건 → 수동 시간 입력 (일정 생성은 시간만 있으면 동작)
- 결항(`사전결항` 등) 편명 선택 시 경고 배너 표시하되 진행은 허용 (스케줄 변동 가능)
- 날짜 역전 → 422 + 프론트 인라인 오류
- 기존 `/api/itinerary`·팀원 RAG 계약 무변경 (스키마 추가만)

## 테스트/검증

- flight_client: 실 API 편명 검색(당일)·0건 날짜(+7일)·결항 필드 매핑 curl 검증
- multi: 당일(days 1)·1박2일·2박3일·5박(예보 범위 밖 포함)·selected 분배·날짜 역전 422
- 프론트: 편명 조회 성공/폴백/결항 3상태, 일자별 아코디언, 빌드+oxlint
