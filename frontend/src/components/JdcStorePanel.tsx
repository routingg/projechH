import { useMemo, useState } from "react";
import type { JdcStore } from "../types/airport";

// 판매품목별 아이콘 (실데이터 category = POS_BRAN_NM)
const CATEGORY_ICON: Record<string, string> = {
  화장품: "💄",
  향수: "🌸",
  주류: "🍶",
  담배: "🚬",
  "핸드백/지갑/밸트": "👜",
  선글라스: "🕶️",
  액세서리: "💍",
  시계: "⌚",
  완구류: "🧸",
  과자류: "🍫",
  인삼류: "🌿",
  라이터: "🔥",
  "문구류/미용기기": "✏️",
  기타: "🛍️",
};

function icon(cat?: string | null) {
  return (cat && CATEGORY_ICON[cat]) || "🛍️";
}

export default function JdcStorePanel({
  stores,
  dataLimitations,
}: {
  stores: JdcStore[];
  dataLimitations?: string[];
}) {
  const [category, setCategory] = useState<string>("전체");
  const [query, setQuery] = useState("");

  // 카테고리별 개수 (많은 순)
  const categories = useMemo(() => {
    const counts = new Map<string, number>();
    for (const s of stores) {
      const c = s.category || "기타";
      counts.set(c, (counts.get(c) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [stores]);

  const filtered = useMemo(() => {
    const q = query.trim();
    return stores.filter(
      (s) =>
        (category === "전체" || (s.category || "기타") === category) &&
        (q === "" || s.store_name.includes(q))
    );
  }, [stores, category, query]);

  if (stores.length === 0) return null;

  const limits =
    dataLimitations ??
    Array.from(new Set(stores.map((s) => s.data_limit).filter((d): d is string => !!d)));

  return (
    <section className="mt-8">
      <h2 className="text-lg font-extrabold text-stone-900 mb-1">JDC 면세점</h2>
      <p className="text-xs text-stone-400 mt-0 mb-3">
        출도 전 이용 가능한 면세점 매장이에요. (매장정보 안내 전용)
      </p>

      {/* 검색 */}
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="브랜드 검색 (예: 샤넬, 정관장)"
        className="w-full px-3 py-2 mb-3 rounded-xl border border-brand-100 bg-white text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-brand-300"
      />

      {/* 카테고리 필터 칩 */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <button
          onClick={() => setCategory("전체")}
          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
            category === "전체"
              ? "bg-brand-500 border-brand-500 text-white"
              : "bg-white border-brand-200 text-stone-500 hover:bg-brand-50"
          }`}
        >
          전체 {stores.length}
        </button>
        {categories.map(([cat, n]) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
              category === cat
                ? "bg-brand-500 border-brand-500 text-white"
                : "bg-white border-brand-200 text-stone-500 hover:bg-brand-50"
            }`}
          >
            {icon(cat)} {cat} {n}
          </button>
        ))}
      </div>

      <p className="text-xs text-stone-400 mb-2">{filtered.length}개 매장</p>

      <div className="grid sm:grid-cols-2 gap-3">
        {filtered.map((s, i) => (
          <div
            key={i}
            className="bg-white rounded-2xl border border-brand-100 p-4 shadow-[var(--shadow-soft)]"
          >
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm text-stone-800">
                {icon(s.category)} {s.store_name}
              </strong>
              {s.category && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-brand-50 text-brand-600 font-bold shrink-0">
                  {s.category}
                </span>
              )}
            </div>
            <div className="mt-2 space-y-1 text-xs text-stone-500">
              <div>📍 {s.location}</div>
              {(s.open_time || s.close_time) && (
                <div>
                  🕒 {s.open_time ?? "-"} ~ {s.close_time ?? "-"}
                </div>
              )}
              {s.phone && <div>☎ {s.phone}</div>}
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="text-sm text-stone-400 py-6 text-center">검색 결과가 없어요.</p>
      )}

      {/* JDC 데이터 한계 — 접기 (삭제 금지 고지) */}
      <details className="group mt-3">
        <summary className="cursor-pointer list-none text-xs font-semibold text-stone-400 hover:text-stone-500 select-none">
          JDC 데이터 한계 보기{" "}
          <span className="inline-block transition-transform group-open:rotate-180">▾</span>
        </summary>
        <ul className="mt-2 mb-0 pl-4 space-y-0.5 text-xs text-stone-400">
          {limits.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
          <li>출처: JDC 제주국제공항 면세점 매장정보 API</li>
        </ul>
      </details>
    </section>
  );
}
