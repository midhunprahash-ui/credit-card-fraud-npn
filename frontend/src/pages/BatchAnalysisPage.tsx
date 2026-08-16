import type { ModelIdentifier, VersionName } from "../api/types";
import { BatchPanel } from "../components/BatchPanel";
import { FilterBar } from "../components/FilterBar";
import { PageHeader } from "../components/ui";

type Filters = {
  versions: VersionName[];
  models: ModelIdentifier[];
  inputMode: "Manual" | "Real-time";
};

export function BatchAnalysisPage({
  filters,
  onFiltersChange,
}: {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
}) {
  return (
    <>
      <PageHeader
        eyebrow="Bulk investigation"
        title="Batch analysis"
        description="Validate and score raw transaction CSV files in chunks, then download complete results and invalid-row reports."
      />
      <FilterBar
        versions={filters.versions}
        models={filters.models}
        locked={false}
        onVersionsChange={(versions) =>
          onFiltersChange({ ...filters, versions })
        }
        onModelsChange={(models) => onFiltersChange({ ...filters, models })}
      />
      <BatchPanel models={filters.models} />
    </>
  );
}
