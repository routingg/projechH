import type { AirportFacility } from "../types/airport";

const CATEGORY_ICON: Record<string, string> = {
  식음료: "🍽️",
  금융: "🏦",
  안내: "ℹ️",
  판매: "🛍️",
  면세점: "🛒",
  라운지: "🛋️",
  기타서비스: "🔧",
  편의점: "🏪",
  카페: "☕",
};

export default function AirportFacilityPanel({
  facilities,
}: {
  facilities: AirportFacility[];
}) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-extrabold text-stone-900 mb-1">체류 가능 시설</h2>
      <p className="text-xs text-stone-400 mt-0 mb-3">
        출도 전 이용할 수 있는 공항 내 시설이에요.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {facilities.map((f, i) => (
          <div
            key={i}
            className="flex items-center gap-3 bg-white rounded-2xl border border-brand-100 p-3.5 shadow-[var(--shadow-soft)]"
          >
            <span className="text-2xl">{CATEGORY_ICON[f.category] ?? "📍"}</span>
            <div className="min-w-0">
              <div className="font-bold text-sm text-stone-800 truncate">{f.facility_name}</div>
              <div className="text-[11px] text-stone-400">
                {f.terminal} {f.floor} · {f.category}
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-stone-300 mt-2">
        출처: 한국공항공사 제주공항 층별 입점업체 현황
      </p>
    </section>
  );
}
