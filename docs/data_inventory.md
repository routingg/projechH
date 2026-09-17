# 데이터 인벤토리 (backend/data/raw)

수집한 원본 데이터를 용도별 폴더로 정리한 목록. **모든 CSV는 `cp949`(EUC-KR) 인코딩** —
에디터에서 한글이 깨지면 EUC-KR로 다시 열 것. (빌드 스크립트는 인코딩 자동 처리)

`backend/data/raw/` 는 `.gitignore` 대상이라 파일 자체는 커밋되지 않는다. 아래는 로컬 구성 참고용.

```
backend/data/raw/
├── barrier_free_tourism/        # 무장애 관광 정보
│   ├── jejudatahub_attractions/ #   제주데이터허브 개별 관광지 90개 (CSV 70 + HWP 20) → RAG 벡터DB 소스
│   │   └── _download_summary.json
│   └── datagokr_points/         #   공공데이터포털 개별 CSV 5개
├── transport/                   # 저상버스현황 · 운행노선현황
├── airport/                     # 한국공항공사
│   ├── floor_maps/              #   제주공항 도면 SVG(1~4층) + 2층 면세점 PNG
│   └── 층별_입점업체_현황.csv
├── jdc_dutyfree/                # JDC 면세점 매장정보 원본(jdc_brands_raw.txt)
├── jeju_gis_api/                # 제주 GIS API 원본 JSON (list/meta/img)
└── tools/                       # download_jeju_attachments.py (데이터허브 수집 스크립트)
```

## 그룹별 설명

### 1. barrier_free_tourism — 무장애 관광 정보
| 위치 | 내용 | 스키마 | 용도 |
|---|---|---|---|
| `jejudatahub_attractions/` (90개) | 제주데이터허브 "무장애여행정보" 관광지별 파일 | `위도·경도·장소명칭·장소상세정보·무장애관광정보·추천코스여부·품질·기준일자` | **RAG 벡터DB** |
| `datagokr_points/올레길10코스…무장애여행정보` | 공공데이터포털, 위 스키마와 **동일** | ↑ 동일 | RAG에 함께 사용 가능 |
| `datagokr_points/사회적약자 시설현황` (108행) | 관광지별 접근성 요약표 | `관광지명·주소·전화·장애인화장실(개수)·주차(개수)·대여Y/N·수유실·휴게실` | 관광지 점수(GIS와 동일 원천) |
| `datagokr_points/…주변정보·중문단지` | 관광지 주변 편의시설 | `관광지명·주변시설종류·명칭·반경·주소·연락처…` | 주변시설 안내(보조) |
| `datagokr_points/올레길1코스 위치정보` | 올레1 휠체어 구간 좌표 포인트 | `순서·위도·경도·구분·설명·포인트…` | 코스 포인트(보조) |

> 핵심: **제주데이터허브 90개 + datagokr 올레길10코스**는 스키마가 같아 그대로 병합해 쓸 수 있다.
> 나머지 datagokr 파일은 테마는 같아도 형식·용도가 다르다.

### 2. transport — 교통
- `저상버스현황` (160행: 노선·차량·업체), `저상버스운행노선현황` — 교통 접근성 보조.

### 3. airport — 한국공항공사
- `floor_maps/` : 제주공항 1~4층 도면 SVG + 2층 면세점 안내 PNG → **공항 도면 뷰어**
- `층별_입점업체_현황.csv` (77개) → **공항 시설 목록**
- 처리: `backend/scripts/build_airport_data.py`

### 4. jdc_dutyfree — JDC 면세점
- `jdc_brands_raw.txt` : JDC API 원본(129개 매장). 처리: `scripts/fetch_jdc.py`

### 5. jeju_gis_api — 제주 GIS API 원본
- `jeju_tour_{list,meta,img}_raw.json` : 관광지 목록·좌표·이미지 원본. 처리: `scripts/fetch_jeju_places.py`

## 데이터 → 코드 경로 매핑
| 원본 폴더 | 처리 스크립트 | 산출물 |
|---|---|---|
| `airport/` | `scripts/build_airport_data.py` | `processed/airport_facilities.json`, `airport_floor_maps.json` |
| `jdc_dutyfree/` (또는 실 API) | `scripts/fetch_jdc.py` | `processed/jdc_stores.json` |
| (제주 GIS 실 API) | `scripts/fetch_jeju_places.py` | `processed/jeju_places.json` + `jeju_gis_api/*.json` |
| `barrier_free_tourism/jejudatahub_attractions/` | `scripts/preprocess/build_rag_vector_db.py` | `vector_store/` (FAISS) |
