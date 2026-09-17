import type { FloorMap } from "../types/airport";
import AirportFloorMapViewer from "./AirportFloorMapViewer";

export default function AirportFlowPanel({
  arrivalTime,
  reason,
  floorMaps,
}: {
  arrivalTime: string | null;
  reason: string;
  floorMaps: FloorMap[];
}) {
  return (
    <section>
      {/* 도착 권장 시간 — 히어로 카드 */}
      <div className="rounded-3xl bg-gradient-to-r from-sea-600 to-sea-500 px-6 py-7 text-center shadow-[var(--shadow-soft)] mb-6">
        <div className="text-xs font-bold text-white/70 tracking-wide">공항 도착 권장 시간</div>
        <div className="text-5xl font-extrabold text-white mt-1 tracking-tight">
          {arrivalTime ?? "-"}
        </div>
        <p className="m-0 mt-2 text-xs text-white/80 max-w-md mx-auto">{reason}</p>
      </div>

      {/* 실제 층별 도면 뷰어 (탭 + 줌) */}
      <AirportFloorMapViewer floorMaps={floorMaps} />
    </section>
  );
}
