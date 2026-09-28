import type { ReactNode } from "react";
import type { PlaceFacts, Recommendation } from "../types/place";
import ScoreBadge from "./ScoreBadge";

const FACT_LABELS: Record<keyof PlaceFacts, string> = {
  has_accessible_parking: "주차장",
  has_accessible_toilet: "화장실",
  has_wheelchair_rental: "휠체어 대여",
  is_indoor: "실내",
};

function factChip(value: boolean | null): { mark: string; cls: string } {
  if (value === true) return { mark: "✓", cls: "bg-green-50 text-green-700 border-green-200" };
  if (value === false) return { mark: "✕", cls: "bg-red-50 text-red-500 border-red-200" };
  return { mark: "?", cls: "bg-stone-50 text-stone-400 border-stone-200" };
}

function scoreColor(level: Recommendation["recommendation_level"]): string {
  if (level === "recommended") return "text-green-600";
  if (level === "conditional") return "text-amber-600";
  return "text-red-500";
}

const LEVEL_BAR_COLOR: Record<Recommendation["recommendation_level"], string> = {
  recommended: "bg-green-500",
  conditional: "bg-amber-500",
  not_recommended: "bg-red-500",
};

function MiniBar({ label, value, inverted = false }: { label: string; value: number; inverted?: boolean }) {
  const good = inverted ? value <= 30 : value >= 60;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 shrink-0 text-stone-400">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden">
        <div
          className={`h-full rounded-full ${good ? "bg-sea-500" : "bg-brand-400"}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="w-7 text-right font-semibold text-stone-600">{value}</span>
    </div>
  );
}

export default function PlaceCard({
  rec,
  actionSlot,
  selected = false,
  animationDelayMs = 0,
}: {
  rec: Recommendation;
  actionSlot?: ReactNode; // 담기 버튼 등 외부 주입 액션
  selected?: boolean; // 지도 마커 선택과 연동된 하이라이트
  animationDelayMs?: number; // 목록에 순차적으로 나타나는 효과용
}) {
  const warnings = rec.warnings.filter((w) => !w.startsWith("본 추천은 참고 정보"));
  const matchReason = rec.match_reason ?? [];
  // match_reason 과 겹치는 스니펫은 중복 표시하지 않는다
  const barrierInfo = (rec.barrier_free_info ?? []).filter(
    (b) => !matchReason.some((m) => b.startsWith(m.slice(0, 40)))
  );

  const rawImg = rec.image_urls?.[0];
  // 제주 GIS 로드뷰 사진은 scripts/download_place_images.py 로 미리 받아
  // frontend/public 에 정적 파일로 저장해 둔다 (원본 도메인 인증서 문제 +
  // Render 무료 플랜 cold-start로 인한 프록시 502/503을 피하기 위함).
  // 원본 URL의 도메인 이후 경로를 그대로 정적 파일 경로로 사용한다.
  const heroImg = rawImg ? new URL(rawImg).pathname : undefined;

  return (
    <div
      style={{ animationDelay: `${animationDelayMs}ms` }}
      className={`animate-fade-in-up bg-white rounded-2xl border mb-3 shadow-[var(--shadow-soft)] overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[var(--shadow-lift)] ${
        selected ? "border-brand-400 ring-2 ring-brand-300" : "border-brand-100"
      }`}
    >
      <div aria-hidden className={`h-1 ${LEVEL_BAR_COLOR[rec.recommendation_level]}`} />
      {/* 데스크톱: 이미지 좌측 고정폭 + 정보 우측 / 모바일: 이미지 상단 전체폭 */}
      <div className="sm:flex sm:items-stretch">
        <div className="relative shrink-0 w-full h-40 sm:w-52 sm:h-auto">
          {heroImg ? (
            <img
              src={heroImg}
              alt={`${rec.name} 로드뷰`}
              loading="lazy"
              className="w-full h-full object-cover bg-stone-100"
              onError={(e) => {
                e.currentTarget.style.display = "none";
                e.currentTarget.parentElement
                  ?.querySelector("[data-img-fallback]")
                  ?.classList.remove("hidden");
              }}
            />
          ) : null}
          <div
            data-img-fallback
            className={`w-full h-full grid place-items-center bg-gradient-to-br from-brand-50 to-sea-50 text-4xl ${
              heroImg ? "hidden" : ""
            }`}
            aria-hidden
          >
            {rec.category === "indoor" ? "🏛" : "🌿"}
          </div>
          {/* 접근성 판단 결과 — 사진보다 먼저 읽히도록 오버레이로 표시 */}
          <div className="absolute inset-x-2 top-2 flex items-start justify-between gap-2">
            <ScoreBadge level={rec.recommendation_level} />
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/95 shadow-sm text-xs font-extrabold ${scoreColor(rec.recommendation_level)}`}
            >
              {rec.mobility_feasibility_score}점
            </span>
          </div>
        </div>
        <div className="p-5 flex-1 min-w-0">
      <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="m-0 text-lg font-bold text-stone-800">{rec.name}</h3>
            {rec.relevance_score != null && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-sea-50 text-sea-600 border border-sea-100 font-bold">
                질문 관련도 {rec.relevance_score}%
              </span>
            )}
          </div>
          <p className="m-0 mt-1 text-xs text-stone-400">
            {rec.category === "indoor" ? "🏛 실내" : "🌿 실외"}
            {rec.address ? ` · ${rec.address}` : ""}
          </p>
      </div>

      {/* 사실 칩 — 정보 없음(?)도 그대로 표기 */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        {(Object.keys(FACT_LABELS) as (keyof PlaceFacts)[]).map((key) => {
          const c = factChip(rec.facts[key]);
          return (
            <span
              key={key}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border text-xs font-medium ${c.cls}`}
            >
              <span>{c.mark}</span>
              {FACT_LABELS[key]}
              {rec.facts[key] === null && <span className="font-normal">(정보 없음)</span>}
            </span>
          );
        })}
      </div>

      {matchReason.length > 0 && (
        <div className="mt-3 rounded-xl bg-sea-50 border border-sea-100 p-3">
          <p className="m-0 text-[11px] font-bold text-sea-600">질문과 관련된 무장애 정보</p>
          <ul className="m-0 mt-1 pl-4 space-y-0.5 text-xs text-stone-600">
            {matchReason.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      <details className="mt-3 group">
        <summary className="cursor-pointer list-none text-xs font-semibold text-brand-500 hover:text-brand-600 select-none">
          자세히 보기 <span className="inline-block transition-transform group-open:rotate-180">▾</span>
        </summary>
        <div className="mt-3 space-y-1.5">
          <MiniBar label="접근성" value={rec.accessibility_score} />
          <MiniBar label="교통" value={rec.transport_score} />
          <MiniBar label="날씨 위험" value={rec.weather_risk_score} inverted />
          <MiniBar label="공항 부담" value={rec.airport_burden_score} inverted />
        </div>
        {barrierInfo.length > 0 && (
          <div className="mt-3">
            <p className="m-0 text-xs font-bold text-stone-500">무장애 상세 정보</p>
            <ul className="m-0 mt-1 pl-4 space-y-0.5 text-xs text-stone-500">
              {barrierInfo.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
            <p className="m-0 mt-1 text-[10px] text-stone-300">
              출처: 제주데이터허브 무장애여행정보
            </p>
          </div>
        )}
        {warnings.length > 0 && (
          <ul className="mt-3 mb-0 pl-4 space-y-0.5 text-xs text-stone-500">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        )}
      </details>

      {actionSlot && <div className="mt-3">{actionSlot}</div>}
      </div>
      </div>
    </div>
  );
}
