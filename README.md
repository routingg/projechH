# WheelTrip Jeju (ProjectH)

휠체어 이용자·이동약자의 제주 여행을 위한 **당일 이동가능성 예측 + 출도 전 공항 동선 안내** AI 서비스.

단순 무장애 관광지 목록이 아니라, 무장애 관광정보 · 기상청 예보/특보 · 저상버스 · 한국공항공사 공항 도면/입점업체 · JDC 면세점 매장정보를 결합하여
"오늘 실제로 이동 가능한 일정"과 "출도 전 공항 내 이동·체류 동선"을 추천한다.

## 구조

```
backend/   FastAPI 서버 (점수화·추천·일정재구성·공항동선·JDC·RAG gateway)
frontend/  React + Vite + TypeScript
docs/      데이터 출처 문서
```

## 개발 환경

conda 환경 `projecth` (Python 3.11 + Node.js) 사용.

```bash
conda create -n projecth python=3.11 nodejs
conda activate projecth
```

### 백엔드 실행

```bash
conda activate projecth
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
# http://localhost:8000/docs
```

### 프론트엔드 실행

```bash
conda activate projecth
cd frontend
npm install
npm run dev
# http://localhost:5173
```

## 범위

- Claude Code 담당: 백엔드/프론트/데이터 전처리/점수화/추천/일정재구성/공항동선/JDC/RAG 연동 gateway
- RAG(LLM 추천 설명)는 별도 팀원 담당. 백엔드는 `/api/rag/recommend` gateway로 연결만 하며, 미연결 시 mock 설명을 반환한다.

## 주의

- 추천 결과는 **참고 정보**이며 휠체어 접근 가능성이나 안전을 보장하지 않는다.
- 데이터에서 확인되지 않은 정보는 "정보 없음"으로 표시한다.
- JDC 데이터는 **면세점 매장정보 안내에만** 사용한다. 공항 편의시설/동선은 한국공항공사 데이터를 사용한다.
