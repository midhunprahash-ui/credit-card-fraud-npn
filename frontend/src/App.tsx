import { useEffect, useState } from "react";

import { api } from "./api/client";
import type { ModelIdentifier, VersionName } from "./api/types";
import { AppShell, type PageId } from "./components/AppShell";
import { DEFAULT_MODELS } from "./config/models";
import { BatchAnalysisPage } from "./pages/BatchAnalysisPage";
import { FraudAlertsPage } from "./pages/FraudAlertsPage";
import { LiveAnalysisPage } from "./pages/LiveAnalysisPage";
import { ModelComparisonPage } from "./pages/ModelComparisonPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { OverviewPage } from "./pages/OverviewPage";

const PAGES = new Set<PageId>([
  "overview",
  "live",
  "alerts",
  "batch",
  "models",
  "monitoring",
]);
type Filters = {
  versions: VersionName[];
  models: ModelIdentifier[];
  inputMode: "Manual" | "Real-time";
};

function pageFromHash(): PageId {
  const value = window.location.hash.replace(/^#\/?/, "") as PageId;
  return PAGES.has(value) ? value : "overview";
}

export default function App() {
  const [page, setPage] = useState<PageId>(pageFromHash);
  const [apiOnline, setApiOnline] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    versions: ["V1", "V2"],
    models: DEFAULT_MODELS,
    inputMode: "Manual",
  });
  useEffect(() => {
    const handleHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", handleHash);
    api
      .health()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);
  function navigate(next: PageId) {
    window.location.hash = `/${next}`;
    setPage(next);
  }
  let content: React.ReactNode;
  switch (page) {
    case "live":
      content = (
        <LiveAnalysisPage filters={filters} onFiltersChange={setFilters} />
      );
      break;
    case "alerts":
      content = <FraudAlertsPage />;
      break;
    case "batch":
      content = (
        <BatchAnalysisPage filters={filters} onFiltersChange={setFilters} />
      );
      break;
    case "models":
      content = <ModelComparisonPage />;
      break;
    case "monitoring":
      content = <MonitoringPage />;
      break;
    default:
      content = <OverviewPage onOpenAlerts={() => navigate("alerts")} />;
  }
  return (
    <AppShell page={page} onNavigate={navigate} apiOnline={apiOnline}>
      {content}
    </AppShell>
  );
}
