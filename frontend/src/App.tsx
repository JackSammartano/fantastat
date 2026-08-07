import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { StatePanel } from "./components/StatePanel";
import { IS_STATIC } from "./api/client";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({
    default: module.DashboardPage
  }))
);
const CurrentListPage = lazy(() =>
  import("./pages/CurrentListPage").then((module) => ({
    default: module.CurrentListPage
  }))
);
const PlayerDetailPage = lazy(() =>
  import("./pages/PlayerDetailPage").then((module) => ({
    default: module.PlayerDetailPage
  }))
);
const ComparePage = lazy(() =>
  import("./pages/ComparePage").then((module) => ({
    default: module.ComparePage
  }))
);
const RankingsPage = lazy(() =>
  import("./pages/RankingsPage").then((module) => ({
    default: module.RankingsPage
  }))
);
const MappingReviewPage = lazy(() =>
  import("./pages/MappingReviewPage").then((module) => ({
    default: module.MappingReviewPage
  }))
);

export function App() {
  return (
    <Suspense
      fallback={<StatePanel title="Caricamento" message="Apertura pagina…" />}
    >
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="players" element={<Navigate to="/current-list" replace />} />
          <Route path="current-list" element={<CurrentListPage />} />
          <Route path="players/:playerId" element={<PlayerDetailPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="rankings" element={<RankingsPage />} />
          <Route path="mappings" element={IS_STATIC ? <Navigate to="/" replace /> : <MappingReviewPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
