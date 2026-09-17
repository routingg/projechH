const SOURCES: { name: string; url: string }[] = [
  { name: "제주올레길 휠체어구간(1코스)", url: "https://www.data.go.kr/data/15097499/fileData.do" },
  { name: "제주올레길 휠체어구간(14코스)", url: "https://www.data.go.kr/data/15097502/fileData.do" },
  { name: "사회적약자 시설데이터 로드뷰", url: "https://www.data.go.kr/data/15109149/openapi.do" },
  { name: "사회적약자 시설(로드뷰) 관광지 현황", url: "https://www.data.go.kr/data/15109153/fileData.do" },
  { name: "제주 저상버스현황", url: "https://www.data.go.kr/data/15114410/fileData.do" },
  { name: "제주 저상버스운행노선현황", url: "https://www.data.go.kr/data/15155485/fileData.do" },
  { name: "기상청 단기예보 조회서비스", url: "https://www.data.go.kr/data/15084084/openapi.do" },
  { name: "기상청 기상특보 조회서비스", url: "https://www.data.go.kr/data/15000415/openapi.do" },
  { name: "한국공항공사 제주공항 도면 이미지", url: "https://www.data.go.kr/data/15151895/fileData.do" },
  { name: "한국공항공사 제주공항 층별 입점업체", url: "https://www.data.go.kr/data/15119335/fileData.do" },
  { name: "JDC 제주국제공항 면세점 매장정보", url: "https://www.data.go.kr/data/15144890/openapi.do" },
];

export default function DataSourceFooter() {
  return (
    <footer className="border-t border-brand-100 bg-white">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5">
        <details className="group">
          <summary className="cursor-pointer list-none flex items-center justify-between text-xs text-stone-400 select-none">
            <span>
              <strong className="text-stone-500">WheelTrip Jeju</strong> · 공공데이터{" "}
              {SOURCES.length}종 기반
            </span>
            <span className="font-semibold text-brand-400 hover:text-brand-500">
              데이터 출처 보기{" "}
              <span className="inline-block transition-transform group-open:rotate-180">▾</span>
            </span>
          </summary>

          <ul className="mt-3 mb-0 pl-4 columns-1 sm:columns-2 text-xs text-stone-400 space-y-0.5">
            {SOURCES.map((s) => (
              <li key={s.url}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-stone-400 hover:text-brand-500 no-underline"
                >
                  {s.name}
                </a>
              </li>
            ))}
          </ul>
          <p className="mt-3 mb-0 text-[11px] text-stone-300">
            ※ JDC 데이터는 면세점 매장정보 안내에만 사용합니다. 공항 편의시설·동선은
            한국공항공사 데이터를 사용하며, 확인되지 않은 정보는 표시하지 않습니다. 본 서비스의
            추천 결과는 참고 정보이며 접근 가능성과 안전을 보장하지 않습니다.
          </p>
        </details>
      </div>
    </footer>
  );
}
