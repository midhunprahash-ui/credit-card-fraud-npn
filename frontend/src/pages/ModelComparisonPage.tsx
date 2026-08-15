import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { ModelCatalogItem, VersionName } from "../api/types";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  Panel,
  StatusBadge,
} from "../components/ui";
import { formatLatency } from "../utils/format";

export function ModelComparisonPage() {
  const [models, setModels] = useState<ModelCatalogItem[] | null>(null);
  const [version, setVersion] = useState<VersionName | "Both">("Both");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api
      .models()
      .then((result) => setModels(result.models))
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Model catalog unavailable",
        ),
      );
  }, []);
  const visible = useMemo(
    () =>
      (models ?? []).filter(
        (model) => version === "Both" || model.version_name === version,
      ),
    [models, version],
  );
  if (error) return <ErrorState message={error} />;
  if (!models) return <LoadingState label="Loading approved model metrics…" />;
  return (
    <>
      <PageHeader
        eyebrow="Model governance"
        title="V1 versus V2"
        description="Compare all eight approved pipelines using validation-selected operating points and untouched chronological test reporting."
        actions={
          <div className="segmented-control">
            {(["Both", "V1", "V2"] as const).map((item) => (
              <button
                key={item}
                className={version === item ? "active" : ""}
                onClick={() => setVersion(item)}
              >
                {item}
              </button>
            ))}
          </div>
        }
      />
      <div className="callout">
        <strong>Why PR-AUC leads this comparison</strong>
        <p>
          Fraud is rare, so PR-AUC measures how well each model prioritises the
          positive class without being flattered by the many legitimate
          transactions. Test metrics are final reporting only and must not be
          used for further model selection.
        </p>
      </div>
      <Panel
        title="Approved pipeline metrics"
        eyebrow="Validation selects · test reports"
      >
        <div className="table-scroll comparison-table">
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>Val PR-AUC</th>
                <th>Test PR-AUC</th>
                <th>ROC-AUC</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>Threshold</th>
                <th>Training</th>
                <th>Pred. latency</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((model) => {
                const test = model.metrics.test;
                return (
                  <tr key={model.model_identifier}>
                    <td>
                      <div className="model-cell">
                        <strong>{model.model_name}</strong>
                        <span className="mono">{model.run_id}</span>
                        <div className="badge-row">
                          {model.champion ? (
                            <StatusBadge tone="high">
                              Version champion
                            </StatusBadge>
                          ) : null}
                          {model.model_key === "logistic_regression" ? (
                            <StatusBadge tone="neutral">Baseline</StatusBadge>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <Metric value={model.validation_pr_auc} />
                    <Metric value={model.test_pr_auc} />
                    <Metric value={test?.roc_auc} />
                    <Metric value={test?.precision} />
                    <Metric value={test?.recall} />
                    <Metric value={test?.f1} />
                    <td className="mono">{model.threshold.toFixed(6)}</td>
                    <td>
                      {model.metrics.training_seconds == null
                        ? "—"
                        : formatDuration(model.metrics.training_seconds)}
                    </td>
                    <td>
                      {model.metrics.prediction_latency_ms == null
                        ? "—"
                        : formatLatency(model.metrics.prediction_latency_ms)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
      <div className="comparison-cards">
        <Panel title="Validation PR-AUC" eyebrow="Primary selection metric">
          <div className="metric-bars">
            {[...visible]
              .sort((a, b) => b.validation_pr_auc - a.validation_pr_auc)
              .map((model) => (
                <div key={model.model_identifier}>
                  <span>{model.model_name}</span>
                  <div>
                    <i style={{ width: `${model.validation_pr_auc * 100}%` }} />
                  </div>
                  <strong>{model.validation_pr_auc.toFixed(3)}</strong>
                </div>
              ))}
          </div>
        </Panel>
        <Panel title="Interpretation" eyebrow="Analyst guidance">
          <ul className="guidance-list">
            <li>
              <strong>CatBoost.V2</strong> is the current overall champion.
            </li>
            <li>
              <strong>Logistic Regression</strong> is the interpretable
              baseline.
            </li>
            <li>Every score uses its own saved model threshold.</li>
            <li>Model agreement is not an ensemble.</li>
            <li>Anonymised V-feature meanings are never invented.</li>
          </ul>
        </Panel>
      </div>
      <Panel title="Confusion matrices" eyebrow="Chronological test set">
        <div className="confusion-grid">
          {visible.map((model) => (
            <ConfusionMatrix key={model.model_identifier} model={model} />
          ))}
        </div>
      </Panel>
      <Panel title="Global feature evidence" eyebrow="Saved training artifacts">
        <div className="feature-grid">
          {visible
            .filter((model) => model.top_features.length)
            .map((model) => (
              <article className="feature-card" key={model.model_identifier}>
                <header>
                  <strong>{model.model_name}</strong>
                  <span>
                    {model.top_features[0]?.kind === "coefficient"
                      ? "Absolute coefficients"
                      : "Global importance"}
                  </span>
                </header>
                <ol>
                  {model.top_features.slice(0, 6).map((feature) => (
                    <li key={feature.feature}>
                      <span title={feature.feature}>{feature.feature}</span>
                      <i
                        style={{
                          width: `${(feature.value / Math.max(...model.top_features.map((item) => item.value))) * 100}%`,
                        }}
                      />
                    </li>
                  ))}
                </ol>
              </article>
            ))}
        </div>
        <p className="panel-note">
          These are global training-artifact summaries, not transaction-level
          explanations. Anonymised V features are shown by name only.
        </p>
      </Panel>
    </>
  );
}

function Metric({ value }: { value: number | undefined }) {
  return <td className="mono">{value == null ? "—" : value.toFixed(4)}</td>;
}
function formatDuration(seconds: number) {
  if (seconds >= 3600) return `${(seconds / 3600).toFixed(1)} h`;
  if (seconds >= 60) return `${(seconds / 60).toFixed(1)} min`;
  return `${seconds.toFixed(1)} s`;
}
function ConfusionMatrix({ model }: { model: ModelCatalogItem }) {
  const matrix = model.metrics.test?.confusion_matrix;
  return (
    <article className="confusion-card">
      <header>
        <strong>{model.model_name}</strong>
        <span>Actual label →</span>
      </header>
      {matrix ? (
        <div className="matrix">
          <span />
          <b>Legitimate</b>
          <b>Fraud</b>
          <b>Pred. legitimate</b>
          <i className="matrix-low">{matrix[0][0].toLocaleString()}</i>
          <i className="matrix-miss">{matrix[1][0].toLocaleString()}</i>
          <b>Pred. fraud</b>
          <i className="matrix-review">{matrix[0][1].toLocaleString()}</i>
          <i className="matrix-high">{matrix[1][1].toLocaleString()}</i>
        </div>
      ) : (
        <p className="muted">Metrics artifact unavailable</p>
      )}
    </article>
  );
}
