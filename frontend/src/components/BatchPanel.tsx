import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { BatchResponse, ModelIdentifier } from "../api/types";
import {
  downloadText,
  formatCurrency,
  formatNumber,
  recordsToCsv,
} from "../utils/format";
import { Icon } from "./Icon";
import { EmptyState, ErrorState, Panel, StatCard, StatusBadge } from "./ui";

export function BatchPanel({ models }: { models: ModelIdentifier[] }) {
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!processing) return;
    const timer = window.setInterval(
      () => setProgress((value) => Math.min(88, value + 4)),
      180,
    );
    return () => window.clearInterval(timer);
  }, [processing]);

  async function processFile() {
    if (!file || !models.length) return;
    setProcessing(true);
    setError(null);
    setReport(null);
    setProgress(12);
    try {
      const response = await api.predictBatch(file, models);
      setProgress(100);
      setReport(response);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Batch processing failed",
      );
    } finally {
      setProcessing(false);
    }
  }

  function selectFile(selected: File | undefined) {
    if (!selected) return;
    setFile(selected);
    setReport(null);
    setError(null);
  }

  return (
    <div className="batch-layout">
      <Panel title="Upload raw transactions" eyebrow="CSV batch input">
        <button
          className="drop-zone"
          type="button"
          onClick={() => inputRef.current?.click()}
        >
          <Icon name="upload" size={28} />
          <strong>{file ? file.name : "Choose a CSV file"}</strong>
          <span>
            {file
              ? `${formatNumber(file.size / 1_024, 1)} KB`
              : "Maximum 5 MB · up to 1,000 rows"}
          </span>
        </button>
        <input
          ref={inputRef}
          className="visually-hidden"
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => selectFile(event.target.files?.[0])}
        />
        <div className="batch-actions">
          <p className="muted">
            {models.length
              ? `${models.length} independent pipeline${models.length === 1 ? "" : "s"} selected`
              : "Select at least one model above"}
          </p>
          <button
            className="button button-primary"
            disabled={!file || !models.length || processing}
            onClick={() => void processFile()}
          >
            {processing ? "Processing…" : "Analyse CSV"}
          </button>
        </div>
        {processing || progress === 100 ? (
          <div className="progress-wrap" aria-label={`Processing ${progress}%`}>
            <div className="progress-track">
              <span style={{ width: `${progress}%` }} />
            </div>
            <span>{progress}%</span>
          </div>
        ) : null}
        {error ? <ErrorState message={error} /> : null}
      </Panel>

      {report ? (
        <>
          <div className="stats-grid stats-six">
            <StatCard
              label="Total rows"
              value={formatNumber(report.summary.total_rows)}
            />
            <StatCard
              label="Valid rows"
              value={formatNumber(report.summary.valid_rows)}
              tone="low"
            />
            <StatCard
              label="Invalid rows"
              value={formatNumber(report.summary.invalid_rows)}
              tone={report.summary.invalid_rows ? "review" : "neutral"}
            />
            <StatCard
              label="Failed rows"
              value={formatNumber(report.summary.failed_rows)}
              tone={report.summary.failed_rows ? "high" : "neutral"}
            />
            <StatCard
              label="Full agreement"
              value={formatNumber(report.summary.model_agreement_count)}
            />
            <StatCard
              label="Suspicious value"
              value={formatCurrency(
                report.summary.suspicious_transaction_value,
              )}
              tone="high"
            />
          </div>
          <Panel
            title="Prediction results"
            eyebrow="Searchable output"
            actions={
              <div className="button-row">
                <button
                  className="button button-secondary"
                  onClick={() =>
                    downloadText(
                      "prediction_results.csv",
                      recordsToCsv(report.results),
                    )
                  }
                >
                  Download results
                </button>
                <button
                  className="button button-ghost"
                  disabled={!report.invalid_row_report.length}
                  onClick={() =>
                    downloadText(
                      "invalid_rows.csv",
                      recordsToCsv(
                        report.invalid_row_report as unknown as Array<
                          Record<string, unknown>
                        >,
                      ),
                    )
                  }
                >
                  Invalid rows
                </button>
              </div>
            }
          >
            <BatchResultsTable rows={report.results} />
          </Panel>
          {report.invalid_row_report.length ? (
            <Panel title="Invalid-row report" eyebrow="Rows not scored">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Transaction</th>
                      <th>Error</th>
                      <th>Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.invalid_row_report.map((row) => (
                      <tr key={`${row.row_number}-${row.error_code}`}>
                        <td>{row.row_number}</td>
                        <td>{row.transaction_id ?? "—"}</td>
                        <td>
                          <StatusBadge tone="review">
                            {row.error_code}
                          </StatusBadge>
                        </td>
                        <td>{row.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ) : null}
        </>
      ) : !processing && !error ? (
        <EmptyState
          title="No batch analysed yet"
          detail="Upload a raw joined-transaction CSV to see model-specific counts, agreement, suspicious value, and row-level results."
        />
      ) : null}
    </div>
  );
}

function BatchResultsTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  const [search, setSearch] = useState("");
  const [sortColumn, setSortColumn] = useState("TransactionID");
  const [descending, setDescending] = useState(false);
  const visible = rows
    .filter((row) => String(row.TransactionID ?? "").includes(search.trim()))
    .sort((first, second) => {
      const left = first[sortColumn];
      const right = second[sortColumn];
      const comparison =
        typeof left === "number" && typeof right === "number"
          ? left - right
          : String(left ?? "").localeCompare(String(right ?? ""));
      return descending ? -comparison : comparison;
    })
    .slice(0, 100);
  const columns = rows.length
    ? Object.keys(rows[0]).filter(
        (column) =>
          column === "TransactionID" ||
          column.endsWith("_score") ||
          ["fraud_vote_count", "processing_status"].includes(column),
      )
    : [];
  function sort(column: string) {
    if (column === sortColumn) setDescending((value) => !value);
    else {
      setSortColumn(column);
      setDescending(false);
    }
  }
  return (
    <>
      <label className="search-box">
        <Icon name="search" />
        <span className="visually-hidden">Search by transaction ID</span>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search transaction ID"
        />
      </label>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>
                  <button className="sort-button" onClick={() => sort(column)}>
                    {column.replaceAll("_", " ")}{" "}
                    {sortColumn === column ? (descending ? "↓" : "↑") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => (
              <tr key={String(row.TransactionID ?? index)}>
                {columns.map((column) => (
                  <td
                    key={column}
                    className={column.endsWith("_score") ? "mono" : ""}
                  >
                    {typeof row[column] === "number"
                      ? Number(row[column]).toFixed(
                          column.endsWith("_score") ? 5 : 0,
                        )
                      : String(row[column] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="table-note">
        Showing {visible.length} of {rows.length} processed rows.
      </p>
    </>
  );
}
