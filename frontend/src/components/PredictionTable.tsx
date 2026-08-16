import { useState } from "react";

import { api } from "../api/client";
import type { ModelIdentifier } from "../api/types";
import { formatNumber } from "../utils/format";
import { ErrorState, StatusBadge } from "./ui";

export type PredictionTableRow = {
  key: string;
  transactionId: number;
  modelIdentifier: ModelIdentifier;
  modelName: string;
  decision: boolean;
  score: number;
  threshold: number;
  input?: Record<string, unknown>;
};

type RowDetail = {
  key: string;
  loading: boolean;
  input: Record<string, unknown> | null;
  explanationTechniqueLabel: string | null;
  features: Array<{
    feature: string;
    contribution: number;
    direction: "toward_fraud" | "toward_not_fraud";
  }>;
  error: string | null;
};

export function PredictionTable({
  rows,
  loadInput,
}: {
  rows: PredictionTableRow[];
  loadInput?: (transactionId: number) => Promise<Record<string, unknown>>;
}) {
  const [detail, setDetail] = useState<RowDetail | null>(null);

  async function toggle(row: PredictionTableRow) {
    if (detail?.key === row.key) {
      setDetail(null);
      return;
    }
    setDetail({
      key: row.key,
      loading: true,
      input: row.input ?? null,
      explanationTechniqueLabel: null,
      features: [],
      error: null,
    });
    try {
      const input = row.input ?? (await loadInput?.(row.transactionId));
      if (!input) throw new Error("Transaction inputs are unavailable.");
      setDetail((current) =>
        current?.key === row.key ? { ...current, input } : current,
      );
      const explanation = await api.explain(input, row.modelIdentifier);
      setDetail((current) =>
        current?.key === row.key
          ? {
              ...current,
              loading: false,
              input,
              explanationTechniqueLabel:
                explanation.explanation_technique_label,
              features: explanation.important_features,
            }
          : current,
      );
    } catch (caught) {
      setDetail((current) =>
        current?.key === row.key
          ? {
              ...current,
              loading: false,
              error:
                caught instanceof Error
                  ? caught.message
                  : "Could not load prediction details",
            }
          : current,
      );
    }
  }

  return (
    <div className="table-scroll prediction-table-wrap">
      <table className="prediction-table">
        <thead>
          <tr>
            <th>Transaction ID</th>
            <th>Model</th>
            <th>Fraud</th>
            <th>Not fraud</th>
            <th>Score</th>
            <th>Threshold</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const expanded = detail?.key === row.key;
            return (
              <PredictionTableEntry
                key={row.key}
                row={row}
                expanded={expanded}
                detail={expanded ? detail : null}
                onToggle={() => void toggle(row)}
              />
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PredictionTableEntry({
  row,
  expanded,
  detail,
  onToggle,
}: {
  row: PredictionTableRow;
  expanded: boolean;
  detail: RowDetail | null;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={`prediction-row ${row.decision ? "prediction-fraud" : "prediction-not-fraud"}`}
        onClick={onToggle}
      >
        <td>
          <button
            type="button"
            className="row-expand-button mono"
            aria-expanded={expanded}
            onClick={(event) => {
              event.stopPropagation();
              onToggle();
            }}
          >
            {row.transactionId}{" "}
            <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
          </button>
        </td>
        <td>{row.modelName}</td>
        <td className={row.decision ? "decision-fraud" : "decision-empty"}>
          {row.decision ? "● FRAUD" : "—"}
        </td>
        <td className={!row.decision ? "decision-not-fraud" : "decision-empty"}>
          {!row.decision ? "● NOT FRAUD" : "—"}
        </td>
        <td className="mono">{formatNumber(row.score, 6)}</td>
        <td className="mono">{formatNumber(row.threshold, 6)}</td>
      </tr>
      {expanded ? (
        <tr className="prediction-detail-row">
          <td colSpan={6}>
            <PredictionDetail detail={detail} />
          </td>
        </tr>
      ) : null}
    </>
  );
}

function PredictionDetail({ detail }: { detail: RowDetail | null }) {
  if (!detail) return null;
  const inputEntries = Object.entries(detail.input ?? {}).filter(
    ([name, value]) => name !== "isFraud" && value !== null && value !== "",
  );
  return (
    <div className="prediction-detail-grid">
      <section>
        <h4>Strongest decision features</h4>
        {detail.explanationTechniqueLabel ? (
          <p className="explanation-technique">
            Explanation method: {detail.explanationTechniqueLabel}
          </p>
        ) : null}
        {detail.loading ? (
          <p className="muted">Calculating local explanation…</p>
        ) : null}
        {detail.features.length ? (
          <table className="feature-driver-table">
            <colgroup>
              <col className="feature-name-column" />
              <col className="feature-direction-column" />
              <col className="feature-contribution-column" />
            </colgroup>
            <thead>
              <tr>
                <th>Feature</th>
                <th>Direction</th>
                <th>Contribution</th>
              </tr>
            </thead>
            <tbody>
              {detail.features.map((feature) => (
                <tr key={feature.feature}>
                  <td className="mono">{feature.feature}</td>
                  <td>
                    <StatusBadge
                      tone={
                        feature.direction === "toward_fraud" ? "high" : "low"
                      }
                    >
                      {feature.direction === "toward_fraud"
                        ? "Toward fraud"
                        : "Toward not fraud"}
                    </StatusBadge>
                  </td>
                  <td className="mono feature-contribution">
                    {feature.contribution >= 0 ? "+" : ""}
                    {formatNumber(feature.contribution, 6)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        <p className="detail-note">
          Local model contribution or score sensitivity for this transaction. It
          explains model behaviour, not causation.
        </p>
        {detail.error ? <ErrorState message={detail.error} /> : null}
      </section>
      <section>
        <h4>Transaction inputs ({inputEntries.length})</h4>
        <div className="input-values-scroll">
          <table className="input-values-table">
            <colgroup>
              <col className="input-name-column" />
              <col className="input-value-column" />
            </colgroup>
            <thead>
              <tr>
                <th>Input</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {inputEntries.map(([name, value]) => (
                <tr key={name}>
                  <td className="mono">{name}</td>
                  <td>{String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
