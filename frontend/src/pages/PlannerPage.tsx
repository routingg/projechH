import { useEffect, useRef, useState } from "react";
import PlannerConditionBar, { type PlannerValue } from "../components/PlannerConditionBar";
import PlaceCard from "../components/PlaceCard";
import PlaceMap, { type MapMarker } from "../components/PlaceMap";
import RagExplanationBox from "../components/RagExplanationBox";
import ItineraryTimeline from "../components/ItineraryTimeline";
import AirportFlowPanel from "../components/AirportFlowPanel";
import AirportFacilityPanel from "../components/AirportFacilityPanel";
import JdcStorePanel from "../components/JdcStorePanel";
import AirportKakaoMap from "../components/AirportKakaoMap";
import { postRecommendationsFull } from "../api/recommendation";
import { postRag, toCandidatePlaces } from "../api/rag";
import { postItinerary } from "../api/itinerary";
import { postAirportPlan } from "../api/airport";
import { postRoute, type RouteResponse } from "../api/route";
import { JEJU_AIRPORT } from "../lib/kakao";
import type { Recommendation, RecommendationLevel } from "../types/place";
import type { RagResponse } from "../types/rag";
import type { Itinerary } from "../types/itinerary";
import type { AirportPlan } from "../types/airport";

const LEVEL_COLOR: Record<RecommendationLevel, string> = {
  recommended: "#16a34a",
  conditional: "#d97706",
  not_recommended: "#dc2626",
};

const TOP_N = 24;

