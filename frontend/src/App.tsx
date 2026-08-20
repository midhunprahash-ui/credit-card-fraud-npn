import { useEffect, useState } from "react";

import { api } from "./api/client";
import type { ModelIdentifier, VersionName } from "./api/types";
import { AppShell } from "./components/AppShell";
import { DEFAULT_MODELS } from "./config/models";
import { LiveAnalysisPage } from "./pages/LiveAnalysisPage";
import { readSessionState, writeSessionState } from "./utils/storage";

type Filters = {
  versions: VersionName[];
  models: ModelIdentifier[];
};

export default function App() {
  const [apiOnline, setApiOnline] = useState(false);
  const [filters, setFilters] = useState<Filters>(() =>
    readSessionState("filters", {
      versions: ["V1", "V2"] as VersionName[],
      models: DEFAULT_MODELS,
    }),
  );
  useEffect(() => {
    api
      .health()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);
  useEffect(() => writeSessionState("filters", filters), [filters]);
  return (
    <AppShell apiOnline={apiOnline}>
      <LiveAnalysisPage filters={filters} onFiltersChange={setFilters} />
    </AppShell>
  );
}
