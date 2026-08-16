import { useCallback, useEffect, useState } from "react";

import { api, subscribeToStream, type StreamMessage } from "../api/client";
import type {
  CompletedStreamEvent,
  ModelIdentifier,
  PredictionResponse,
  QueueStreamEvent,
  StreamDataset,
  StreamStatus,
  VersionName,
} from "../api/types";
import { BatchPanel } from "../components/BatchPanel";
import { FilterBar } from "../components/FilterBar";
import { Icon } from "../components/Icon";
import { PredictionResults } from "../components/PredictionResults";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  Panel,
  RiskScore,
  StatCard,
  StatusBadge,
} from "../components/ui";
import { formatLatency, formatNumber } from "../utils/format";

type Filters = {
  versions: VersionName[];
  models: ModelIdentifier[];
};

type InputMode = "json" | "csv" | "realtime";

const STREAM_STATUS_EVENTS = new Set([
  "stream_status",
  "stream_started",
  "stream_paused",
  "stream_resumed",
  "stream_stopping",
  "stream_finished",
  "stream_failed",
]);

export function LiveAnalysisPage({
  filters,
  onFiltersChange,
}: {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
}) {
  const [inputMode, setInputMode] = useState<InputMode>("json");
  const [streamStatus, setStreamStatus] = useState<string>("IDLE");
  const locked = ["LOADING", "RUNNING", "STOPPING"].includes(streamStatus);
  return (
    <>
      <PageHeader
        eyebrow="ML classification"
        title="Fraud prediction"
        description="Choose trained model pipelines, then classify a single JSON transaction, a CSV file, or a chronological real-time replay."
      />
      <FilterBar
        versions={filters.versions}
        models={filters.models}
        locked={locked}
        onVersionsChange={(versions) =>
          onFiltersChange({ ...filters, versions })
        }
        onModelsChange={(models) => onFiltersChange({ ...filters, models })}
      />
      <div
        className="prediction-mode-tabs"
        role="tablist"
        aria-label="Input type"
      >
        {(
          [
            ["json", "Single JSON"],
            ["csv", "CSV Upload"],
            ["realtime", "Real-time"],
          ] as const
        ).map(([mode, label]) => (
          <button
            key={mode}
            role="tab"
            type="button"
            aria-selected={inputMode === mode}
            className={inputMode === mode ? "active" : ""}
            disabled={locked && inputMode !== mode}
            onClick={() => setInputMode(mode)}
          >
            {label}
          </button>
        ))}
      </div>
      {inputMode === "json" ? (
        <SingleJsonPanel models={filters.models} />
      ) : inputMode === "csv" ? (
        <BatchPanel models={filters.models} />
      ) : (
        <RealtimeWorkspace
          models={filters.models}
          onStatusChange={setStreamStatus}
        />
      )}
    </>
  );
}

