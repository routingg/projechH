import { useEffect, useRef, useState } from "react";
import { JEJU_AIRPORT, KAKAO_KEY, loadKakaoSdk } from "../lib/kakao";

export interface MapMarker {
  id?: string; // place_id — 클릭 연동용
  lat: number;
  lng: number;
  label: string;
  color?: string; // 마커 색 (등급 등)
  order?: number; // 숫자 마커 (일정 순서)
}

const LEVEL_HINT = "🟢 추천  🟠 조건부  🔴 비추천 · 마커를 누르면 해당 카드로 이동해요";

function pinEl(color: string, order?: number, selected = false): HTMLDivElement {
  const el = document.createElement("div");
  const size = selected ? 32 : 24;
  el.style.cssText =
    `display:flex;align-items:center;justify-content:center;` +
    `width:${size}px;height:${size}px;border-radius:50%;background:${color};` +
    `border:${selected ? 3 : 2}px solid #fff;` +
    `box-shadow:0 1px ${selected ? 8 : 4}px rgba(0,0,0,.4);cursor:pointer;` +
    `color:#fff;font-weight:800;font-size:12px;`;
  if (order != null) el.textContent = String(order);
  return el;
}

export default function PlaceMap({
  markers,
  connect = false,
  routePath,
  showAirport = true,
  showLegend = false,
  height = "18rem",
  selectedId = null,
  onMarkerClick,
}: {
  markers: MapMarker[];
  connect?: boolean; // order 순서대로 직선 연결 (일정 동선)
  routePath?: { lat: number; lng: number }[]; // 실도로 경로 (있으면 직선 대신 이걸 그림)
  showAirport?: boolean;
  showLegend?: boolean;
  height?: string;
  selectedId?: string | null; // 강조할 마커 id
  onMarkerClick?: (id: string) => void;
}) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const [map, setMap] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const clickRef = useRef(onMarkerClick);
  clickRef.current = onMarkerClick;
  const drawnRef = useRef<any[]>([]); // 오버레이·폴리라인 (갱신 시 제거)
  const infoRef = useRef<any>(null); // 열려 있는 InfoWindow
  const boundsKeyRef = useRef("");

  const pts = markers.filter((m) => m.lat && m.lng);
  const hasPts = pts.length > 0;

  // 지도 생성은 컨테이너당 1회 — 마커/선택 변경 시 지도를 재생성하지 않는다 (깜빡임 방지)
  useEffect(() => {
    if (!KAKAO_KEY) {
      setError("no-key");
      return;
    }
    if (!container) return;
    let cancelled = false;
    loadKakaoSdk()
      .then((kakao) => {
        if (cancelled) return;
        const center = new kakao.maps.LatLng(JEJU_AIRPORT.lat, JEJU_AIRPORT.lng);
        const mp = new kakao.maps.Map(container, { center, level: 8 });
        kakao.maps.event.addListener(mp, "click", () => infoRef.current?.close());
        drawnRef.current = [];
        boundsKeyRef.current = "";
        setMap(mp);
      })
      .catch((e) => setError(e.message === "no-key" ? "no-key" : "load-fail"));
    return () => {
      cancelled = true;
    };
  }, [container]);

  // 오버레이·경로 갱신 (지도는 유지)
  useEffect(() => {
    if (!map) return;
    const kakao = (window as any).kakao;
    drawnRef.current.forEach((o) => o.setMap(null));
    drawnRef.current = [];
    infoRef.current?.close();

    const bounds = new kakao.maps.LatLngBounds();

    pts.forEach((m) => {
      const pos = new kakao.maps.LatLng(m.lat, m.lng);
      bounds.extend(pos);
      const selected = m.id != null && m.id === selectedId;
      const el = pinEl(m.color ?? "#f4633a", m.order, selected);
      el.addEventListener("click", () => {
        if (m.id) clickRef.current?.(m.id);
        infoRef.current?.close();
        const iw = new kakao.maps.InfoWindow({
          position: pos,
          content: `<div style="padding:4px 8px;font-size:12px;white-space:nowrap;">${m.label}</div>`,
        });
        iw.open(map);
        infoRef.current = iw;
      });
      drawnRef.current.push(
        new kakao.maps.CustomOverlay({
          map,
          position: pos,
          content: el,
          yAnchor: 0.5,
          zIndex: selected ? 10 : 1,
        })
      );
    });

    if (showAirport) {
      const ap = new kakao.maps.LatLng(JEJU_AIRPORT.lat, JEJU_AIRPORT.lng);
      bounds.extend(ap);
      drawnRef.current.push(
        new kakao.maps.CustomOverlay({
          map,
          position: ap,
          content:
            '<div style="padding:2px 8px;background:#0d9488;color:#fff;border-radius:999px;font-size:11px;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.35);">✈ 공항</div>',
          yAnchor: 0.5,
        })
      );
    }

    if (routePath && routePath.length > 1) {
      // 실도로 경로 (실선)
      const path = routePath.map((p) => new kakao.maps.LatLng(p.lat, p.lng));
      path.forEach((ll: any) => bounds.extend(ll));
      drawnRef.current.push(
        new kakao.maps.Polyline({
          map,
          path,
          strokeWeight: 4,
          strokeColor: "#f4633a",
          strokeOpacity: 0.9,
          strokeStyle: "solid",
        })
      );
    } else if (connect && pts.length > 1) {
      // 실도로 경로가 없을 때 직선(점선)
      const path = [...pts]
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
        .map((m) => new kakao.maps.LatLng(m.lat, m.lng));
      if (showAirport) path.push(new kakao.maps.LatLng(JEJU_AIRPORT.lat, JEJU_AIRPORT.lng));
      drawnRef.current.push(
        new kakao.maps.Polyline({
          map,
          path,
          strokeWeight: 3,
          strokeColor: "#f4633a",
          strokeOpacity: 0.8,
          strokeStyle: "shortdash",
        })
      );
    }

    // 마커 구성이 바뀐 경우에만 화면 범위 재조정 (선택 변경만으로는 시점 유지)
    const key =
      pts.map((m) => `${m.lat},${m.lng}`).join("|") + `#${routePath?.length ?? 0}`;
    if (hasPts && key !== boundsKeyRef.current) {
      boundsKeyRef.current = key;
      map.setBounds(bounds);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, markers, connect, routePath, showAirport, selectedId]);

  // 카드에서 선택하면 해당 마커로 지도 이동
  useEffect(() => {
    if (!map || !selectedId) return;
    const kakao = (window as any).kakao;
    const m = pts.find((x) => x.id === selectedId);
    if (m) map.panTo(new kakao.maps.LatLng(m.lat, m.lng));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, selectedId]);

  if (error === "no-key") return null; // 키 없으면 지도 생략
  if (!hasPts) return null;

  return (
    <div>
      <div
        ref={setContainer}
        style={{ height }}
        className="w-full rounded-2xl overflow-hidden border border-brand-100 bg-stone-100"
      />
      {showLegend && <p className="text-[11px] text-stone-400 mt-1">{LEVEL_HINT}</p>}
      {error === "load-fail" && (
        <p className="text-xs text-red-500 mt-1">지도를 불러오지 못했습니다.</p>
      )}
    </div>
  );
}
