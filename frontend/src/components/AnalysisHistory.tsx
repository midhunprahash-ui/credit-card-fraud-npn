import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type {
  AnalysisHistoryPrediction,
  AnalysisMode,
  AnalysisRun,
  AnalysisRunDetail,
  ExplanationResponse,
} from "../api/types";
import { downloadBlob, formatDate, formatNumber } from "../utils/format";
import { Icon } from "./Icon";
import { PredictionTable } from "./PredictionTable";
import { EmptyState, ErrorState, Panel, StatusBadge } from "./ui";

const MODE_LABELS: Record<AnalysisMode, string> = {
  single: "Single JSON",
  csv: "CSV Upload",
  realtime: "Real-time",
};

function cachedExplanation(
  prediction: AnalysisHistoryPrediction,
): ExplanationResponse | undefined {
  if (prediction.explanation_status !== "COMPLETED") return undefined;
  return {
    transaction_id: 0,
    model_identifier: prediction.model_identifier,
    method: "local_feature_contribution",
    explanation_technique:
      prediction.explanation_technique === "feature_ablation"
        ? "feature_ablation"
        : "shap",
    explanation_technique_label:
      prediction.explanation_technique_label ?? "Local feature contribution",
    important_features: prediction.top_contributed_features ?? [],
    behavioral_explanation: prediction.reasoning,
    behavioral_explanation_source: prediction.reasoning_source,
  };
}

