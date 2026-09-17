import type { RecommendationLevel } from "../types/place";

const STYLES: Record<RecommendationLevel, { label: string; cls: string }> = {
  recommended: { label: "추천", cls: "bg-green-100 text-green-700" },
  conditional: { label: "조건부 추천", cls: "bg-amber-100 text-amber-700" },
  not_recommended: { label: "비추천", cls: "bg-red-100 text-red-600" },
};

export default function ScoreBadge({ level }: { level: RecommendationLevel }) {
  const s = STYLES[level];
  return (
    <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold ${s.cls}`}>
      {s.label}
    </span>
  );
}
