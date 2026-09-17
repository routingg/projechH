# 데이터 출처

WheelTrip Jeju (ProjectH)가 사용하는 공공데이터 목록과 활용 범위.

## 1. 무장애·휠체어 데이터 (접근성 점수)

| 데이터 | URL |
|---|---|
| 제주올레길 1코스(종달리) 휠체어구간 무장애여행정보 | https://www.data.go.kr/data/15097499/fileData.do |
| 제주올레길 14코스(금능리) 휠체어구간 무장애여행정보 | https://www.data.go.kr/data/15097502/fileData.do |
| 사회적약자 시설데이터 로드뷰 (openapi) | https://www.data.go.kr/data/15109149/openapi.do |
| 사회적약자 시설 데이터(로드뷰) 구축 관광지 현황 | https://www.data.go.kr/data/15109153/fileData.do |

## 2. 교통 접근성 데이터 (교통 점수)

| 데이터 | URL |
|---|---|
| 제주특별자치도 저상버스현황 | https://www.data.go.kr/data/15114410/fileData.do |
| 제주특별자치도 저상버스운행노선현황 | https://www.data.go.kr/data/15155485/fileData.do |

## 3. 기상청 데이터 (날씨 위험도)

| 데이터 | URL |
|---|---|
| 기상청 단기예보 조회서비스 | https://www.data.go.kr/data/15084084/openapi.do |
| 기상청 기상특보 조회서비스 | https://www.data.go.kr/data/15000415/openapi.do |
| 기상청 생활기상지수 조회서비스 (선택 보조) | https://www.data.go.kr/data/15085288/openapi.do |

## 4. 공항공사 데이터 (공항 편의시설·동선)

| 데이터 | URL |
|---|---|
| 한국공항공사 제주국제공항 도면 이미지 정보 | https://www.data.go.kr/data/15151895/fileData.do |
| 한국공항공사 제주공항 층별 입점업체 현황 | https://www.data.go.kr/data/15119335/fileData.do |

활용: 공항 층별 도면 안내, 카페·편의점·은행 등 체류 가능 시설 안내, 출도 전 공항 내 이동·체류 동선 안내.

## 5. JDC 데이터 (면세점 매장정보 전용)

| 데이터 | URL |
|---|---|
| JDC 제주국제공항 면세점 매장정보 | https://www.data.go.kr/data/15144890/openapi.do |

활용: 면세점 매장명·판매품목·위치·전화번호·운영시간.

### JDC 데이터 사용 한계 (중요)

- JDC 데이터는 **면세점 매장정보 안내에만** 사용한다.
- JDC 데이터로 공항 편의시설 위치나 이용 가능 여부(휠체어 대여·수유실·물품보관함 등)를 판단하지 않는다.
- 공항 편의시설·동선 정보는 한국공항공사 데이터로 처리한다.
- JDC 고객서비스 헌장·편의시설 안내 링크는 사용하지 않는다.

## 공통 주의

- 본 서비스의 추천 결과는 참고 정보이며 휠체어 접근 가능성이나 안전을 보장하지 않는다.
- 데이터에서 확인되지 않은 정보는 "정보 없음(null/unknown)"으로 유지하며, 있다고 가정하지 않는다.
