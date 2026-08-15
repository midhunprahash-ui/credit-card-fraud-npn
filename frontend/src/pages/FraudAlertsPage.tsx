import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { AlertDetail, FraudAlert, ModelIdentifier } from "../api/types";
import { Icon } from "../components/Icon";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Panel,
  RiskScore,
  StatusBadge,
} from "../components/ui";
import { formatCurrency, formatDate, formatLatency } from "../utils/format";
import { MODEL_OPTIONS, modelName } from "../config/models";

const STATUS_OPTIONS = [
  "ALL",
  "OPEN",
  "IN_REVIEW",
  "CONFIRMED_FRAUD",
  "LEGITIMATE",
  "ESCALATED",
  "CLOSED",
];

export function FraudAlertsPage() {
  const [alerts, setAlerts] = useState<FraudAlert[] | null>(null);
  const [selected, setSelected] = useState<AlertDetail | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("ALL");
  const [minimumRisk, setMinimumRisk] = useState(0);
  const [minimumAgreement, setMinimumAgreement] = useState(0);
  const [version, setVersion] = useState("ALL");
  const [model, setModel] = useState("ALL");
  const [dateWindow, setDateWindow] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const query = status === "ALL" ? "" : `status=${status}`;
    api
      .alerts(query)
      .then((result) => setAlerts(result.alerts))
      .catch((caught) =>
        setError(
          caught instanceof Error ? caught.message : "Alerts unavailable",
        ),
      );
  }, [status, reload]);
  const filtered = useMemo(
    () =>
      (alerts ?? []).filter(
        (alert) =>
          String(alert.transaction_id).includes(search.trim()) &&
          alert.highest_risk_score >= minimumRisk &&
          alert.model_agreement >= minimumAgreement &&
          (version === "ALL" ||
            alert.stream_runs?.selected_versions.includes(
              version as "V1" | "V2",
            )) &&
          (model === "ALL" ||
            alert.stream_runs?.selected_models.includes(
              model as ModelIdentifier,
            )) &&
          (!dateWindow ||
            new Date(alert.created_at).getTime() >=
              Date.now() - dateWindow * 86_400_000),
      ),
    [alerts, search, minimumRisk, minimumAgreement, version, model, dateWindow],
  );
  async function openAlert(alertId: string) {
    setLoadingDetail(true);
    setError(null);
    try {
      setSelected(await api.alert(alertId));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Alert investigation unavailable",
      );
    } finally {
      setLoadingDetail(false);
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="Investigation workflow"
        title="Fraud alerts"
        description="Prioritise model-flagged transactions, compare pipeline evidence, and record auditable analyst decisions."
      />
      <Panel title="Alert queue" eyebrow="Highest risk first">
        <div className="filter-row">
          <label className="search-box">
            <Icon name="search" />
            <input
              aria-label="Search transaction ID"
              placeholder="Search TransactionID"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <label className="compact-field">
            <span>Status</span>
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {STATUS_OPTIONS.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label className="compact-field">
            <span>Version</span>
            <select
              value={version}
              onChange={(event) => setVersion(event.target.value)}
            >
              <option value="ALL">All versions</option>
              <option>V1</option>
              <option>V2</option>
            </select>
          </label>
          <label className="compact-field">
            <span>Model</span>
            <select
              value={model}
              onChange={(event) => setModel(event.target.value)}
            >
              <option value="ALL">All models</option>
              {MODEL_OPTIONS.map((item) => (
                <option value={item.id} key={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="compact-field">
            <span>Date</span>
            <select
              value={dateWindow}
              onChange={(event) => setDateWindow(Number(event.target.value))}
            >
              <option value={0}>Any date</option>
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
            </select>
          </label>
          <label className="compact-field">
            <span>Minimum risk</span>
            <select
              value={minimumRisk}
              onChange={(event) => setMinimumRisk(Number(event.target.value))}
            >
              <option value={0}>Any risk</option>
              <option value={0.6}>60%+</option>
              <option value={0.85}>85%+</option>
            </select>
          </label>
          <label className="compact-field">
            <span>Fraud votes</span>
            <select
              value={minimumAgreement}
              onChange={(event) =>
                setMinimumAgreement(Number(event.target.value))
              }
            >
              <option value={0}>Any agreement</option>
              <option value={1}>1+ models</option>
              <option value={2}>2+ models</option>
              <option value={3}>3+ models</option>
            </select>
          </label>
        </div>
        {error && !alerts ? (
          <ErrorState
            message={error}
            onRetry={() => {
              setError(null);
              setReload((value) => value + 1);
            }}
          />
        ) : alerts === null ? (
          <LoadingState label="Loading prioritised alerts…" />
        ) : filtered.length ? (
          <div className="table-scroll">
            <table className="clickable-table">
              <thead>
                <tr>
                  <th>Transaction</th>
                  <th>Highest risk</th>
                  <th>Agreement</th>
                  <th>Suspicious value</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th>
                    <span className="visually-hidden">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((alert) => (
                  <tr
                    key={alert.id}
                    tabIndex={0}
                    onClick={() => void openAlert(alert.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") void openAlert(alert.id);
                    }}
                  >
                    <td className="mono">{alert.transaction_id}</td>
                    <td>
                      <RiskScore score={alert.highest_risk_score} compact />
                    </td>
                    <td>
                      {alert.model_agreement}/{alert.selected_model_count}
                    </td>
                    <td>{formatCurrency(alert.suspicious_amount ?? 0)}</td>
                    <td>{formatDate(alert.created_at)}</td>
                    <td>
                      <StatusBadge
                        tone={
                          alert.status === "OPEN"
                            ? "high"
                            : alert.status === "LEGITIMATE" ||
                                alert.status === "CLOSED"
                              ? "low"
                              : "review"
                        }
                      >
                        {alert.status.replaceAll("_", " ")}
                      </StatusBadge>
                    </td>
                    <td>
                      <Icon name="chevron" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No matching fraud alerts"
            detail="Adjust filters or run the held-out replay to populate the investigation queue."
          />
        )}
      </Panel>
      {loadingDetail ? (
        <LoadingState label="Opening transaction investigation…" />
      ) : null}
      {selected ? (
        <InvestigationDrawer
          alert={selected}
          onClose={() => setSelected(null)}
          onUpdated={async () => {
            setSelected(await api.alert(selected.id));
            setReload((value) => value + 1);
          }}
        />
      ) : null}
    </>
  );
}

function InvestigationDrawer({
  alert,
  onClose,
  onUpdated,
}: {
  alert: AlertDetail;
  onClose: () => void;
  onUpdated: () => Promise<void>;
}) {
  const [analyst, setAnalyst] = useState("demo-analyst");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  async function action(value: string) {
    if (
      value === "CLOSED" &&
      !window.confirm(
        "Close this alert? The action remains in the audit history.",
      )
    )
      return;
    setSaving(true);
    setActionError(null);
    try {
      await api.alertAction(alert.id, {
        action: value,
        analyst_identifier: analyst,
        note: note.trim() || null,
      });
      setNote("");
      await onUpdated();
    } catch (caught) {
      setActionError(
        caught instanceof Error ? caught.message : "Action could not be saved",
      );
    } finally {
      setSaving(false);
    }
  }
  const payload = alert.transaction?.transaction_payload ?? {};
  return (
    <div
      className="drawer-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        className="investigation-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="investigation-title"
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">Transaction investigation</p>
            <h2 id="investigation-title">Transaction {alert.transaction_id}</h2>
            <div className="badge-row">
              <RiskScore score={alert.highest_risk_score} />
              <StatusBadge tone="review">
                {alert.status.replaceAll("_", " ")}
              </StatusBadge>
            </div>
          </div>
          <button
            className="icon-button"
            aria-label="Close investigation"
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </header>
        <div className="drawer-content">
          <section>
            <h3>Transaction and identity</h3>
            <div className="detail-grid">
              {Object.entries(payload)
                .filter(([, value]) => value != null)
                .slice(0, 18)
                .map(([key, value]) => (
                  <div key={key}>
                    <span>{key}</span>
                    <strong>{maskValue(key, value)}</strong>
                  </div>
                ))}
            </div>
            <p className="panel-note">
              Sensitive-looking card, address, device, and email values are
              masked in this analyst view.
            </p>
          </section>
          <section>
            <h3>Model results</h3>
            <div className="investigation-models">
              {alert.predictions.map((prediction) => (
                <article key={prediction.model_identifier}>
                  <div>
                    <strong>{modelName(prediction.model_identifier)}</strong>
                    <small className="mono">{prediction.model_run_id}</small>
                  </div>
                  <RiskScore score={prediction.risk_score} compact />
                  <dl>
                    <div>
                      <dt>Threshold</dt>
                      <dd>{prediction.threshold.toFixed(6)}</dd>
                    </div>
                    <div>
                      <dt>Latency</dt>
                      <dd>{formatLatency(prediction.latency_ms)}</dd>
                    </div>
                    <div>
                      <dt>Decision</dt>
                      <dd>{prediction.decision ? "Fraud" : "Legitimate"}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
            <p className="panel-note">
              Actual demonstration label:{" "}
              <strong>
                {alert.predictions[0]?.actual_label == null
                  ? "Hidden"
                  : alert.predictions[0].actual_label
                    ? "Fraud"
                    : "Legitimate"}
              </strong>
              . It was stored only after prediction.
            </p>
          </section>
          <section>
            <h3>Analyst action</h3>
            <div className="form-grid">
              <label className="field">
                <span>Analyst identifier</span>
                <input
                  value={analyst}
                  onChange={(event) => setAnalyst(event.target.value)}
                />
              </label>
              <label className="field field-full">
                <span>Investigation note</span>
                <textarea
                  rows={3}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Add evidence or escalation context…"
                />
              </label>
            </div>
            <div className="action-grid">
              <button
                disabled={saving}
                className="button button-danger"
                onClick={() => void action("CONFIRMED_FRAUD")}
              >
                Confirm fraud
              </button>
              <button
                disabled={saving}
                className="button button-secondary"
                onClick={() => void action("MARKED_LEGITIMATE")}
              >
                Mark legitimate
              </button>
              <button
                disabled={saving}
                className="button button-secondary"
                onClick={() => void action("ESCALATED")}
              >
                Escalate
              </button>
              <button
                disabled={saving || !note.trim()}
                className="button button-ghost"
                onClick={() => void action("NOTE_ADDED")}
              >
                Add note
              </button>
              <button
                disabled={saving}
                className="button button-ghost"
                onClick={() => void action("CLOSED")}
              >
                Close alert
              </button>
            </div>
            {actionError ? <ErrorState message={actionError} /> : null}
          </section>
          <section>
            <h3>Action history</h3>
            {alert.analyst_actions.length ? (
              <ol className="timeline">
                {alert.analyst_actions.map((item) => (
                  <li key={item.id}>
                    <span />
                    <div>
                      <strong>{item.action.replaceAll("_", " ")}</strong>
                      <small>
                        {item.analyst_identifier} ·{" "}
                        {formatDate(item.created_at)}
                      </small>
                      {item.note ? <p>{item.note}</p> : null}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState
                title="No analyst actions"
                detail="The first decision or note will start the audit trail."
              />
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}

function maskValue(key: string, value: unknown): string {
  const text = String(value);
  const sensitive = /card|addr|email|device|id_/i.test(key);
  if (!sensitive) return text.length > 32 ? `${text.slice(0, 29)}…` : text;
  if (text.length <= 4) return "••••";
  return `••••${text.slice(-4)}`;
}
