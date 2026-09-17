import { Link } from "react-router-dom";

// 이용 흐름 — 플래너 지도에 그려지는 동선(관광지 → 공항) 순서 그대로
const ROUTE_STEPS = [
  {
    pin: "1",
    title: "가고 싶은 곳을 편하게 적어요",
    desc: "“바다가 보이는 완만한 산책로”처럼 문장으로 물어보면 됩니다.",
  },
  {
    pin: "2",
    title: "지도에서 갈 수 있는 곳을 확인해요",
    desc: "경사·화장실·날씨를 장소마다 점수로 계산해 지도 위에 표시합니다.",
  },
  {
    pin: "3",
    title: "마음에 드는 곳을 담아 하루 일정으로",
    desc: "담은 곳은 반드시 포함하고, 나머지는 시간대에 맞춰 채워 드립니다.",
  },
  {
    pin: "✈",
    title: "공항까지 이어서 준비해요",
    desc: "도착 권장 시간과 제주공항 1–4층 도면 동선으로 마무리합니다.",
    isAirport: true,
  },
];

// 장소마다 확인하는 것 — 서비스의 실제 판단 기준
const CHECKS = [
  {
    term: "이동가능성 점수",
    desc: "경사로·장애인화장실·주차·대중교통·공항 거리를 장소마다 하나의 점수로 정리합니다.",
  },
  {
    term: "날씨까지 반영",
    desc: "기상특보가 뜨면 실외 일정을 실내로 대체 제안하고, 공항 조기 이동을 안내합니다.",
  },
  {
    term: "확인 안 된 건 ‘정보 없음’",
    desc: "데이터로 확인되지 않은 시설은 추측하지 않습니다. 없는 사실은 지어내지 않아요.",
  },
];