export function AnalysisHistory({ mode }: { mode: AnalysisMode }) {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [detail, setDetail] = useState<AnalysisRunDetail | null>(null);
  const [expandedTransaction, setExpandedTransaction] = useState<string | null>(
    null,
  );
  const [explainingTransaction, setExplainingTransaction] = useState<
    string | null
  >(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    try {
      const response = await api.history(mode, 50);
      setRuns(response.runs);
      setError(null);
      setDetail((current) => {
        if (!current) return current;
        return response.runs.some((run) => run.id === current.run.id)
          ? current
          : null;
      });
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not load history",
      );
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    void loadRuns();
    const refresh = () => void loadRuns();
    window.addEventListener("cypher:analysis-history-changed", refresh);
    return () =>
      window.removeEventListener("cypher:analysis-history-changed", refresh);
  }, [loadRuns]);

  async function selectRun(runId: string) {
    if (detail?.run.id === runId) {
      setDetail(null);
      setExpandedTransaction(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setDetail(await api.historyRun(runId));
      setExpandedTransaction(null);
      setSearch("");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not load analysis details",
      );
    } finally {
      setLoading(false);
    }
  }

  async function toggleTransaction(transactionId: string) {
    if (!detail) return;
    if (expandedTransaction === transactionId) {
      setExpandedTransaction(null);
      return;
    }
    setExpandedTransaction(transactionId);
    const transaction = detail.transactions.find(
      (item) => item.id === transactionId,
    );
    const missing =
      transaction?.predictions.filter(
        (prediction) => prediction.explanation_status !== "COMPLETED",
      ) ?? [];
    if (!missing.length) return;
    setExplainingTransaction(transactionId);
    const settled = await Promise.allSettled(
      missing.map((prediction) =>
        api.explainHistoryPrediction(prediction.id).then((explanation) => ({
          predictionId: prediction.id,
          explanation,
        })),
      ),
    );
    const completed = new Map(
      settled.flatMap((result) =>
        result.status === "fulfilled"
          ? [[result.value.predictionId, result.value.explanation] as const]
          : [],
      ),
    );
    setDetail((current) =>
      current
        ? {
            ...current,
            transactions: current.transactions.map((item) =>
              item.id === transactionId
                ? {
                    ...item,
                    predictions: item.predictions.map((prediction) => {
                      const explanation = completed.get(prediction.id);
                      if (!explanation)
                        return missing.some(
                          (candidate) => candidate.id === prediction.id,
                        )
                          ? {
                              ...prediction,
                              explanation_status: "FAILED" as const,
                              explanation_error:
                                "Explanation generation failed",
                            }
                          : prediction;
                      return {
                        ...prediction,
                        explanation_status: "COMPLETED" as const,
                        explanation_technique:
                          explanation.explanation_technique,
                        explanation_technique_label:
                          explanation.explanation_technique_label,
                        top_contributed_features:
                          explanation.important_features,
                        reasoning: explanation.behavioral_explanation,
                        reasoning_source:
                          explanation.behavioral_explanation_source,
                        explanation_error: null,
                      };
                    }),
                  }
                : item,
            ),
          }
        : current,
    );
    setExplainingTransaction(null);
  }

  async function exportHistory() {
    setExporting(true);
    setError(null);
    try {
      downloadBlob(
        `${mode}_analysis_history.csv`,
        await api.exportHistory(mode),
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not export history",
      );
    } finally {
      setExporting(false);
    }
  }

  const visibleTransactions = useMemo(() => {
    const query = search.trim();
    return (detail?.transactions ?? [])
      .filter((transaction) =>
        String(
          transaction.raw_transaction_id ?? transaction.transaction_id ?? "",
        ).includes(query),
      )
      .slice(0, 100);
  }, [detail, search]);

  return (
    <Panel
      title={`${MODE_LABELS[mode]} history`}
      eyebrow="Saved in Supabase for this browser"
      actions={
        <button
          className="button button-secondary"
          type="button"
          disabled={exporting || !runs.length}
          onClick={() => void exportHistory()}
        >
          <Icon name="download" />
          {exporting ? "Exporting…" : "Export all history"}
        </button>
      }
    >
      {error ? <ErrorState message={error} /> : null}
      {!runs.length && !loading ? (
        <EmptyState
          title="No saved analyses"
          detail={`Completed ${MODE_LABELS[mode].toLowerCase()} analyses will appear here.`}
        />
      ) : (
        <div className="analysis-history-layout">
          <div className="history-run-list" aria-label="Saved analysis runs">
            {runs.map((run) => (
              <button
                key={run.id}
                type="button"
                className={`history-run-card ${detail?.run.id === run.id ? "active" : ""}`}
                onClick={() => void selectRun(run.id)}
              >
                <span>
                  <strong>{run.source_name || MODE_LABELS[mode]}</strong>
                  <small>{formatDate(run.created_at)}</small>
                </span>
                <span>
                  <StatusBadge
                    tone={
                      run.status === "FAILED"
                        ? "high"
                        : run.status === "COMPLETED"
                          ? "low"
                          : "review"
                    }
                  >
                    {run.status}
                  </StatusBadge>
                  <small>{formatNumber(run.total_transactions)} rows</small>
                </span>
              </button>
            ))}
          </div>
          <div className="history-detail">
            {loading ? <p className="muted">Loading saved analysis…</p> : null}
            {detail ? (
              <>
                <label className="search-box">
                  <Icon name="search" />
                  <span className="visually-hidden">
                    Search saved transaction ID
                  </span>
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search transaction ID"
                  />
                </label>
                <div className="history-transaction-list">
                  {visibleTransactions.map((transaction) => {
                    const expanded = expandedTransaction === transaction.id;
                    const hasFraudPrediction = transaction.predictions.some(
                      (prediction) => prediction.decision,
                    );
                    const hasPrediction = transaction.predictions.length > 0;
                    return (
                      <section
                        className="history-transaction"
                        key={transaction.id}
                      >
                        <button
                          type="button"
                          className="history-transaction-summary"
                          aria-expanded={expanded}
                          onClick={() => void toggleTransaction(transaction.id)}
                        >
                          <span className="mono">
                            {transaction.raw_transaction_id ||
                              transaction.transaction_id ||
                              "Unknown transaction"}
                          </span>
                          <span>
                            {transaction.predictions.length} model result
                            {transaction.predictions.length === 1 ? "" : "s"}
                          </span>
                          <span className="history-verdict">
                            <StatusBadge
                              tone={
                                !hasPrediction
                                  ? "neutral"
                                  : hasFraudPrediction
                                    ? "high"
                                    : "low"
                              }
                            >
                              {!hasPrediction
                                ? "UNAVAILABLE"
                                : hasFraudPrediction
                                  ? "FRAUD"
                                  : "NOT FRAUD"}
                            </StatusBadge>
                          </span>
                          <StatusBadge
                            tone={
                              transaction.status === "FAILED" ? "high" : "low"
                            }
                          >
                            {transaction.status}
                          </StatusBadge>
                          <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
                        </button>
                        {expanded ? (
                          <div className="history-transaction-detail">
                            {transaction.error_message ? (
                              <ErrorState message={transaction.error_message} />
                            ) : null}
                            {explainingTransaction === transaction.id ? (
                              <p className="muted">
                                Generating and saving model explanations…
                              </p>
                            ) : null}
                            {transaction.predictions.length ? (
                              <PredictionTable
                                rows={transaction.predictions.map(
                                  (prediction) => ({
                                    key: prediction.id,
                                    transactionId:
                                      transaction.transaction_id ?? 0,
                                    modelIdentifier:
                                      prediction.model_identifier,
                                    modelName: prediction.model_name,
                                    decision: prediction.decision,
                                    score: prediction.risk_score,
                                    threshold: prediction.threshold,
                                    analyzedAt: prediction.created_at,
                                    input: transaction.input_payload,
                                    historyPredictionId: prediction.id,
                                    cachedExplanation:
                                      cachedExplanation(prediction),
                                  }),
                                )}
                              />
                            ) : null}
                          </div>
                        ) : null}
                      </section>
                    );
                  })}
                </div>
                <p className="table-note">
                  Showing {visibleTransactions.length} of{" "}
                  {detail.transactions.length} saved transactions.
                </p>
              </>
            ) : !loading ? (
              <EmptyState
                title="Choose a saved run"
                detail="Select a run to inspect its transactions and model explanations."
              />
            ) : null}
          </div>
        </div>
      )}
    </Panel>
  );
}
