import { useMemo, useState } from "react";
import type { FloorMap } from "../types/airport";

const FLOOR_ORDER = ["1F", "2F", "3F", "4F"];

export default function AirportFloorMapViewer({ floorMaps }: { floorMaps: FloorMap[] }) {
  const floors = useMemo(
    () =>
      [...new Set(floorMaps.map((m) => m.floor))].sort(
        (a, b) => FLOOR_ORDER.indexOf(a) - FLOOR_ORDER.indexOf(b)
      ),
    [floorMaps]
  );
  const [floor, setFloor] = useState(floors[0] ?? "1F");
  const [zoom, setZoom] = useState(1);

  const imagesForFloor = floorMaps.filter((m) => m.floor === floor);
  const [imgIdx, setImgIdx] = useState(0);
  const current = imagesForFloor[Math.min(imgIdx, imagesForFloor.length - 1)];

  if (floorMaps.length === 0) return null;

  return (
    <section>
      <h2 className="text-lg font-extrabold text-stone-900 mb-2">공항 층별 도면</h2>

      {/* 층 탭 */}
      <div className="flex gap-1.5 mb-2">
        {floors.map((f) => (
          <button
            key={f}
            onClick={() => {
              setFloor(f);
              setImgIdx(0);
              setZoom(1);
            }}
            className={`px-4 py-1.5 rounded-xl text-sm font-bold border transition-colors cursor-pointer ${
              floor === f
                ? "bg-brand-500 border-brand-500 text-white"
                : "bg-white border-brand-200 text-stone-500 hover:bg-brand-50"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* 같은 층에 여러 도면(예: 2F 면세점 안내)일 때 선택 */}
      {imagesForFloor.length > 1 && (
        <div className="flex gap-1.5 mb-2">
          {imagesForFloor.map((m, i) => (
            <button
              key={m.image_url}
              onClick={() => setImgIdx(i)}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold border cursor-pointer ${
                i === imgIdx
                  ? "bg-sea-500 border-sea-500 text-white"
                  : "bg-white border-stone-200 text-stone-500"
              }`}
            >
              {m.description}
            </button>
          ))}
        </div>
      )}

      {/* 줌 컨트롤 */}
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={() => setZoom((z) => Math.max(0.5, Math.round((z - 0.25) * 100) / 100))}
          className="w-8 h-8 rounded-lg border border-brand-200 bg-white text-stone-600 font-bold cursor-pointer"
        >
          −
        </button>
        <span className="text-xs text-stone-400 w-12 text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => setZoom((z) => Math.min(3, Math.round((z + 0.25) * 100) / 100))}
          className="w-8 h-8 rounded-lg border border-brand-200 bg-white text-stone-600 font-bold cursor-pointer"
        >
          +
        </button>
        <span className="text-xs text-stone-400 ml-1">드래그(스크롤)로 이동</span>
      </div>

      {/* 도면 (스크롤로 팬) */}
      <div className="w-full h-96 overflow-auto rounded-2xl border border-brand-100 bg-white grid place-items-center">
        <img
          src={current.image_url}
          alt={current.description}
          style={{ width: `${zoom * 100}%`, maxWidth: "none" }}
          className="block"
        />
      </div>
      <p className="text-[10px] text-stone-300 mt-1">출처: {current.source}</p>
    </section>
  );
}
