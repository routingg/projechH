import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import PlannerPage from "./pages/PlannerPage";
import DataSourceFooter from "./components/DataSourceFooter";

const navItems = [
  { to: "/", label: "홈", end: true },
  { to: "/planner", label: "여행 플래너", end: false },
];

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* 키보드 사용자용 스킵 링크 — Tab 첫 이동에서 나타남 */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-5 focus:py-3 focus:rounded-xl focus:bg-brand-700 focus:text-white focus:text-base focus:font-bold no-underline"
      >
        본문으로 건너뛰기
      </a>
      <header className="sticky top-0 z-20 bg-white/80 backdrop-blur-md border-b border-brand-100">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-4 sm:px-6 h-16">
          <NavLink to="/" end className="flex items-center gap-2 no-underline">
            <span className="grid place-items-center w-8 h-8 rounded-xl bg-brand-500 text-white text-lg shadow-sm">
              ♿
            </span>
            <span className="font-extrabold text-lg tracking-tight text-stone-800">
              WheelTrip <span className="text-brand-500">Jeju</span>
            </span>
          </NavLink>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-full text-base font-semibold no-underline transition-colors ${
                    isActive
                      ? "bg-brand-700 text-white shadow-sm"
                      : "text-stone-600 hover:bg-brand-50 hover:text-brand-700"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main id="main" className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/planner" element={<PlannerPage />} />
          {/* 구 탭 경로는 플래너로 통합됨 — 북마크 호환 리다이렉트 */}
          <Route path="/recommendation" element={<Navigate to="/planner" replace />} />
          <Route path="/itinerary" element={<Navigate to="/planner" replace />} />
          <Route path="/airport" element={<Navigate to="/planner" replace />} />
          <Route path="/search" element={<Navigate to="/planner" replace />} />
        </Routes>
      </main>

      <DataSourceFooter />
    </div>
  );
}
