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
}: {
  rec: Recommendation;
  actionSlot?: ReactNode; // 담기 버튼 등 외부 주입 액션
  selected?: boolean; // 지도 마커 선택과 연동된 하이라이트
}) {
  const warnings = rec.warnings.filter((w) => !w.startsWith("본 추천은 참고 정보"));
  const matchReason = rec.match_reason ?? [];
  // match_reason 과 겹치는 스니펫은 중복 표시하지 않는다
  const barrierInfo = (rec.barrier_free_info ?? []).filter(
    (b) => !matchReason.some((m) => b.startsWith(m.slice(0, 40)))
  );

  const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
  const rawImg = rec.image_urls?.[0];
  // 제주 GIS 이미지는 인증서 문제로 백엔드 프록시를 통해 로드
  const heroImg = rawImg ? `${API_BASE}/api/image?url=${encodeURIComponent(rawImg)}` : undefined;

  return (
    <div
      className={`bg-white rounded-2xl border mb-3 shadow-[var(--shadow-soft)] overflow-hidden transition-shadow ${
        selected ? "border-brand-400 ring-2 ring-brand-300" : "border-brand-100"
      }`}
    >
      {heroImg && (
        <img
          src={heroImg}
          alt={`${rec.name} 로드뷰`}
          loading="lazy"
          className="w-full h-40 object-cover bg-stone-100"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      )}
      <div className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="m-0 text-lg font-bold text-stone-800">{rec.name}</h3>
            <ScoreBadge level={rec.recommendation_level} />
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
        <div className="text-right shrink-0">
          <div className={`text-3xl font-extrabold leading-none ${scoreColor(rec.recommendation_level)}`}>
            {rec.mobility_feasibility_score}
          </div>
          <div className="text-[10px] text-stone-400 mt-1">이동가능성</div>
        </div>
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
  );
}
