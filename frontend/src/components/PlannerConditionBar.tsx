import { useState } from "react";
import type { UserProfile, WheelchairType, WeatherSensitivity } from "../types/user";

export interface PlannerValue {
  profile: UserProfile;
  travelDate: string;
  query: string;
}

const QUERY_EXAMPLES = [
  "휠체어로 갈만한 바다 보이는 산책로",
  "경사가 완만하고 장애인화장실 있는 곳",
  "비 와도 괜찮은 실내 전시",
  "주차 편한 무장애 여행지",
];

const PREFERRED_OPTIONS = [
  { value: "indoor", label: "🏛 실내" },
  { value: "nature", label: "🌿 자연" },
  { value: "culture", label: "🎨 문화" },
];

const inputCls =
  "px-3 py-2 rounded-xl border border-brand-100 bg-white text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-brand-300";
const labelCls = "flex flex-col gap-1 text-xs font-semibold text-stone-500";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function PlannerConditionBar({
  onSubmit,
  loading,
}: {
  onSubmit: (value: PlannerValue) => void;
  loading: boolean;
}) {
  const [query, setQuery] = useState("");
  const [travelDate, setTravelDate] = useState(today());
  const [wheelchairType, setWheelchairType] = useState<WheelchairType>("manual");
  const [departureTime, setDepartureTime] = useState("18:30");
  const [startLocation, setStartLocation] = useState("제주시 연동");
  const [hasCompanion, setHasCompanion] = useState(true);
  const [sensitivity, setSensitivity] = useState<WeatherSensitivity>("high");
  const [preferred, setPreferred] = useState<string[]>([]);
  const [gps, setGps] = useState<{ lat: number; lon: number } | null>(null);
  const [gpsStatus, setGpsStatus] = useState<"idle" | "loading" | "ok" | "fail">("idle");

  function useMyLocation() {
    if (!navigator.geolocation) {
      setGpsStatus("fail");
      return;
    }
    setGpsStatus("loading");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setGpsStatus("ok");
      },
      () => setGpsStatus("fail"),
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }

  function togglePreferred(value: string) {
    setPreferred((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  function submit(withQuery?: string) {
    const q = (withQuery ?? query).trim();
    if (withQuery !== undefined) setQuery(withQuery);
    onSubmit({
      profile: {
        start_location: startLocation,
        wheelchair_type: wheelchairType,
        has_companion: hasCompanion,
        preferred_type: preferred,
        departure_time: departureTime,
        weather_sensitivity: sensitivity,
        user_lat: gps?.lat ?? null,
        user_lon: gps?.lon ?? null,
      },
      travelDate,
      query: q,
    });
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="bg-white rounded-2xl border border-brand-100 p-5 mb-5 shadow-[var(--shadow-soft)]"
    >
      {/* 자연어 질문 */}
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-bold text-stone-500">
          어떤 상황인지, 어떤 곳에 가고 싶은지 편하게 적어주세요
        </span>
        <div className="flex gap-2">
          <textarea
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='예: "전동휠체어를 타는데 바다가 보이는 완만한 산책로에 가고 싶어요"'
            className="flex-1 px-4 py-2.5 rounded-xl border border-brand-100 bg-white text-sm text-stone-700 resize-none focus:outline-none focus:ring-2 focus:ring-brand-300"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-5 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white font-bold text-sm transition-colors cursor-pointer shrink-0"
          >
            {loading ? "분석 중…" : "추천 받기"}
          </button>
        </div>
      </label>
      <div className="flex flex-wrap gap-1.5 mt-2">
        {QUERY_EXAMPLES.map((ex) => (
          <button
            type="button"
            key={ex}
            onClick={() => submit(ex)}
            disabled={loading}
            className="px-3 py-1 rounded-full text-xs font-semibold border border-brand-200 text-stone-500 bg-white hover:bg-brand-50 cursor-pointer disabled:opacity-60"
          >
            {ex}
          </button>
        ))}
      </div>
      <p className="m-0 mt-1.5 text-[11px] text-stone-400">
        질문 없이 "추천 받기"만 눌러도 오늘 조건 기준 이동가능성 순으로 보여드려요.
      </p>

      {/* 필수 조건 한 줄 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
        <label className={labelCls}>
          여행 날짜
          <input
            type="date"
            className={inputCls}
            value={travelDate}
            onChange={(e) => setTravelDate(e.target.value)}
          />
        </label>
        <label className={labelCls}>
          휠체어 종류
          <select
            className={inputCls}
            value={wheelchairType}
            onChange={(e) => setWheelchairType(e.target.value as WheelchairType)}
          >
            <option value="manual">수동</option>
            <option value="electric">전동</option>
            <option value="unknown">미정</option>
          </select>
        </label>
        <label className={labelCls}>
          출도(비행기) 시간
          <input
            type="time"
            className={inputCls}
            value={departureTime}
            onChange={(e) => setDepartureTime(e.target.value)}
          />
        </label>
        <div className={labelCls}>
          내 위치
          <button
            type="button"
            onClick={useMyLocation}
            className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-colors cursor-pointer text-left ${
              gpsStatus === "ok"
                ? "bg-sea-500 border-sea-500 text-white"
                : "bg-white border-brand-200 text-stone-500 hover:bg-brand-50"
            }`}
          >
            📍{" "}
            {gpsStatus === "ok"
              ? "현재 위치 반영됨"
              : gpsStatus === "loading"
                ? "위치 확인 중…"
                : "현재 위치 사용"}
          </button>
        </div>
      </div>
      {gpsStatus === "fail" && (
        <p className="m-0 mt-1 text-[11px] text-stone-400">
          위치를 가져오지 못했어요 — 공항 기준 근접도로 계산합니다.
        </p>
      )}

      {/* 세부 조건 (접기) */}
      <details className="mt-3 group">
        <summary className="cursor-pointer list-none text-xs font-semibold text-stone-400 hover:text-brand-500 select-none">
          세부 조건 (동반자·날씨 민감도·선호 유형·출발지){" "}
          <span className="inline-block transition-transform group-open:rotate-180">▾</span>
        </summary>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-stone-600">
            <input
              type="checkbox"
              className="w-4 h-4 accent-brand-500"
              checked={hasCompanion}
              onChange={(e) => setHasCompanion(e.target.checked)}
            />
            동반자 있음
          </label>
          <label className="flex items-center gap-2 text-xs font-semibold text-stone-500">
            날씨 민감도
            <select
              className={inputCls}
              value={sensitivity}
              onChange={(e) => setSensitivity(e.target.value as WeatherSensitivity)}
            >
              <option value="low">낮음</option>
              <option value="normal">보통</option>
              <option value="high">높음</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs font-semibold text-stone-500">
            출발지
            <input
              className={inputCls}
              value={startLocation}
              onChange={(e) => setStartLocation(e.target.value)}
            />
          </label>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-stone-500">선호 유형</span>
            {PREFERRED_OPTIONS.map((opt) => {
              const active = preferred.includes(opt.value);
              return (
                <button
                  type="button"
                  key={opt.value}
                  onClick={() => togglePreferred(opt.value)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
                    active
                      ? "bg-brand-500 border-brand-500 text-white"
                      : "bg-white border-brand-200 text-stone-500 hover:bg-brand-50"
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      </details>
    </form>
  );
}