function SingleJsonPanel({ models }: { models: ModelIdentifier[] }) {
  const [jsonText, setJsonText] = useState(
    JSON.stringify(
      {
        TransactionID: 3488959,
        TransactionDT: 13151880,
        TransactionAmt: 57.95,
        ProductCD: "W",
      },
      null,
      2,
    ),
  );
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function predict() {
    if (!models.length) {
      setError("Select at least one model.");
      return;
    }
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      const parsed: unknown = JSON.parse(jsonText);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
        throw new Error("JSON must contain one transaction object.");
      setPrediction(
        await api.predict(parsed as Record<string, unknown>, models),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="single-layout">
      <Panel title="Transaction JSON" eyebrow="One raw transaction">
        <label className="field" htmlFor="transaction-json">
          <span>JSON input</span>
          <textarea
            id="transaction-json"
            aria-label="JSON input"
            className="code-input"
            rows={18}
            value={jsonText}
            onChange={(event) => setJsonText(event.target.value)}
            spellCheck={false}
          />
          <small>
            Include TransactionID and raw transaction fields. `isFraud` is
            removed before inference if supplied.
          </small>
        </label>
        <div className="predict-footer">
          <span className="muted">
            {models.length} model{models.length === 1 ? "" : "s"} selected
          </span>
          <button
            className="button button-primary"
            disabled={loading || !models.length}
            onClick={() => void predict()}
          >
            {loading ? "Running prediction…" : "Run prediction"}
          </button>
        </div>
        {error ? <ErrorState message={error} /> : null}
      </Panel>
      <div>
        {prediction ? (
          <PredictionResults prediction={prediction} />
        ) : (
          <EmptyState
            title="Ready to classify"
            detail="Paste one raw transaction as JSON and run the selected trained model pipelines."
          />
        )}
      </div>
    </div>
  );
}

const EMPTY_STREAM: StreamStatus = {
  stream_run_id: null,
  dataset_id: null,
  status: "IDLE",
  selected_versions: [],
  selected_models: [],
  transactions_per_second: 1,
  transactions_received: 0,
  transactions_processed: 0,
  transactions_queued: 0,
  currently_processing: null,
  current_sequence: -1,
  current_throughput: 0,
  average_latency_ms: 0,
  p95_latency_ms: 0,
  fraud_alerts: 0,
  suspicious_transaction_value: 0,
  failed_transactions: 0,
  unpersisted_transactions: 0,
  started_at: null,
  completed_at: null,
};

function RealtimeWorkspace({
  models,
  onStatusChange,
}: {
  models: ModelIdentifier[];
  onStatusChange: (status: string) => void;
}) {
  const [datasets, setDatasets] = useState<StreamDataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [rate, setRate] = useState(1);
  const [status, setStatus] = useState<StreamStatus>(EMPTY_STREAM);
  const [queue, setQueue] = useState<QueueStreamEvent[]>([]);
  const [completed, setCompleted] = useState<CompletedStreamEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handleMessage = useCallback((message: StreamMessage) => {
    if (message.type === "transaction_received") {
      const event = message.data as QueueStreamEvent;
      setQueue((items) => [...items, event].slice(-250));
      if (event.stream) setStatus(event.stream);
    } else if (
      message.type === "transaction_completed" ||
      message.type === "transaction_failed"
    ) {
      const event = message.data as CompletedStreamEvent;
      setQueue((items) =>
        items.filter((item) => item.sequence_number !== event.sequence_number),
      );
      setCompleted((items) => [event, ...items].slice(0, 250));
      if (event.stream) setStatus(event.stream);
    } else if (
      STREAM_STATUS_EVENTS.has(message.type) &&
      "status" in message.data
    )
      setStatus(message.data as StreamStatus);
  }, []);
  useEffect(() => {
    Promise.all([api.streamDatasets(), api.streamStatus()])
      .then(([data, initial]) => {
        setDatasets(data.datasets);
        setDatasetId(data.datasets[0]?.id ?? "");
        setStatus(initial);
      })
      .catch((caught) =>
        setError(
          caught instanceof Error ? caught.message : "Streaming unavailable",
        ),
      );
    const close = subscribeToStream(handleMessage, setConnected);
    return close;
  }, [handleMessage]);
  useEffect(
    () => onStatusChange(status.status),
    [status.status, onStatusChange],
  );
  async function control(action: "pause" | "resume" | "stop" | "restart") {
    if (
      action === "restart" &&
      !window.confirm(
        "Restart this replay from sequence zero? Current on-screen live rows will be cleared.",
      )
    )
      return;
    setError(null);
    try {
      setStatus(await api.streamControl(action));
      if (action === "restart") {
        setQueue([]);
        setCompleted([]);
      }
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : `Could not ${action} stream`,
      );
    }
  }
  async function start() {
    if (!datasetId || !models.length) {
      setError("Choose a dataset and at least one model.");
      return;
    }
    setError(null);
    setQueue([]);
    setCompleted([]);
    try {
      setStatus(await api.streamStart(datasetId, models, rate));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not start stream",
      );
    }
  }
  const active = ["RUNNING", "PAUSED", "LOADING", "STOPPING"].includes(
    status.status,
  );
  const latestPrediction = completed.find(
    (event) => event.results.length && event.agreement,
  );
  return (
    <div className="realtime-workspace">
      <Panel
        title="Stream controls"
        eyebrow="Chronological held-out replay"
        actions={
          <div className="connection-status">
            <span
              className={`connection-dot ${connected ? "online" : "offline"}`}
            />
            {connected ? "SSE connected" : "SSE reconnecting"}
          </div>
        }
      >
        <div className="stream-controls">
          <label className="field">
            <span>Dataset</span>
            <select
              value={datasetId}
              disabled={active}
              onChange={(event) => setDatasetId(event.target.value)}
            >
              {datasets.map((dataset) => (
                <option value={dataset.id} key={dataset.id}>
                  {dataset.name} · {formatNumber(dataset.row_count)} rows
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Arrival rate</span>
            <select
              value={rate}
              disabled={active}
              onChange={(event) => setRate(Number(event.target.value))}
            >
              <option value={1}>1 transaction/second</option>
              <option value={2}>2 transactions/second</option>
              <option value={5}>5 transactions/second</option>
            </select>
          </label>
          <div className="control-buttons">
            <button
              className="button button-primary"
              disabled={active || !datasetId || !models.length}
              onClick={() => void start()}
            >
              <Icon name="play" />
              Start
            </button>
            <button
              className="button button-secondary"
              disabled={status.status !== "RUNNING"}
              onClick={() => void control("pause")}
            >
              <Icon name="pause" />
              Pause
            </button>
            <button
              className="button button-secondary"
              disabled={status.status !== "PAUSED"}
              onClick={() => void control("resume")}
            >
              <Icon name="play" />
              Resume
            </button>
            <button
              className="button button-danger"
              disabled={!active}
              onClick={() => void control("stop")}
            >
              <Icon name="stop" />
              Stop
            </button>
            <button
              className="button button-ghost"
              disabled={active || !status.stream_run_id}
              onClick={() => void control("restart")}
            >
              <Icon name="refresh" />
              Restart
            </button>
          </div>
        </div>
        {error ? <ErrorState message={error} /> : null}
      </Panel>
      <div className="stats-grid stats-six">
        <StatCard
          label="Stream status"
          value={
            <StatusBadge
              tone={
                status.status === "RUNNING"
                  ? "low"
                  : status.status === "FAILED"
                    ? "high"
                    : "review"
              }
            >
              {status.status}
            </StatusBadge>
          }
        />
        <StatCard
          label="Received"
          value={formatNumber(status.transactions_received)}
        />
        <StatCard
          label="Processed"
          value={formatNumber(status.transactions_processed)}
          tone="low"
        />
        <StatCard
          label="Queued"
          value={formatNumber(
            Math.max(status.transactions_queued, queue.length),
          )}
          tone={queue.length ? "review" : "neutral"}
        />
        <StatCard
          label="Throughput"
          value={`${status.current_throughput.toFixed(2)} TPS`}
        />
        <StatCard
          label="P95 latency"
          value={formatLatency(status.p95_latency_ms)}
        />
      </div>
      <div className="dashboard-grid">
        <Panel title="Live transactions" eyebrow="Completed in FIFO order">
          {completed.length ? (
            <LiveTable rows={completed} />
          ) : (
            <EmptyState
              title="No completed transactions"
              detail="Start the stream to publish predictions as each FIFO event completes."
            />
          )}
        </Panel>
        <Panel title="Live queue" eyebrow={`${queue.length} waiting`}>
          {queue.length ? (
            <div className="queue-list">
              {queue.slice(0, 12).map((item) => (
                <div key={item.sequence_number}>
                  <span className="queue-position">#{item.queue_position}</span>
                  <div>
                    <strong>{item.transaction_id}</strong>
                    <small>Sequence {item.sequence_number}</small>
                  </div>
                  <StatusBadge tone="review">Queued</StatusBadge>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Queue is empty"
              detail="Backlog appears here when arrivals exceed scoring throughput."
            />
          )}
        </Panel>
      </div>
      {latestPrediction ? (
        <PredictionResults
          prediction={{
            transaction_id: latestPrediction.transaction_id,
            input_completeness: 1,
            results: latestPrediction.results,
            agreement: latestPrediction.agreement!,
          }}
        />
      ) : null}
    </div>
  );
}

function LiveTable({ rows }: { rows: CompletedStreamEvent[] }) {
  return (
    <div className="table-scroll live-table">
      <table>
        <thead>
          <tr>
            <th>Seq</th>
            <th>Transaction</th>
            <th>Highest risk</th>
            <th>Fraud votes</th>
            <th>Actual label</th>
            <th>Latency</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const maximum = Math.max(
              0,
              ...row.results.map((result) => result.risk_score),
            );
            return (
              <tr key={row.sequence_number}>
                <td className="mono">{row.sequence_number}</td>
                <td className="mono">{row.transaction_id}</td>
                <td>
                  {row.results.length ? (
                    <RiskScore score={maximum} compact />
                  ) : (
                    "—"
                  )}
                </td>
                <td>
                  {row.agreement
                    ? `${row.agreement.fraud_vote_count}/${row.agreement.selected_model_count}`
                    : "—"}
                </td>
                <td>
                  <StatusBadge tone={row.actual_label ? "high" : "low"}>
                    {row.actual_label ? "Fraud" : "Legitimate"}
                  </StatusBadge>
                </td>
                <td>{formatLatency(row.latency_ms)}</td>
                <td>{row.status}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
