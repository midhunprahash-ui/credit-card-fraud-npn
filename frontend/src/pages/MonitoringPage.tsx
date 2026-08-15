import { useEffect, useState } from "react";

import { api } from "../api/client";
import type {
  Health,
  IntegrationStatus,
  MetricsSummary,
  ModelCatalogItem,
} from "../api/types";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  Panel,
  StatCard,
  StatusBadge,
} from "../components/ui";
import { formatLatency, formatNumber } from "../utils/format";

type MonitorData = {
  health: Health;
  integrations: IntegrationStatus;
  metrics: MetricsSummary;
  models: ModelCatalogItem[];
};
export function MonitoringPage() {
  const [data, setData] = useState<MonitorData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState(new Date());
  const [reload, setReload] = useState(0);
  useEffect(() => {
    Promise.all([api.health(), api.integrations(), api.metrics(), api.models()])
      .then(([health, integrations, metrics, models]) => {
        setData({ health, integrations, metrics, models: models.models });
        setRefreshedAt(new Date());
      })
      .catch((caught) =>
        setError(
          caught instanceof Error ? caught.message : "Monitoring unavailable",
        ),
      );
  }, [reload]);
  if (error)
    return (
      <ErrorState
        message={error}
        onRetry={() => {
          setError(null);
          setReload((value) => value + 1);
        }}
      />
    );
  if (!data) return <LoadingState />;
  const stream =
    "transactions_processed" in data.metrics.stream
      ? data.metrics.stream
      : null;
  return (
    <>
      <PageHeader
        eyebrow="Operational telemetry"
        title="Application monitoring"
        description="Inspect API, storage, model-cache, stream, latency, and error health without exposing transaction payloads or secrets."
        actions={
          <button
            className="button button-secondary"
            onClick={() => setReload((value) => value + 1)}
          >
            Refresh metrics
          </button>
        }
      />
      <div className="health-grid">
        <HealthCard
          name="FastAPI backend"
          configured
          reachable
          detail={`${data.health.models_registered} models registered`}
        />
        <HealthCard
          name="Supabase"
          configured={data.integrations.supabase.configured}
          reachable={data.integrations.supabase.reachable}
          detail={data.integrations.supabase.detail}
        />
        <HealthCard
          name="Cloudflare R2"
          configured={data.integrations.cloudflare_r2.configured}
          reachable={data.integrations.cloudflare_r2.reachable}
          detail={data.integrations.cloudflare_r2.detail}
        />
      </div>
      <div className="stats-grid">
        <StatCard
          label="Prediction count"
          value={formatNumber(data.metrics.runtime.model_predictions)}
        />
        <StatCard
          label="Average request"
          value={formatLatency(data.metrics.runtime.average_request_latency_ms)}
        />
        <StatCard
          label="Error count"
          value={formatNumber(data.metrics.runtime.error_count)}
          tone={data.metrics.runtime.error_count ? "high" : "low"}
        />
        <StatCard
          label="Loaded models"
          value={`${data.metrics.model_manager.loaded_count}/${data.metrics.model_manager.max_loaded_models}`}
        />
        <StatCard
          label="Queue length"
          value={formatNumber(stream?.transactions_queued ?? 0)}
          tone={stream?.transactions_queued ? "review" : "neutral"}
        />
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Model manager"
          eyebrow="Bounded LRU cache"
          className="span-two"
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Version</th>
                  <th>Loading state</th>
                  <th>Champion</th>
                  <th>Run ID</th>
                </tr>
              </thead>
              <tbody>
                {data.models.map((model) => (
                  <tr key={model.model_identifier}>
                    <td>{model.display_name}</td>
                    <td>
                      <StatusBadge tone="neutral">
                        {model.version_name}
                      </StatusBadge>
                    </td>
                    <td>
                      <StatusBadge
                        tone={
                          model.loading_status === "loaded"
                            ? "low"
                            : model.loading_status === "failed"
                              ? "high"
                              : "neutral"
                        }
                      >
                        {model.loading_status}
                      </StatusBadge>
                    </td>
                    <td>{model.champion ? "Yes" : "—"}</td>
                    <td className="mono">{model.run_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Active stream" eyebrow="FIFO runtime">
          <dl className="monitor-list">
            <div>
              <dt>Status</dt>
              <dd>{stream?.status ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Received</dt>
              <dd>{formatNumber(stream?.transactions_received ?? 0)}</dd>
            </div>
            <div>
              <dt>Average latency</dt>
              <dd>{formatLatency(stream?.average_latency_ms ?? 0)}</dd>
            </div>
            <div>
              <dt>p95 latency</dt>
              <dd>{formatLatency(stream?.p95_latency_ms ?? 0)}</dd>
            </div>
            <div>
              <dt>Unpersisted</dt>
              <dd>{formatNumber(stream?.unpersisted_transactions ?? 0)}</dd>
            </div>
          </dl>
        </Panel>
        <Panel title="Runtime safety" eyebrow="Current process">
          <ul className="guidance-list">
            <li>Raw payloads are excluded from logs.</li>
            <li>Actual labels reveal only after demo inference.</li>
            <li>Model manifests and hashes are verified before loading.</li>
            <li>CORS origins come from the environment.</li>
            <li>Frontend contains no Supabase or R2 secret.</li>
          </ul>
        </Panel>
      </div>
      <p className="refresh-note">
        Last refreshed {refreshedAt.toLocaleTimeString()}
      </p>
    </>
  );
}
function HealthCard({
  name,
  configured,
  reachable,
  detail,
}: {
  name: string;
  configured: boolean;
  reachable: boolean;
  detail: string;
}) {
  return (
    <article className="health-card">
      <div>
        <span
          className={`health-icon ${reachable ? "healthy" : configured ? "warning" : "muted-icon"}`}
        />
        <div>
          <strong>{name}</strong>
          <span>{detail}</span>
        </div>
      </div>
      <StatusBadge tone={reachable ? "low" : configured ? "review" : "neutral"}>
        {reachable ? "Healthy" : configured ? "Unreachable" : "Not configured"}
      </StatusBadge>
    </article>
  );
}
