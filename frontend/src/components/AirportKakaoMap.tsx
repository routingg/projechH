import { useEffect, useRef, useState } from "react";
import { JEJU_AIRPORT, KAKAO_KEY, loadKakaoSdk } from "../lib/kakao";

export default function AirportKakaoMap() {
  const mapRef = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<"map" | "roadview">("map");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!KAKAO_KEY) {
      setError("no-key");
      return;
    }
    let cancelled = false;
    loadKakaoSdk()
      .then((kakao) => {
        if (cancelled || !mapRef.current) return;
        const center = new kakao.maps.LatLng(JEJU_AIRPORT.lat, JEJU_AIRPORT.lng);
        if (mode === "map") {
          const map = new kakao.maps.Map(mapRef.current, { center, level: 3 });
          const marker = new kakao.maps.Marker({ position: center });
          marker.setMap(map);
          const info = new kakao.maps.InfoWindow({
            content:
              '<div style="padding:6px 10px;font-size:12px;font-weight:700;">✈ 제주국제공항</div>',
          });
          info.open(map, marker);
          map.addControl(
            new kakao.maps.ZoomControl(),
            kakao.maps.ControlPosition.RIGHT
          );
        } else {
          const rv = new kakao.maps.Roadview(mapRef.current);
          const rvClient = new kakao.maps.RoadviewClient();
          rvClient.getNearestPanoId(center, 50, (panoId: number | null) => {
            if (panoId) rv.setPanoId(panoId, center);
            else setError("no-roadview");
          });
        }
      })
      .catch(() => setError("load-fail"));
    return () => {
      cancelled = true;
    };
  }, [mode]);

  if (error === "no-key") {
    return (
      <div className="rounded-2xl border border-dashed border-brand-200 bg-brand-50 p-5 text-sm text-stone-500">
        <strong className="text-stone-700">카카오맵 키가 필요합니다.</strong>
        <p className="mt-1 mb-0">
          Kakao Developers에서 JavaScript 앱키를 발급받아{" "}
          <code className="text-brand-600">frontend/.env</code>에{" "}
          <code className="text-brand-600">VITE_KAKAO_MAP_KEY=키</code>를 넣고
          dev 서버를 재시작하세요.
        </p>
      </div>
    );
  }

  return (
    <section className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-extrabold text-stone-900 m-0">공항 위치 지도</h2>
        <div className="flex gap-1">
          {(["map", "roadview"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
                mode === m
                  ? "bg-brand-500 border-brand-500 text-white"
                  : "bg-white border-brand-200 text-stone-500 hover:bg-brand-50"
              }`}
            >
              {m === "map" ? "지도" : "로드뷰"}
            </button>
          ))}
        </div>
      </div>

      <div
        ref={mapRef}
        className="w-full h-72 rounded-2xl overflow-hidden border border-brand-100 bg-stone-100"
      />
      {error === "no-roadview" && (
        <p className="text-xs text-stone-400 mt-1">이 위치의 로드뷰가 없습니다.</p>
      )}
      {error === "load-fail" && (
        <p className="text-xs text-red-500 mt-1">
          지도를 불러오지 못했습니다. 카카오 앱키·도메인 등록(localhost)을 확인하세요.
        </p>
      )}

      <a
        href={`https://map.kakao.com/link/to/제주국제공항,${JEJU_AIRPORT.lat},${JEJU_AIRPORT.lng}`}
        target="_blank"
        rel="noreferrer"
        className="inline-block mt-2 px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-bold no-underline"
      >
        카카오맵으로 길찾기 →
      </a>
    </section>
  );
}
