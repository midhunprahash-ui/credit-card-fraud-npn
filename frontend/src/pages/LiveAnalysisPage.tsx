import { useCallback, useEffect, useMemo, useState } from "react";

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
import { formatCurrency, formatLatency, formatNumber } from "../utils/format";

type Filters = {
  versions: VersionName[];
  models: ModelIdentifier[];
  inputMode: "Manual" | "Real-time";
};

export function LiveAnalysisPage({
  filters,
  onFiltersChange,
}: {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
}) {
  const [streamStatus, setStreamStatus] = useState<string>("IDLE");
  const locked = ["LOADING", "RUNNING", "STOPPING"].includes(streamStatus);
  return (
    <>
      <PageHeader
        eyebrow="Prediction workspace"
        title="Live analysis"
        description="Score real transactions manually or replay the labelled chronological held-out partition through a strict FIFO stream."
      />
      <FilterBar
        versions={filters.versions}
        models={filters.models}
        inputMode={filters.inputMode}
        locked={locked}
        onVersionsChange={(versions) =>
          onFiltersChange({ ...filters, versions })
        }
        onModelsChange={(models) => onFiltersChange({ ...filters, models })}
        onInputModeChange={(inputMode) =>
          onFiltersChange({ ...filters, inputMode })
        }
      />
      {filters.inputMode === "Manual" ? (
        <ManualWorkspace models={filters.models} />
      ) : (
        <RealtimeWorkspace
          models={filters.models}
          onStatusChange={setStreamStatus}
        />
      )}
    </>
  );
}

function ManualWorkspace({ models }: { models: ModelIdentifier[] }) {
  const [tab, setTab] = useState<"single" | "csv">("single");
  return (
    <div className="workspace">
      <div className="tabs" role="tablist" aria-label="Manual input">
        <button
          role="tab"
          aria-selected={tab === "single"}
          className={tab === "single" ? "active" : ""}
          onClick={() => setTab("single")}
        >
          Single Transaction
        </button>
        <button
          role="tab"
          aria-selected={tab === "csv"}
          className={tab === "csv" ? "active" : ""}
          onClick={() => setTab("csv")}
        >
          CSV Upload
        </button>
      </div>
      {tab === "single" ? (
        <SingleTransactionPanel models={models} />
      ) : (
        <BatchPanel models={models} />
      )}
    </div>
  );
}

type DemoSummary = {
  transaction_id: number;
  transaction_dt: number;
  transaction_amount: number | null;
  product_code: string | null;
  has_identity: boolean;
};

