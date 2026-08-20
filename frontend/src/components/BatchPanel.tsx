import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type {
  AnalysisRunDetail,
  BatchResponse,
  ModelIdentifier,
} from "../api/types";
import { modelName } from "../config/models";
import { downloadText, formatNumber, recordsToCsv } from "../utils/format";
import {
  publishHistoryChange,
  readSessionState,
  writeSessionState,
} from "../utils/storage";
import { AnalysisHistory } from "./AnalysisHistory";
import { Icon } from "./Icon";
import { PredictionTable } from "./PredictionTable";
import { EmptyState, ErrorState, Panel, StatCard, StatusBadge } from "./ui";

export function BatchPanel({ models }: { models: ModelIdentifier[] }) {
  const saved = useRef(
    readSessionState<{
      fileName: string | null;
      report: BatchResponse | null;
      reportModels: ModelIdentifier[];
      runId: string | null;
    }>("csv", {
      fileName: null,
      report: null,
      reportModels: [],
      runId: null,
    }),
  );
  const [file, setFile] = useState<File | null>(null);
  const [restoredFileName, setRestoredFileName] = useState(
    saved.current.fileName,
  );
  const [report, setReport] = useState<BatchResponse | null>(
    saved.current.report,
  );
  const [reportModels, setReportModels] = useState<ModelIdentifier[]>(
    saved.current.reportModels,
  );
  const [restoredRunId, setRestoredRunId] = useState(saved.current.runId);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    writeSessionState("csv", {
      fileName: file?.name ?? restoredFileName,
      report: report?.analysis_run_id ? null : report,
      reportModels,
      runId: report?.analysis_run_id ?? restoredRunId,
    });
  }, [file, report, reportModels, restoredFileName, restoredRunId]);

  useEffect(() => {
    const runId = restoredRunId;
    if (report || !runId) return;
    api
      .historyRun(runId)
      .then((detail) => {
        setReport(historyDetailToBatch(detail));
        setReportModels(detail.run.selected_models);
      })
      .catch(() => {
        // The inline history still provides access if an old run was removed.
      });
  }, [report, restoredRunId]);

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
      setReportModels(models);
      setRestoredFileName(file.name);
      setRestoredRunId(response.analysis_run_id ?? null);
      publishHistoryChange();
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
    setRestoredFileName(selected.name);
    setReport(null);
    setReportModels([]);
    setRestoredRunId(null);
    setError(null);
  }

  return (
    <>
      <div className="batch-layout">
        <Panel title="Upload raw transactions" eyebrow="CSV batch input">
          <button
            className="drop-zone"
            type="button"
            onClick={() => inputRef.current?.click()}
          >
            <Icon name="upload" size={28} />
            <strong>
              {file
                ? file.name
                : restoredFileName
                  ? `${restoredFileName} · reselect to analyse again`
                  : "Choose a CSV file"}
            </strong>
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
            <div
              className="progress-wrap"
              aria-label={`Processing ${progress}%`}
            >
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
            <div className="stats-grid batch-summary-grid">
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
                        recordsToCsv(
                          report.results.map(
                            ({
                              input_payload: _input,
                              model_results: _models,
                              history_ordinal: _ordinal,
                              history_prediction_ids: _historyIds,
                              ...row
                            }) => row,
                          ),
                        ),
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
              <BatchResultsTable rows={report.results} models={reportModels} />
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
            detail="Upload a raw transaction CSV to receive model scores and Fraud or Legitimate classifications for each accepted row."
          />
        ) : null}
      </div>
      <AnalysisHistory mode="csv" />
    </>
  );
}

function BatchResultsTable({
  rows,
  models,
}: {
  rows: Array<Record<string, unknown>>;
  models: ModelIdentifier[];
}) {
  const [search, setSearch] = useState("");
  const visible = rows
    .filter((row) => String(row.TransactionID ?? "").includes(search.trim()))
    .slice(0, 100);
  const predictionRows = visible.flatMap((row) =>
    models.flatMap((identifier) => {
      const name = modelName(identifier);
      const score = row[`${name}_score`];
      const threshold = row[`${name}_threshold`];
      const decision = row[`${name}_decision`];
      if (
        typeof score !== "number" ||
        typeof threshold !== "number" ||
        typeof decision !== "boolean"
      )
        return [];
      return [
        {
          key: `${String(row.TransactionID)}-${identifier}`,
          transactionId: Number(row.TransactionID),
          modelIdentifier: identifier,
          modelName: name,
          score,
          threshold,
          decision,
          input:
            typeof row.input_payload === "object" && row.input_payload !== null
              ? (row.input_payload as Record<string, unknown>)
              : undefined,
          historyPredictionId:
            typeof row.history_prediction_ids === "object" &&
            row.history_prediction_ids !== null
              ? String(
                  (row.history_prediction_ids as Record<string, unknown>)[
                    identifier
                  ] ?? "",
                ) || undefined
              : undefined,
        },
      ];
    }),
  );
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
      <PredictionTable rows={predictionRows} />
      <p className="table-note">
        Showing {visible.length} transactions and {predictionRows.length} model
        predictions.
      </p>
    </>
  );
}

function historyDetailToBatch(detail: AnalysisRunDetail): BatchResponse {
  const successful = detail.transactions.filter(
    (transaction) => transaction.status === "COMPLETED",
  );
  const invalid = detail.transactions.filter(
    (transaction) => transaction.status === "FAILED",
  );
  const results = successful.map((transaction) => {
    const row: Record<string, unknown> = {
      TransactionID:
        transaction.transaction_id ?? transaction.raw_transaction_id,
      input_payload: transaction.input_payload,
      history_ordinal: transaction.ordinal,
      history_prediction_ids: Object.fromEntries(
        transaction.predictions.map((prediction) => [
          prediction.model_identifier,
          prediction.id,
        ]),
      ),
    };
    for (const prediction of transaction.predictions) {
      row[`${prediction.model_name}_score`] = prediction.risk_score;
      row[`${prediction.model_name}_threshold`] = prediction.threshold;
      row[`${prediction.model_name}_decision`] = prediction.decision;
    }
    return row;
  });
  const storedSummary = detail.run.summary as Partial<BatchResponse["summary"]>;
  return {
    summary: {
      total_rows: storedSummary.total_rows ?? detail.run.total_transactions,
      valid_rows:
        storedSummary.valid_rows ?? detail.run.successful_transactions,
      invalid_rows: storedSummary.invalid_rows ?? invalid.length,
      processed_rows:
        storedSummary.processed_rows ?? detail.run.successful_transactions,
      failed_rows: storedSummary.failed_rows ?? detail.run.failed_transactions,
      fraud_count_by_model: storedSummary.fraud_count_by_model ?? {},
      model_agreement_count: storedSummary.model_agreement_count ?? 0,
      suspicious_transaction_value:
        storedSummary.suspicious_transaction_value ?? 0,
    },
    results,
    invalid_row_report: invalid.map((transaction) => ({
      row_number: transaction.ordinal + 2,
      transaction_id:
        transaction.transaction_id ?? transaction.raw_transaction_id,
      error_code: transaction.error_code ?? "analysis_failed",
      message: transaction.error_message ?? "The transaction was not scored",
    })),
    processing_status: detail.run.status.toLowerCase(),
    analysis_run_id: detail.run.id,
    history_status: "stored",
  };
}
