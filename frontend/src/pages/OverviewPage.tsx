import { useEffect, useState } from "react";

import { api } from "../api/client";
import type {
  FraudAlert,
  Health,
  MetricsSummary,
  ModelCatalogItem,
} from "../api/types";
import {
  formatCurrency,
  formatLatency,
  formatNumber,
  formatPercent,
} from "../utils/format";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Panel,
  RiskScore,
  StatCard,
  StatusBadge,
} from "../components/ui";

type OverviewData = {
  health: Health;
  metrics: MetricsSummary;
  models: ModelCatalogItem[];
  alerts: FraudAlert[];
};

export function OverviewPage({ onOpenAlerts }: { onOpenAlerts: () => void }) {
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([
      api.health(),
      api.metrics(),
      api.models(),
      api.alerts().catch(() => ({ alerts: [] })),
    ])
      .then(
        ([health, metrics, models, alerts]) =>
          active &&
          setData({
            health,
            metrics,
            models: models.models,
            alerts: alerts.alerts,
          }),
      )
      .catch(
        (caught) =>
          active &&
          setError(
            caught instanceof Error ? caught.message : "Overview failed",
          ),
      );
    return () => {
      active = false;
    };
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
  const champion = data.models
    .filter((model) => model.champion)
    .sort(
      (first, second) => second.validation_pr_auc - first.validation_pr_auc,
    )[0];
  const alertRate = stream?.transactions_processed
    ? stream.fraud_alerts / stream.transactions_processed
    : 0;
  return (
    <>
      <PageHeader
        eyebrow="Fraud operations"
        title="Intelligence overview"
        description="A concise view of current scoring activity, alert pressure, model health, and the highest-risk transactions."
        actions={
          <StatusBadge tone={data.health.status === "ok" ? "low" : "high"}>
            {data.health.status === "ok"
              ? "Systems operational"
              : "Attention required"}
          </StatusBadge>
        }
      />
      <div className="stats-grid">
        <StatCard
          label="Transactions processed"
          value={formatNumber(
            stream?.transactions_processed ??
              data.metrics.runtime.transactions_scored,
          )}
          detail={`${formatNumber(stream?.transactions_queued ?? 0)} currently queued`}
        />
        <StatCard
          label="Fraud alerts"
          value={formatNumber(stream?.fraud_alerts ?? data.alerts.length)}
          detail={`${formatPercent(alertRate)} alert rate`}
          tone="high"
        />
        <StatCard
          label="Suspicious value"
          value={formatCurrency(
            stream?.suspicious_transaction_value ??
              data.alerts.reduce(
                (sum, alert) => sum + (alert.suspicious_amount ?? 0),
                0,
              ),
          )}
          tone="review"
        />
        <StatCard
          label="Average latency"
          value={formatLatency(
            stream?.average_latency_ms ??
              data.metrics.runtime.average_request_latency_ms,
          )}
          detail={
            stream
              ? `p95 ${formatLatency(stream.p95_latency_ms)}`
              : "Manual requests"
          }
        />
        <StatCard
          label="Current champion"
          value={champion?.model_name ?? "CatBoost.V2"}
          detail="Selected on validation PR-AUC"
          tone="low"
        />
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Recent high-risk transactions"
          eyebrow="Prioritised alert queue"
          className="span-two"
          actions={
            <button className="text-button" onClick={onOpenAlerts}>
              View all alerts →
            </button>
          }
        >
          {data.alerts.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Transaction</th>
                    <th>Risk</th>
                    <th>Agreement</th>
                    <th>Value</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.alerts.slice(0, 7).map((alert) => (
                    <tr key={alert.id}>
                      <td className="mono">{alert.transaction_id}</td>
                      <td>
                        <RiskScore score={alert.highest_risk_score} compact />
                      </td>
                      <td>
                        {alert.model_agreement}/{alert.selected_model_count}
                      </td>
                      <td>{formatCurrency(alert.suspicious_amount ?? 0)}</td>
                      <td>
                        <StatusBadge
                          tone={alert.status === "OPEN" ? "high" : "review"}
                        >
                          {alert.status.replaceAll("_", " ")}
                        </StatusBadge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No persisted alerts"
              detail="Alerts will appear after a Supabase-backed held-out replay flags a transaction."
            />
          )}
        </Panel>
        <Panel title="Risk distribution" eyebrow="Current alert scores">
          <RiskDistribution alerts={data.alerts} />
        </Panel>
        <Panel title="Model agreement" eyebrow="Current run">
          <div className="agreement-summary">
            <strong>{stream?.fraud_alerts ?? 0}</strong>
            <span>transactions received at least one fraud vote</span>
          </div>
          <div className="mini-bars">
            <div>
              <span>Processed</span>
              <i style={{ width: "100%" }} />
            </div>
            <div>
              <span>Flagged</span>
              <i
                className="bar-high"
                style={{ width: `${Math.max(2, alertRate * 100)}%` }}
              />
            </div>
            <div>
              <span>Failed</span>
              <i
                className="bar-review"
                style={{
                  width: `${Math.max(0, ((stream?.failed_transactions ?? 0) / Math.max(1, stream?.transactions_received ?? 1)) * 100)}%`,
                }}
              />
            </div>
          </div>
          <p className="panel-note">
            Agreement is a visual vote count, not a trained ensemble.
          </p>
        </Panel>
      </div>
    </>
  );
}

function RiskDistribution({ alerts }: { alerts: FraudAlert[] }) {
  const bins = [0, 0, 0, 0, 0];
  for (const alert of alerts)
    bins[Math.min(4, Math.floor(alert.highest_risk_score * 5))] += 1;
  const maximum = Math.max(1, ...bins);
  return (
    <div className="histogram" aria-label="Alert risk distribution">
      {bins.map((count, index) => (
        <div key={index}>
          <span
            className="histogram-bar"
            style={{ height: `${Math.max(4, (count / maximum) * 100)}%` }}
          />
          <small>
            {index * 20}–{(index + 1) * 20}
          </small>
        </div>
      ))}
    </div>
  );
}