function SingleTransactionPanel({ models }: { models: ModelIdentifier[] }) {
  const [method, setMethod] = useState<"demo" | "form" | "json" | "file">(
    "demo",
  );
  const [demos, setDemos] = useState<DemoSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [payload, setPayload] = useState<Record<string, unknown>>({
    TransactionID: 3488959,
    TransactionDT: 13151880,
    TransactionAmt: 57.95,
    ProductCD: "W",
  });
  const [jsonText, setJsonText] = useState(JSON.stringify(payload, null, 2));
  const [oneRowFile, setOneRowFile] = useState<File | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api
      .demoTransactions(30)
      .then((result) => {
        setDemos(result.transactions);
        if (result.transactions[0])
          setSelectedId(result.transactions[0].transaction_id);
      })
      .catch((caught) =>
        setError(
          caught instanceof Error ? caught.message : "Demo data unavailable",
        ),
      );
  }, []);
  async function predict() {
    if (!models.length) {
      setError("Select at least one model.");
      return;
    }
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      if (method === "file") {
        if (!oneRowFile) throw new Error("Choose a one-row CSV file.");
        setPrediction(await api.predictFile(oneRowFile, models));
      } else {
        let transaction = payload;
        if (method === "demo") {
          if (!selectedId)
            throw new Error("Choose a demonstration transaction.");
          transaction = (await api.transaction(selectedId)).transaction_payload;
          setPayload(transaction);
          setJsonText(JSON.stringify(transaction, null, 2));
        } else if (method === "json") {
          const parsed: unknown = JSON.parse(jsonText);
          if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
            throw new Error("JSON must contain one transaction object.");
          transaction = parsed as Record<string, unknown>;
        }
        setPrediction(await api.predict(transaction, models));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="single-layout">
      <Panel title="Transaction input" eyebrow="Raw joined transaction">
        <div className="method-grid">
          {(
            [
              ["demo", "Real transaction"],
              ["form", "Simplified form"],
              ["json", "Complete JSON"],
              ["file", "One-row CSV"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              className={method === id ? "method-card active" : "method-card"}
              onClick={() => setMethod(id)}
            >
              <span>{label}</span>
              <small>
                {id === "demo"
                  ? "Recommended"
                  : id === "json"
                    ? "All raw fields"
                    : id === "file"
                      ? "CSV contract"
                      : "Required fields"}
              </small>
            </button>
          ))}
        </div>
        {method === "demo" ? (
          <label className="field">
            <span>Held-out TransactionID</span>
            <select
              value={selectedId ?? ""}
              onChange={(event) => setSelectedId(Number(event.target.value))}
            >
              {demos.map((demo) => (
                <option key={demo.transaction_id} value={demo.transaction_id}>
                  {demo.transaction_id} ·{" "}
                  {formatCurrency(demo.transaction_amount ?? 0)} ·{" "}
                  {demo.product_code ?? "Unknown"}
                  {demo.has_identity ? " · identity joined" : ""}
                </option>
              ))}
            </select>
            <small>The label is hidden until after model inference.</small>
          </label>
        ) : null}
        {method === "form" ? (
          <div className="form-grid">
            <label className="field">
              <span>TransactionID</span>
              <input
                type="number"
                value={Number(payload.TransactionID)}
                onChange={(event) =>
                  setPayload({
                    ...payload,
                    TransactionID: Number(event.target.value),
                  })
                }
              />
            </label>
            <label className="field">
              <span>TransactionDT</span>
              <input
                type="number"
                value={Number(payload.TransactionDT)}
                onChange={(event) =>
                  setPayload({
                    ...payload,
                    TransactionDT: Number(event.target.value),
                  })
                }
              />
            </label>
            <label className="field">
              <span>Amount</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={Number(payload.TransactionAmt)}
                onChange={(event) =>
                  setPayload({
                    ...payload,
                    TransactionAmt: Number(event.target.value),
                  })
                }
              />
            </label>
            <label className="field">
              <span>Product code</span>
              <input
                value={String(payload.ProductCD ?? "")}
                onChange={(event) =>
                  setPayload({ ...payload, ProductCD: event.target.value })
                }
              />
            </label>
          </div>
        ) : null}
        {method === "json" ? (
          <label className="field">
            <span>Complete transaction JSON</span>
            <textarea
              className="code-input"
              rows={14}
              value={jsonText}
              onChange={(event) => setJsonText(event.target.value)}
              spellCheck={false}
            />
            <small>`isFraud` is removed at the API boundary if supplied.</small>
          </label>
        ) : null}
        {method === "file" ? (
          <label className="drop-zone compact">
            <Icon name="upload" />
            <strong>{oneRowFile?.name ?? "Choose a one-row CSV"}</strong>
            <span>Exactly one raw transaction</span>
            <input
              className="visually-hidden"
              type="file"
              accept=".csv,text/csv"
              onChange={(event) =>
                setOneRowFile(event.target.files?.[0] ?? null)
              }
            />
          </label>
        ) : null}
        <div className="predict-footer">
          <span className="muted">
            {models.length} model{models.length === 1 ? "" : "s"} selected
          </span>
          <button
            className="button button-primary"
            disabled={loading || !models.length}
            onClick={() => void predict()}
          >
            {loading ? "Scoring pipelines…" : "Analyse transaction"}
          </button>
        </div>
        {error ? <ErrorState message={error} /> : null}
      </Panel>
      <div>
        {prediction ? (
          <PredictionResults prediction={prediction} />
        ) : (
          <EmptyState
            title="Ready for analysis"
            detail="Choose a real held-out transaction for the primary demonstration, then compare independent model risk scores and thresholds."
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
    } else if ("status" in message.data)
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
  const latestPrediction = completed.find((event) => event.results.length);
  const riskScores = useMemo(
    () =>
      completed.flatMap((event) =>
        event.results.map((result) => result.risk_score),
      ),
    [completed],
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
      <div className="stats-grid stats-eight">
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
          label="Average latency"
          value={formatLatency(status.average_latency_ms)}
        />
        <StatCard
          label="Fraud alerts"
          value={formatNumber(status.fraud_alerts)}
          tone="high"
        />
        <StatCard
          label="Suspicious value"
          value={formatCurrency(status.suspicious_transaction_value)}
          tone="review"
        />
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Live transactions"
          eyebrow="Completed in FIFO order"
          className="span-two"
        >
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
        <Panel
          title="Risk distribution"
          eyebrow={`${riskScores.length} model scores`}
        >
          <ScoreHistogram scores={riskScores} />
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

function ScoreHistogram({ scores }: { scores: number[] }) {
  const bins = [0, 0, 0, 0, 0];
  for (const score of scores) bins[Math.min(4, Math.floor(score * 5))] += 1;
  const max = Math.max(1, ...bins);
  return (
    <div className="histogram">
      {bins.map((count, index) => (
        <div key={index}>
          <span
            className="histogram-bar"
            style={{ height: `${Math.max(4, (count / max) * 100)}%` }}
          />
          <small>
            {index * 20}–{(index + 1) * 20}
          </small>
        </div>
      ))}
    </div>
  );
}