export default function HomePage() {
  return (
    <div className="-mt-8 -mx-4 sm:-mx-6">
      {/* 히어로 — 안내서 표지처럼: 왼쪽은 약속, 오른쪽은 실제 표기 예시 */}
      <section className="px-4 sm:px-6 pt-14 pb-12 border-b border-brand-100">
        <div className="max-w-5xl mx-auto grid gap-10 lg:grid-cols-[1fr_minmax(0,23rem)] lg:gap-14 items-center">
          <div>
            <p className="m-0 text-base sm:text-lg font-bold text-brand-700 tracking-wide">
              휠체어 이용자를 위한 제주 여행 플래너
            </p>
            <h1 className="font-display text-[2.6rem] leading-[1.25] sm:text-6xl sm:leading-[1.2] font-bold text-stone-900 mt-4 mb-0">
              오늘, 휠체어로
              <br />갈 수 있는 제주
            </h1>
            <p className="mt-6 mb-0 text-lg sm:text-xl text-stone-700 leading-relaxed">
              경사로 각도부터 장애인화장실, 오늘의 날씨까지 공공데이터로 확인해{" "}
              <strong className="text-stone-900">갈 수 있는 곳만</strong> 추천해
              드려요. 확인되지 않은 정보는{" "}
              <strong className="text-stone-900">‘정보 없음’</strong>으로
              정직하게 표시합니다.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-4">
              <Link
                to="/planner"
                className="no-underline inline-flex items-center min-h-[3.25rem] px-8 py-3.5 rounded-2xl bg-brand-700 hover:bg-brand-600 text-white text-lg font-bold transition-colors"
              >
                여행 계획 시작하기 →
              </Link>
              <a
                href="#how"
                className="text-lg font-bold text-sea-700 underline underline-offset-4 hover:text-sea-600"
              >
                어떻게 확인하나요?
              </a>
            </div>
            <p className="mt-6 mb-0 text-base text-stone-500">
              ※ 추천 결과는 참고 정보이며 접근 가능성과 안전을 보장하지 않습니다.
            </p>
          </div>

          {/* 실데이터 표기 예시 — 서비스가 보여주는 방식 그대로 (제주도립미술관 실제 값) */}
          <aside aria-label="정보 표기 방식 예시">
            <div className="bg-white rounded-2xl border-2 border-stone-200 shadow-[var(--shadow-soft)] p-6">
              <p className="m-0 text-sm font-bold text-stone-500 tracking-wide">
                이렇게 표시해 드려요 — 실제 데이터 예시
              </p>
              <div className="mt-3 flex items-center justify-between gap-3">
                <strong className="text-xl text-stone-900">제주도립미술관</strong>
                <span className="shrink-0 px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm font-bold">
                  추천
                </span>
              </div>
              <ul className="list-none m-0 mt-4 p-0 space-y-2 text-base">
                <li className="flex items-center gap-2 text-stone-800">
                  <span aria-hidden className="grid place-items-center w-6 h-6 rounded-md bg-sea-50 text-sea-700 font-bold">✓</span>
                  장애인화장실 확인됨
                </li>
                <li className="flex items-center gap-2 text-stone-800">
                  <span aria-hidden className="grid place-items-center w-6 h-6 rounded-md bg-sea-50 text-sea-700 font-bold">✓</span>
                  장애인주차장 확인됨
                </li>
                <li className="flex items-center gap-2 text-stone-800">
                  <span aria-hidden className="grid place-items-center w-6 h-6 rounded-md bg-red-50 text-red-700 font-bold">✕</span>
                  휠체어 대여 없음
                </li>
                <li className="flex items-center gap-2 text-stone-800">
                  <span aria-hidden className="grid place-items-center w-6 h-6 rounded-md bg-brand-50 text-brand-700 font-bold">∠</span>
                  경사 구간 <strong>7˚ · 44m</strong> 실측 기록
                </li>
              </ul>
              <p className="m-0 mt-4 pt-3 border-t border-stone-100 text-sm text-stone-500 leading-relaxed">
                확인 안 된 시설은 <strong className="text-stone-700">? 정보 없음</strong>으로
                구분합니다. 출처: 제주데이터허브 무장애여행정보
              </p>
            </div>
          </aside>
        </div>

        {/* 함께 보는 데이터 — 문장으로 (타일 아님) */}
        <p className="max-w-5xl mx-auto mt-10 mb-0 pt-6 border-t border-brand-100 text-base text-stone-600 leading-relaxed">
          함께 보는 데이터 — 제주 관광지{" "}
          <strong className="text-stone-900">154곳</strong> · 무장애 실측 정보{" "}
          <strong className="text-stone-900">1,102건</strong> · 기상청{" "}
          <strong className="text-stone-900">실시간 예보·특보</strong> · 제주공항 도면{" "}
          <strong className="text-stone-900">1–4층</strong>
        </p>
      </section>

      {/* 이용 흐름 — 플래너 지도의 동선(점선)을 그대로 가져온 시그니처 */}
      <section id="how" className="px-4 sm:px-6 py-14 scroll-mt-20">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-3xl sm:text-4xl font-bold text-stone-900 m-0">
            지도의 동선처럼, 네 걸음
          </h2>
          <p className="mt-3 mb-0 text-lg text-stone-600">
            플래너 지도에 그려지는 경로 그대로 — 관광지에서 공항까지.
          </p>
          <ol className="relative list-none m-0 mt-10 p-0">
            {/* 동선 점선 — 지도 위 경로선과 같은 주황 점선 */}
            <div
              aria-hidden
              className="absolute left-[23px] top-6 bottom-10 border-l-[3px] border-dashed border-brand-300"
            />
            {ROUTE_STEPS.map((s) => (
              <li key={s.title} className="relative flex gap-5 pb-9 last:pb-0">
                <span
                  aria-hidden
                  className={`relative z-10 grid place-items-center w-12 h-12 shrink-0 rounded-full text-white text-lg font-extrabold border-4 border-[#fdfaf7] ${
                    s.isAirport ? "bg-sea-700" : "bg-brand-700"
                  }`}
                >
                  {s.pin}
                </span>
                <div className="pt-1">
                  <h3 className="m-0 text-xl font-bold text-stone-900">{s.title}</h3>
                  <p className="mt-1.5 mb-0 text-base sm:text-lg text-stone-600 leading-relaxed">
                    {s.desc}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* 장소마다 확인하는 것 — 키라인 목록 */}
      <section className="px-4 sm:px-6 pb-14">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-3xl sm:text-4xl font-bold text-stone-900 m-0">
            장소마다 이런 것을 확인합니다
          </h2>
          <dl className="m-0 mt-8 space-y-6">
            {CHECKS.map((c) => (
              <div key={c.term} className="border-l-4 border-brand-300 pl-5 py-1">
                <dt className="text-xl font-bold text-stone-900">{c.term}</dt>
                <dd className="m-0 mt-1.5 text-base sm:text-lg text-stone-600 leading-relaxed">
                  {c.desc}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* 마감 CTA — 현무암 먹색 단면 (그라데이션 없음) */}
      <section className="px-4 sm:px-6 pb-6">
        <div className="max-w-3xl mx-auto rounded-3xl bg-stone-900 px-6 sm:px-10 py-12 text-center">
          <h2 className="font-display m-0 text-3xl sm:text-4xl font-bold text-white leading-snug">
            오늘 갈 수 있는 곳,
            <br className="sm:hidden" /> 지금 확인해 보세요
          </h2>
          <p className="mt-4 mb-0 text-lg text-stone-300">
            질문 한 줄이면 추천부터 공항 동선까지 준비됩니다.
          </p>
          <Link
            to="/planner"
            className="no-underline inline-flex items-center min-h-[3.25rem] mt-8 px-8 py-3.5 rounded-2xl bg-white text-stone-900 text-lg font-bold hover:bg-brand-50 transition-colors"
          >
            여행 계획 시작하기
          </Link>
        </div>
      </section>
    </div>
  );
}
