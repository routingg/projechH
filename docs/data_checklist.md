# 데이터 수집 체크리스트 (Step 14 실데이터 연동용)

현재 서비스는 전부 mock 데이터로 동작 중이며, 아래 데이터를 받아야 실데이터 연동이 가능하다.
모든 데이터는 [공공데이터포털(data.go.kr)](https://www.data.go.kr) 회원가입 후 진행한다.

- **파일형**: 페이지에서 CSV/이미지 즉시 다운로드 → `backend/data/raw/`에 저장 (git 미추적)
- **API형**: "활용신청" 클릭 → 승인 후 마이페이지에서 **인증키(serviceKey)** 확인 → `backend/.env`에 입력
  - 승인은 자동(즉시)~1일 소요. **기상청 API는 신청 즉시 사용 가능하지만 키 활성화까지 1~2시간 걸릴 수 있음**

---

## 1. 무장애·휠체어 데이터 → 접근성 점수 (`mock_places.json` 대체)

- [ ] **제주올레길 1코스(종달리) 휠체어구간 무장애여행관광정보** — 파일형(CSV)
  - https://www.data.go.kr/data/15097499/fileData.do
- [ ] **제주올레길 14코스(금능리) 휠체어구간 무장애여행관광정보** — 파일형(CSV)
  - https://www.data.go.kr/data/15097502/fileData.do
- [ ] **사회적약자 시설 데이터(로드뷰) 구축 관광지 현황** — 파일형(CSV)
  - https://www.data.go.kr/data/15109153/fileData.do
- [ ] **사회적약자 시설데이터 로드뷰** — API형 (활용신청 필요)
  - https://www.data.go.kr/data/15109149/openapi.do
  - 발급키 → `.env`의 `DATA_GO_KR_API_KEY`

## 2. 교통 데이터 → 교통 점수 (place의 `near_low_floor_bus` 실측값)

- [ ] **제주특별자치도 저상버스현황** — 파일형(CSV)
  - https://www.data.go.kr/data/15114410/fileData.do
- [ ] **제주특별자치도 저상버스운행노선현황** — 파일형(CSV)
  - https://www.data.go.kr/data/15155485/fileData.do

## 3. 기상청 데이터 → 날씨 위험도 (`mock_weather.json` 대체)

- [ ] **기상청 단기예보 조회서비스** — API형 (활용신청 필요) ★핵심
  - https://www.data.go.kr/data/15084084/openapi.do
  - 발급키 → `.env`의 `KMA_API_KEY`
  - 필요 항목: 강수확률(POP), 풍속(WSD), 기온(TMP), 습도(REH) / 제주 격자좌표 nx=52, ny=38
- [ ] **기상청 기상특보 조회서비스** — API형 (활용신청 필요) ★핵심
  - https://www.data.go.kr/data/15000415/openapi.do
  - 같은 `KMA_API_KEY` 사용 가능 (계정 단위 키)
  - 필요 항목: 강풍·호우·태풍 특보/예비특보 (제주 지역코드 L1090000)
- [ ] (선택) **기상청 생활기상지수 조회서비스** — API형, 폭염 위험 보조
  - https://www.data.go.kr/data/15085288/openapi.do

## 4. 한국공항공사 데이터 → 공항 동선 (`mock_airport_*.json` 대체)

- [ ] **제주국제공항 도면 이미지 정보** — 파일형(이미지/ZIP)
  - https://www.data.go.kr/data/15151895/fileData.do
  - 층별 도면 이미지 → `frontend/public/static/airport/`에 배치 (현재 placeholder 경로와 동일하게)
- [ ] **제주공항 층별 입점업체 현황** — 파일형(CSV)
  - https://www.data.go.kr/data/15119335/fileData.do

## 5. JDC 데이터 → 면세점 매장정보 (`mock_jdc_stores.json` 대체)

- [ ] **제주국제공항 JDC면세점 매장정보** — API형 (활용신청 필요)
  - https://www.data.go.kr/data/15144890/openapi.do
  - 발급키 → `.env`의 `JDC_API_KEY`
  - ⚠ 면세점 매장정보(매장명·품목·위치·전화·운영시간)에만 사용. 편의시설 판단에 사용 금지

---

## 수집 후 작업 순서

1. 파일형 데이터 → `backend/data/raw/`에 저장 (`.gitignore`로 커밋 제외됨)
2. 전처리 스크립트로 `backend/data/processed/` 생성 → mock과 동일한 스키마로 변환
3. API 키를 `backend/.env`에 입력 (`.env.example` 참고, **커밋 금지**)
4. `weather_client.py` / `airport_client.py` / `jdc_client.py`에 실제 호출 코드 추가
5. **API 실패 시 mock fallback은 유지** (시연 안정성)

## 우선순위 제안

| 순위 | 데이터 | 이유 |
|---|---|---|
| 1 | 기상청 단기예보·특보 API | 서비스 핵심 데모(기상 악화→일정 재구성)가 실시간이 됨 |
| 2 | 관광지 CSV (올레길·로드뷰 관광지) | 관광지 4곳 → 실제 수십 곳으로 확장 |
| 3 | 저상버스 CSV | 교통 점수 실측화 |
| 4 | 공항 도면·입점업체 | 화면 완성도 (도면 placeholder 제거) |
| 5 | JDC API | 매장 목록 실데이터화 |
