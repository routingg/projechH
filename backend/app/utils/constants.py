"""점수화에 사용하는 상수 (가이드 §9)."""

# ── 접근성 가중치 ──
ACC_TOILET = 20        # 장애인 화장실
ACC_PARKING = 20       # 장애인 주차장
ACC_RENTAL = 15        # 휠체어 대여
ACC_RAMP = 20          # 휠체어 접근 가능 경로(램프)
ACC_SURFACE_GOOD = 15  # 노면 상태 양호
ACC_INDOOR = 10        # 실내 관광지

# ── 날씨 위험도 ──
RAIN_HIGH = 60         # 강수확률(%) 이상 +20
RAIN_VERY_HIGH = 80    # 이상 +30
WIND_HIGH = 8.0        # 풍속(m/s) 이상 +20
WIND_VERY_HIGH = 12.0  # 이상 +35
WEATHER_RAIN_HIGH = 20
WEATHER_RAIN_VERY_HIGH = 30
WEATHER_WIND_HIGH = 20
WEATHER_WIND_VERY_HIGH = 35
WEATHER_HEAT = 25
ALERT_HEAVY_RAIN = 40  # 호우특보
ALERT_WIND = 40        # 강풍특보
ALERT_TYPHOON = 60     # 태풍특보
# 예비특보는 정식 특보의 절반으로 반영
PRELIMINARY_ALERT_FACTOR = 0.5
# 실내 관광지는 날씨 위험도 영향을 작게 받는다
INDOOR_WEATHER_FACTOR = 0.3

# ── 교통 접근성 ──
TR_LOW_FLOOR_BUS = 30  # 저상버스 접근 가능
TR_BUS_STOP = 20       # 가까운 버스정류장
TR_AIRPORT_NEAR = 20   # 공항과 거리 가까움
TR_PARKING = 20        # 장애인 주차장
TR_LOW_INTERNAL = 10   # 관광지 내부 이동 부담 낮음

# ── 공항 출도 부담 ──
BURDEN_DEP_UNDER_2H = 50
BURDEN_DEP_UNDER_3H = 30
BURDEN_FAR = 20
BURDEN_WEATHER = 20

# ── 거리 임계값 (km) ──
AIRPORT_NEAR_KM = 10.0
AIRPORT_FAR_KM = 15.0
AIRPORT_DIST_NORM_KM = 40.0  # 공항 근접/부담 점수를 연속 정규화하는 기준 거리

# ── 자연어 질의 추천 ──
QUERY_RELEVANCE_WEIGHT = 0.35  # 결합 랭킹에서 질의 관련도 비중 (나머지는 이동가능성)
QUERY_TOP_K_DOCS = 40          # 질의당 검색할 무장애 문서 수

# ── 이동가능성 가중치 & 분류 임계값 ──
W_ACCESSIBILITY = 0.45
W_TRANSPORT = 0.25
W_WEATHER = 0.20
W_AIRPORT = 0.10
# 양수 기여분 최대치( = 0.45*100 + 0.25*100 = 70 )로 나눠 0~100 스케일로 정규화한다.
# 이렇게 하지 않으면 mobility 최대값이 ~70 에 그쳐 recommended(75+) 등급이 뜨지 않는다.
MOBILITY_SCALE = W_ACCESSIBILITY * 100 + W_TRANSPORT * 100
LEVEL_RECOMMENDED = 75   # 이상: 추천
LEVEL_CONDITIONAL = 50   # 이상~미만: 조건부 추천, 미만: 비추천