function toMarkers(recs: Recommendation[]): MapMarker[] {
  return recs
    .filter((r) => r.lat != null && r.lon != null)
    .map((r) => ({
      id: r.place_id,
      lat: r.lat as number,
      lng: r.lon as number,
      label: `${r.name} (${r.mobility_feasibility_score})`,
      color: LEVEL_COLOR[r.recommendation_level],
    }));
}

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function PlannerPage() {
  const [conditions, setConditions] = useState<PlannerValue | null>(null);
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [queryApplied, setQueryApplied] = useState(false);
  const [rag, setRag] = useState<RagResponse | null>(null);
  const [cart, setCart] = useState<Recommendation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [airportPlan, setAirportPlan] = useState<AirportPlan | null>(null);
  const [courseRoute, setCourseRoute] = useState<RouteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [itinLoading, setItinLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [itinError, setItinError] = useState<string | null>(null);
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const top = (recs ?? []).slice(0, TOP_N);

  // 담은 코스 실도로 경로 미리보기 (마지막은 공항)
  useEffect(() => {
    if (cart.length === 0) {
      setCourseRoute(null);
      return;
    }
    const points = [
      ...cart
        .filter((c) => c.lat != null && c.lon != null)
        .map((c) => ({ lat: c.lat as number, lng: c.lon as number })),
      { lat: JEJU_AIRPORT.lat, lng: JEJU_AIRPORT.lng },
    ];
    if (points.length < 2) {
      setCourseRoute(null);
      return;
    }
    postRoute(points)
      .then(setCourseRoute)
      .catch(() => setCourseRoute(null));
  }, [cart]);

  async function handleSubmit(value: PlannerValue) {
    setLoading(true);
    setError(null);
    setRag(null);
    setSelectedId(null);
    setConditions(value);
    try {
      const result = await postRecommendationsFull({
        user_profile: value.profile,
        travel_date: value.travelDate,
        query: value.query || undefined,
      });
      setRecs(result.recommendations);
      setQueryApplied(result.query_applied);

      // 추천 근거를 RAG gateway 로 보내 자연어 설명을 받아온다 (미연결 시 mock)
      try {
        const explanation = await postRag({
          user_profile: value.profile as unknown as Record<string, unknown>,
          candidate_places: toCandidatePlaces(result.recommendations),
          airport_context: { departure_time: value.profile.departure_time },
        });
        setRag(explanation);
      } catch {
        setRag(null);
      }
    } catch {
      setError("추천 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setLoading(false);
    }
  }

  async function makeItinerary() {
    if (!conditions) return;
    setItinLoading(true);
    setItinError(null);
    try {
      const result = await postItinerary(
        conditions.profile,
        conditions.travelDate,
        cart.map((c) => c.place_id)
      );
      setItinerary(result);
      // 공항 동선도 같은 출도 시간으로 이어서 준비
      try {
        setAirportPlan(
          await postAirportPlan({
            departure_time: conditions.profile.departure_time ?? "18:30",
          })
        );
      } catch {
        setAirportPlan(null);
      }
      setTimeout(() => scrollToId("step-itinerary"), 100);
    } catch {
      setItinError("일정을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setItinLoading(false);
    }
  }

  function inCart(placeId: string): boolean {
    return cart.some((c) => c.place_id === placeId);
  }

  function toggleCart(rec: Recommendation) {
    setCart((prev) =>
      prev.some((c) => c.place_id === rec.place_id)
        ? prev.filter((c) => c.place_id !== rec.place_id)
        : [...prev, rec]
    );
  }

  function focusPlace(id: string) {
    setSelectedId(id);
    cardRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  const courseMarkers: MapMarker[] = cart
    .filter((c) => c.lat != null && c.lon != null)
    .map((c, i) => ({
      id: c.place_id,
      lat: c.lat as number,
      lng: c.lon as number,
      label: c.name,
      color: "#f4633a",
      order: i + 1,
    }));

  const steps = [
    { id: "step-conditions", label: "① 조건·질문", done: conditions !== null },
    { id: "step-recs", label: "② 지도에서 추천", done: (recs?.length ?? 0) > 0 },
    {
      id: "step-course",
      label: `③ 코스 담기${cart.length ? ` (${cart.length})` : ""}`,
      done: cart.length > 0,
    },
    { id: "step-itinerary", label: "④ 하루 일정", done: itinerary !== null },
    { id: "step-airport", label: "⑤ 공항 동선", done: airportPlan !== null },
  ];

  return (
    <div>
      <h1 className="text-2xl font-extrabold text-stone-900 mb-1">여행 플래너</h1>
      <p className="text-sm text-stone-400 mt-0 mb-4">
        질문 한 번으로 추천부터 일정·공항 동선까지 한 화면에서 준비하세요.
      </p>

      {/* 진행 단계 */}
      <div className="sticky top-16 z-10 -mx-4 sm:-mx-6 px-4 sm:px-6 py-2 bg-[#fdfaf7]/90 backdrop-blur-sm border-b border-brand-100 mb-4">
        <div className="flex gap-1.5 overflow-x-auto">
          {steps.map((s) => (
            <button
              type="button"
              key={s.id}
              onClick={() => scrollToId(s.id)}
              className={`px-3 py-1 rounded-full text-xs font-bold whitespace-nowrap cursor-pointer transition-colors ${
                s.done
                  ? "bg-brand-500 text-white"
                  : "bg-white border border-brand-100 text-stone-400 hover:text-brand-500"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div id="step-conditions">
        <PlannerConditionBar onSubmit={handleSubmit} loading={loading} />
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-600 text-sm p-4 mb-4">
          {error}
        </div>
      )}

      {/* ② 지도 추천 */}
      {recs && recs.length > 0 && (
        <section id="step-recs" className="scroll-mt-28">
          {conditions?.query && (
            <p className="text-xs text-stone-500 mb-2">
              {queryApplied ? (
                <>
                  🔍 "<span className="font-semibold">{conditions.query}</span>" 와 관련된 무장애
                  정보를 랭킹에 반영했어요.
                </>
              ) : (
                <>질문과 직접 관련된 무장애 문서를 찾지 못해 기본 순위로 보여드려요.</>
              )}
            </p>
          )}

          <PlaceMap
            markers={toMarkers(top)}
            showLegend
            height="26rem"
            selectedId={selectedId}
            onMarkerClick={focusPlace}
          />

          <p className="text-xs text-stone-400 mb-2 mt-3">
            총 {recs.length}곳 중 상위 {top.length}곳 · 마음에 드는 곳을 "코스에 담기"로
            모아 일정을 만들 수 있어요
          </p>

          {top.map((rec) => (
            <div
              key={rec.place_id}
              ref={(el) => {
                cardRefs.current[rec.place_id] = el;
              }}
              onClick={() => setSelectedId(rec.place_id)}
            >
              <PlaceCard
                rec={rec}
                selected={selectedId === rec.place_id}
                actionSlot={
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleCart(rec);
                    }}
                    className={`w-full sm:w-auto px-4 py-2 rounded-xl text-sm font-bold border transition-colors cursor-pointer ${
                      inCart(rec.place_id)
                        ? "bg-sea-500 border-sea-500 text-white hover:bg-sea-600"
                        : "bg-white border-brand-300 text-brand-600 hover:bg-brand-50"
                    }`}
                  >
                    {inCart(rec.place_id) ? "✓ 코스에 담김 (누르면 빼기)" : "➕ 코스에 담기"}
                  </button>
                }
              />
            </div>
          ))}

          {rag && <RagExplanationBox rag={rag} />}

          <p className="text-xs text-stone-400 mt-4">
            ※ 본 추천은 참고 정보이며 휠체어 접근 가능성이나 안전을 보장하지 않습니다. 확인되지
            않은 정보는 "정보 없음"으로 표시됩니다.
          </p>
        </section>
      )}

      {/* ③ 담은 코스 → 일정 만들기 */}
      {recs && recs.length > 0 && (
        <section id="step-course" className="scroll-mt-28 mt-8">
          <h2 className="text-lg font-extrabold text-stone-800 mb-2">
            ③ 담은 코스 {cart.length > 0 ? `${cart.length}곳` : ""}
          </h2>
          {cart.length > 0 ? (
            <>
              <PlaceMap
                markers={courseMarkers}
                connect
                routePath={courseRoute?.source === "kakao" ? courseRoute.path : undefined}
                showAirport
                height="20rem"
              />
              <p className="text-[11px] text-stone-400 mt-1 mb-3">
                숫자 = 담은 순서 · ✈ = 공항
                {courseRoute?.source === "kakao" && courseRoute.distance_m != null && (
                  <span className="text-brand-500 font-semibold">
                    {" "}
                    · 총 이동 {(courseRoute.distance_m / 1000).toFixed(1)}km ·{" "}
                    {Math.round((courseRoute.duration_s ?? 0) / 60)}분 (실도로)
                  </span>
                )}
              </p>
              <ol className="m-0 mb-3 pl-0 list-none space-y-1.5">
                {cart.map((c, i) => (
                  <li
                    key={c.place_id}
                    className="flex items-center gap-2 bg-white rounded-xl border border-brand-100 px-3 py-2"
                  >
                    <span className="grid place-items-center w-6 h-6 rounded-full bg-brand-500 text-white text-xs font-extrabold shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-sm font-semibold text-stone-700 flex-1 min-w-0 truncate">
                      {c.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => toggleCart(c)}
                      className="text-xs font-semibold text-stone-400 hover:text-red-500 cursor-pointer shrink-0"
                    >
                      빼기
                    </button>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <p className="text-sm text-stone-400 mb-3">
              아직 담은 곳이 없어요. 담지 않고 일정을 만들면 오늘 조건에 맞춰 자동으로
              배치해 드려요.
            </p>
          )}
          <button
            type="button"
            onClick={makeItinerary}
            disabled={itinLoading || !conditions}
            className="px-6 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white font-bold text-sm transition-colors cursor-pointer"
          >
            {itinLoading
              ? "일정 만드는 중…"
              : itinerary
                ? "📅 이 코스로 일정 다시 만들기"
                : "📅 이 코스로 하루 일정 만들기"}
          </button>
          {itinError && (
            <div className="rounded-2xl border border-red-200 bg-red-50 text-red-600 text-sm p-4 mt-3">
              {itinError}
            </div>
          )}
        </section>
      )}

      {/* ④ 하루 일정 */}
      {itinerary && (
        <section id="step-itinerary" className="scroll-mt-28 mt-8">
          <h2 className="text-lg font-extrabold text-stone-800 mb-2">④ 하루 일정</h2>
          <ItineraryTimeline itinerary={itinerary} />
        </section>
      )}

      {/* ⑤ 공항 출도 동선 — 실내는 도면, 카카오맵은 보조 */}
      {airportPlan && (
        <section id="step-airport" className="scroll-mt-28 mt-8">
          <h2 className="text-lg font-extrabold text-stone-800 mb-2">⑤ 공항 출도 동선</h2>
          <AirportFlowPanel
            arrivalTime={airportPlan.recommended_airport_arrival_time}
            reason={airportPlan.reason}
            floorMaps={airportPlan.airport_floor_maps}
          />

          {/* 공항 내부는 카카오맵에 없으므로 위 층별 도면이 기본, 외부 지도는 접힘 */}
          <details className="group mb-6">
            <summary className="cursor-pointer list-none text-xs font-semibold text-brand-500 hover:text-brand-600 select-none">
              🚗 공항까지 가는 길 보기 (카카오맵·로드뷰){" "}
              <span className="inline-block transition-transform group-open:rotate-180">▾</span>
            </summary>
            <div className="mt-3">
              <AirportKakaoMap />
            </div>
          </details>

          <AirportFacilityPanel facilities={airportPlan.airport_facilities} />
          <JdcStorePanel stores={airportPlan.jdc_stores} />

          {/* 주의사항 — 접기 (삭제 금지 고지) */}
          <details className="group mt-6">
            <summary className="cursor-pointer list-none text-xs font-semibold text-stone-400 hover:text-stone-500 select-none">
              이용 시 주의사항{" "}
              <span className="inline-block transition-transform group-open:rotate-180">▾</span>
            </summary>
            <ul className="mt-2 mb-0 pl-4 space-y-0.5 text-xs text-stone-400">
              {airportPlan.cautions.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </details>
        </section>
      )}

      {/* 담은 코스 요약 (하단 고정) */}
      {cart.length > 0 && (
        <div className="sticky bottom-3 z-10 mt-4">
          <div className="bg-white/95 backdrop-blur border border-brand-200 rounded-2xl shadow-[var(--shadow-lift)] px-4 py-3 flex items-center gap-3 flex-wrap">
            <span className="text-sm font-extrabold text-stone-700">
              🧺 담은 코스 {cart.length}곳
            </span>
            <span className="text-xs text-stone-400 flex-1 min-w-0 truncate">
              {cart.map((c) => c.name).join(" → ")}
            </span>
            <button
              type="button"
              onClick={() => scrollToId("step-course")}
              className="px-3 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-xs font-bold cursor-pointer"
            >
              코스 보기
            </button>
            <button
              type="button"
              onClick={() => setCart([])}
              className="text-xs font-semibold text-stone-400 hover:text-red-500 cursor-pointer"
            >
              비우기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
