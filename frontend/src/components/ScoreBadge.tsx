import type { RecommendationLevel } from "../types/place";

const STYLES: Record<RecommendationLevel, { label: string; icon: string; cls: string }> = {
  recommended: { label: "추천", icon: "✓", cls: "bg-green-100 text-green-700" },
  conditional: { label: "조건부 추천", icon: "△", cls: "bg-amber-100 text-amber-700" },
  not_recommended: { label: "비추천", icon: "✕", cls: "bg-red-100 text-red-600" },
};

export default function ScoreBadge({ level }: { level: RecommendationLevel }) {
  const s = STYLES[level];
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${s.cls}`}
    >
      <span aria-hidden>{s.icon}</span>
      {s.label}
    </span>
  );
}
