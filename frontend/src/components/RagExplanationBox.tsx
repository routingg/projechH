import type { RagResponse } from "../types/rag";

function Row({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <div className="text-xs font-bold text-brand-500">{label}</div>
      <div className="text-sm text-stone-600 mt-0.5">{text}</div>
    </div>
  );
}

export default function RagExplanationBox({ rag }: { rag: RagResponse }) {
  return (
    <div className="rounded-2xl border border-brand-100 bg-gradient-to-br from-brand-50 to-sea-50 p-5 mb-4 shadow-[var(--shadow-soft)]">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">🤖</span>
          <span className="font-bold text-stone-800">AI 추천 요약</span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/70 text-stone-400 font-semibold">
          {rag.source === "mock" ? "기본 설명" : "RAG 분석"}
        </span>
      </div>

      <p className="mt-2 mb-0 font-semibold text-stone-700 leading-relaxed">{rag.summary}</p>

      <details className="mt-3 group">
        <summary className="cursor-pointer list-none text-xs font-semibold text-brand-500 hover:text-brand-600 select-none">
          상세 설명 보기 <span className="inline-block transition-transform group-open:rotate-180">▾</span>
        </summary>
        <div className="mt-3 space-y-3">
          <Row label="추천 이유" text={rag.recommended_itinerary_reason} />
          <Row label="위험 설명" text={rag.risk_explanation} />
          <Row label="공항 동선" text={rag.airport_guidance} />
          <ul className="m-0 pl-4 space-y-0.5 text-xs text-stone-500">
            {rag.cautions.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      </details>
    </div>
  );
}
